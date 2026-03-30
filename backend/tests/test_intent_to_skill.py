from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import (
    Principal,
    PrincipalType,
    get_current_principal,
    require_auth,
)
from app.core.database import get_db
from app.modules.intent_to_skill.router import router as intent_router


def _principal(*roles: str, tenant_id: str | None = "tenant-a") -> Principal:
    return Principal(
        principal_id="intent-user",
        principal_type=PrincipalType.HUMAN,
        email="intent@example.com",
        name="Intent User",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id=tenant_id,
    )


def _client_with_principal(principal: Principal) -> TestClient:
    app = FastAPI()
    app.include_router(intent_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    return TestClient(app)


def test_intent_execute_returns_draft_when_no_match(monkeypatch) -> None:
    client = _client_with_principal(_principal("viewer"))
    route_module = __import__("app.modules.intent_to_skill.router", fromlist=["router"])

    class FakeService:
        async def execute_intent(self, db, payload, principal):
            _ = (db, payload, principal)
            return {
                "resolution_type": "draft_required",
                "normalized_intent": "build me a custom workflow",
                "confidence": 0.0,
                "reason": "No matching active skill exceeded minimum confidence",
                "candidates": [],
                "draft_suggestion": {
                    "suggested_skill_key": "draft.build-me-custom",
                    "rationale": "No active match",
                    "recommended_capabilities": ["workflow.execute"],
                },
            }

    monkeypatch.setattr(route_module, "get_intent_to_skill_service", lambda: FakeService())

    response = client.post(
        "/api/intent/execute",
        json={
            "intent_text": "build me a custom workflow",
            "auto_execute": False,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["resolution_type"] == "draft_required"
    assert body["draft_suggestion"]["suggested_skill_key"].startswith("draft.")


def test_intent_execute_blocks_auto_execute_for_viewer(monkeypatch) -> None:
    client = _client_with_principal(_principal("viewer"))
    route_module = __import__("app.modules.intent_to_skill.router", fromlist=["router"])

    class FakeService:
        async def execute_intent(self, db, payload, principal):
            _ = (db, payload, principal)
            return {}

    monkeypatch.setattr(route_module, "get_intent_to_skill_service", lambda: FakeService())

    response = client.post(
        "/api/intent/execute",
        json={
            "intent_text": "search knowledge about incidents",
            "auto_execute": True,
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role for auto_execute"
