from __future__ import annotations

from contextlib import contextmanager
import importlib
from typing import cast

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.modules.supervisor.router import router as supervisor_router


def build_principal(*roles: str) -> Principal:
    return Principal(
        principal_id="ops-user",
        principal_type=PrincipalType.HUMAN,
        email="ops@example.com",
        name="Ops",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@contextmanager
def override_auth_principal(client: TestClient, principal: Principal):
    app = cast(FastAPI, client.app)
    app.dependency_overrides[require_auth] = lambda: principal  # type: ignore[attr-defined]
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)  # type: ignore[attr-defined]


@contextmanager
def override_auth_unauthorized(client: TestClient):
    async def _unauthorized():
        raise HTTPException(status_code=401, detail="Authentication required")

    app = cast(FastAPI, client.app)
    app.dependency_overrides[require_auth] = _unauthorized  # type: ignore[attr-defined]
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)  # type: ignore[attr-defined]


def build_test_app() -> FastAPI:
    from app.modules.supervisor import router as supervisor_router_module

    app = FastAPI()
    app.include_router(supervisor_router)

    async def _db_override():
        yield None

    app.dependency_overrides[supervisor_router_module._get_db] = _db_override
    return app


def test_supervisor_escalation_route_requires_auth() -> None:
    app = build_test_app()
    client = TestClient(app)

    with override_auth_unauthorized(client):
        response = client.post(
            "/api/supervisor/escalations/domain",
            json={
                "domain_key": "programming",
                "requested_by": "agent-a",
                "requested_by_type": "agent",
                "reason": "risk detected",
                "risk_tier": "high",
            },
        )

    assert response.status_code == 401


def test_supervisor_escalation_create_and_list() -> None:
    app = build_test_app()
    client = TestClient(app)

    payload = {
        "domain_key": "programming",
        "requested_by": "agent-a",
        "requested_by_type": "agent",
        "tenant_id": "tenant-a",
        "reason": "high-risk production auth flow",
        "reasons": ["production", "auth"],
        "recommended_next_actions": ["request_supervisor_review"],
        "risk_tier": "high",
        "correlation_id": "corr-123",
    }

    with override_auth_principal(client, build_principal("operator")):
        create_response = client.post("/api/supervisor/escalations/domain", json=payload)
        list_response = client.get("/api/supervisor/escalations/domain?limit=10")

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["escalation_id"].startswith("esc-")
    assert created["status"] == "queued"

    assert list_response.status_code == 200
    body = list_response.json()
    assert body["total"] >= 1
    assert any(item["domain_key"] == "programming" for item in body["items"])


def test_supervisor_escalation_decision_flow() -> None:
    app = build_test_app()
    client = TestClient(app)

    payload = {
        "domain_key": "programming",
        "requested_by": "agent-a",
        "requested_by_type": "agent",
        "tenant_id": "tenant-a",
        "reason": "high-risk production auth flow",
        "risk_tier": "high",
    }

    with override_auth_principal(client, build_principal("operator")):
        created = client.post("/api/supervisor/escalations/domain", json=payload).json()
        escalation_id = created["escalation_id"]

        in_review_response = client.post(
            f"/api/supervisor/escalations/domain/{escalation_id}/decision",
            json={
                "status": "in_review",
                "reviewer_id": "ignored-by-api",
                "decision_reason": "review started",
                "notes": {"phase": "triage"},
            },
        )

        decide_response = client.post(
            f"/api/supervisor/escalations/domain/{escalation_id}/decision",
            json={
                "status": "approved",
                "reviewer_id": "ignored-by-api",
                "decision_reason": "risk mitigated",
                "notes": {"checklist": "ok"},
            },
        )
        get_response = client.get(f"/api/supervisor/escalations/domain/{escalation_id}")

    assert in_review_response.status_code == 200
    assert in_review_response.json()["status"] == "in_review"
    assert decide_response.status_code == 200
    assert decide_response.json()["status"] == "approved"
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "approved"


def test_supervisor_escalation_invalid_transition_returns_409() -> None:
    app = build_test_app()
    client = TestClient(app)

    payload = {
        "domain_key": "programming",
        "requested_by": "agent-a",
        "requested_by_type": "agent",
        "tenant_id": "tenant-a",
        "reason": "needs review",
        "risk_tier": "high",
    }

    with override_auth_principal(client, build_principal("operator")):
        created = client.post("/api/supervisor/escalations/domain", json=payload).json()
        escalation_id = created["escalation_id"]

        invalid_decision = client.post(
            f"/api/supervisor/escalations/domain/{escalation_id}/decision",
            json={
                "status": "approved",
                "reviewer_id": "ignored",
                "decision_reason": "trying to skip in_review",
            },
        )

    assert invalid_decision.status_code == 409
    assert "Invalid escalation transition" in invalid_decision.json()["detail"]


def test_supervisor_decision_emits_event(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    service_module = importlib.import_module("app.modules.supervisor.service")
    events = []

    async def _fake_emit(event_type: str, payload: dict):
        events.append((event_type, payload))

    monkeypatch.setattr(service_module, "_emit_event_safe", _fake_emit)

    payload = {
        "domain_key": "programming",
        "requested_by": "agent-a",
        "requested_by_type": "agent",
        "tenant_id": "tenant-a",
        "reason": "needs review",
        "risk_tier": "high",
    }

    with override_auth_principal(client, build_principal("operator")):
        created = client.post("/api/supervisor/escalations/domain", json=payload).json()
        escalation_id = created["escalation_id"]

        _ = client.post(
            f"/api/supervisor/escalations/domain/{escalation_id}/decision",
            json={
                "status": "in_review",
                "reviewer_id": "ignored",
                "decision_reason": "triage",
            },
        )

        _ = client.post(
            f"/api/supervisor/escalations/domain/{escalation_id}/decision",
            json={
                "status": "approved",
                "reviewer_id": "ignored",
                "decision_reason": "approved",
            },
        )

    assert any(evt[0] == "supervisor.domain_escalation.decided" for evt in events)
    assert any(evt[0] == "supervisor.domain_escalation.decided.v1" for evt in events)
