from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.auth_deps import Principal, PrincipalType
from app.modules.knowledge_engine import router as knowledge_engine_router


def _principal() -> Principal:
    return Principal(
        principal_id="pytest-operator",
        principal_type=PrincipalType.HUMAN,
        email="pytest@example.com",
        name="Pytest Operator",
        roles=["operator", "admin"],
        scopes=["read", "write"],
        tenant_id="test-tenant",
    )


class _FakeKnowledgeEngineService:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self._item = {
            "id": uuid4(),
            "tenant_id": "test-tenant",
            "title": "AXE Intent Surface",
            "content": "How to write better operator intents.",
            "type": "help_doc",
            "tags": ["help", "axe"],
            "visibility": "tenant",
            "metadata": {"help_key": "axe.chat.intent", "surface": "axe-ui"},
            "created_at": now,
            "updated_at": now,
        }

    async def list_help_docs(self, db, principal, surface=None, limit=50):  # noqa: ANN001
        _ = (db, principal, surface, limit)
        return [self._item]

    async def get_help_doc(self, db, principal, help_key, surface=None):  # noqa: ANN001
        _ = (db, principal, surface)
        if help_key == "axe.chat.intent":
            return self._item
        return None


@pytest.mark.asyncio
async def test_list_help_docs_returns_items(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _FakeKnowledgeEngineService()
    monkeypatch.setattr(knowledge_engine_router, "get_knowledge_engine_service", lambda: service)

    response = await knowledge_engine_router.list_help_docs(
        surface="axe-ui",
        limit=10,
        db=object(),
        principal=_principal(),
    )

    assert response.total == 1
    assert response.items[0].metadata["help_key"] == "axe.chat.intent"


@pytest.mark.asyncio
async def test_get_help_doc_returns_404_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _FakeKnowledgeEngineService()
    monkeypatch.setattr(knowledge_engine_router, "get_knowledge_engine_service", lambda: service)

    with pytest.raises(HTTPException) as exc:
        await knowledge_engine_router.get_help_doc(
            help_key="missing.topic",
            surface="axe-ui",
            db=object(),
            principal=_principal(),
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "Help document not found"


@pytest.mark.asyncio
async def test_get_help_doc_returns_item(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _FakeKnowledgeEngineService()
    monkeypatch.setattr(knowledge_engine_router, "get_knowledge_engine_service", lambda: service)

    response = await knowledge_engine_router.get_help_doc(
        help_key="axe.chat.intent",
        surface="axe-ui",
        db=object(),
        principal=_principal(),
    )

    assert response.title == "AXE Intent Surface"
    assert response.metadata["surface"] == "axe-ui"
