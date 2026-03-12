from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

import pytest

from app.modules.axe_sessions.router import get_service


@dataclass
class _MessageRecord:
    id: UUID
    session_id: UUID
    role: str
    content: str
    attachments_json: list[str] = field(default_factory=list)
    message_metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class _SessionRecord:
    id: UUID
    principal_id: str
    tenant_id: str | None
    title: str
    preview: str | None
    status: str = "active"
    message_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_message_at: datetime | None = None
    messages: list[_MessageRecord] = field(default_factory=list)


class _FakeSessionService:
    def __init__(self) -> None:
        self.sessions: dict[UUID, _SessionRecord] = {}

    async def list_sessions(self, *, principal_id: str, tenant_id: str | None):
        return [
            session
            for session in self.sessions.values()
            if session.principal_id == principal_id and session.tenant_id == tenant_id and session.status == "active"
        ]

    async def create_session(self, *, principal_id: str, tenant_id: str | None, payload):
        session = _SessionRecord(
            id=uuid4(),
            principal_id=principal_id,
            tenant_id=tenant_id,
            title=payload.title or "New Chat",
            preview=None,
        )
        self.sessions[session.id] = session
        return session

    async def get_session_detail(self, *, principal_id: str, tenant_id: str | None, session_id: UUID):
        session = self.sessions.get(session_id)
        if session is None or session.status != "active":
            return None
        if session.principal_id != principal_id or session.tenant_id != tenant_id:
            return None
        return session

    async def update_session_title(self, *, principal_id: str, tenant_id: str | None, session_id: UUID, payload):
        session = await self.get_session_detail(principal_id=principal_id, tenant_id=tenant_id, session_id=session_id)
        if session is None:
            return None
        session.title = payload.title
        session.updated_at = datetime.utcnow()
        return session

    async def delete_session(self, *, principal_id: str, tenant_id: str | None, session_id: UUID):
        session = await self.get_session_detail(principal_id=principal_id, tenant_id=tenant_id, session_id=session_id)
        if session is None:
            return False
        session.status = "deleted"
        session.updated_at = datetime.utcnow()
        return True

    async def append_message(self, *, principal_id: str, tenant_id: str | None, session_id: UUID, payload):
        session = await self.get_session_detail(principal_id=principal_id, tenant_id=tenant_id, session_id=session_id)
        if session is None:
            return None
        message = _MessageRecord(
            id=uuid4(),
            session_id=session.id,
            role=payload.role,
            content=payload.content,
            attachments_json=list(payload.attachments),
            message_metadata=dict(payload.metadata),
        )
        session.messages.append(message)
        session.message_count += 1
        session.preview = payload.content[:120]
        session.last_message_at = datetime.utcnow()
        if session.title == "New Chat" and payload.role == "user" and session.message_count == 1:
            session.title = payload.content[:60]
        return message


@pytest.fixture
def fake_session_service(test_app):
    service = _FakeSessionService()
    test_app.dependency_overrides[get_service] = lambda: service
    yield service
    test_app.dependency_overrides.pop(get_service, None)


def test_axe_sessions_create_and_list(client, fake_session_service):
    create = client.post("/api/axe/sessions", json={"title": "Sprint Plan"})
    assert create.status_code == 201
    payload = create.json()
    assert payload["title"] == "Sprint Plan"

    listed = client.get("/api/axe/sessions")
    assert listed.status_code == 200
    sessions = listed.json()
    assert len(sessions) == 1
    assert sessions[0]["title"] == "Sprint Plan"


def test_axe_session_detail_rename_and_delete(client, fake_session_service):
    created = client.post("/api/axe/sessions", json={"title": "Initial"}).json()
    session_id = created["id"]

    detail = client.get(f"/api/axe/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Initial"

    renamed = client.patch(f"/api/axe/sessions/{session_id}", json={"title": "Renamed Session"})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Renamed Session"

    deleted = client.delete(f"/api/axe/sessions/{session_id}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/axe/sessions/{session_id}")
    assert missing.status_code == 404


def test_axe_session_append_message_generates_title(client, fake_session_service):
    created = client.post("/api/axe/sessions", json={}).json()
    session_id = created["id"]

    appended = client.post(
        f"/api/axe/sessions/{session_id}/messages",
        json={"role": "user", "content": "Bitte analysiere die letzten Runtime Fehler", "attachments": []},
    )
    assert appended.status_code == 201
    body = appended.json()
    assert body["role"] == "user"

    detail = client.get(f"/api/axe/sessions/{session_id}")
    assert detail.status_code == 200
    assert detail.json()["title"].startswith("Bitte analysiere")
    assert detail.json()["message_count"] == 1


def test_axe_session_ownership_is_enforced(client, test_app):
    service = _FakeSessionService()
    session = _SessionRecord(
        id=uuid4(),
        principal_id="different-user",
        tenant_id="test-tenant",
        title="Other user",
        preview=None,
    )
    service.sessions[session.id] = session

    test_app.dependency_overrides[get_service] = lambda: service
    response = client.get(f"/api/axe/sessions/{session.id}")
    test_app.dependency_overrides.pop(get_service, None)

    assert response.status_code == 404
