from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import importlib
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.agent_management.router import router as agent_router


def build_agent_principal(agent_id: str = "agent-a") -> Principal:
    return Principal(
        principal_id=agent_id,
        principal_type=PrincipalType.AGENT,
        email=None,
        name="Agent A",
        roles=["agent"],
        scopes=["write"],
        tenant_id="tenant-a",
        agent_id=agent_id,
    )


@contextmanager
def override_auth_principal(client: TestClient, principal: Principal):
    client.app.dependency_overrides[require_auth] = lambda: principal
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(require_auth, None)


@contextmanager
def override_auth_unauthorized(client: TestClient):
    async def _unauthorized():
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    client.app.dependency_overrides[require_auth] = _unauthorized
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(require_auth, None)


@pytest.fixture
def agent_app() -> FastAPI:
    app = FastAPI()
    app.include_router(agent_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    return app


@pytest.fixture
def agent_client(agent_app: FastAPI) -> TestClient:
    return TestClient(agent_app)


def test_agent_invoke_skill_requires_authentication(agent_client: TestClient) -> None:
    with override_auth_unauthorized(agent_client):
        response = agent_client.post(
            "/api/agents/agent-a/invoke-skill",
            json={"skill_key": "demo.skill", "idempotency_key": "idem-1"},
        )
    assert response.status_code == 401


def test_agent_invoke_skill_uses_service(agent_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_agent_principal()
    router_module = importlib.import_module("app.modules.agent_management.router")
    run_id = uuid4()

    class FakeService:
        async def invoke_skill(self, db, agent_id, payload, principal_arg):
            assert agent_id == "agent-a"
            return (
                object(),
                {
                    "id": run_id,
                    "tenant_id": principal_arg.tenant_id,
                    "skill_key": payload.skill_key,
                    "skill_version": 2,
                    "state": "queued",
                    "input_payload": payload.input_payload,
                    "plan_snapshot": {},
                    "provider_selection_snapshot": {},
                    "requested_by": principal_arg.principal_id,
                    "requested_by_type": principal_arg.principal_type.value,
                    "trigger_type": payload.trigger_type.value,
                    "policy_decision": {"allowed": True},
                    "risk_tier": "medium",
                    "correlation_id": "corr-1",
                    "causation_id": None,
                    "idempotency_key": payload.idempotency_key,
                    "mission_id": None,
                    "created_at": datetime.now(timezone.utc),
                    "started_at": None,
                    "finished_at": None,
                    "deadline_at": None,
                    "retry_count": 0,
                    "cost_estimate": 0.0,
                    "cost_actual": None,
                    "output_payload": {},
                    "evaluation_summary": {},
                    "failure_code": None,
                    "failure_reason_sanitized": None,
                },
                None,
            )

    monkeypatch.setattr(router_module, "get_agent_service", lambda: FakeService())
    with override_auth_principal(agent_client, principal):
        response = agent_client.post(
            "/api/agents/agent-a/invoke-skill",
            json={"skill_key": "demo.skill", "idempotency_key": "idem-1"},
        )
    assert response.status_code == 200
    assert response.json()["skill_run"]["skill_key"] == "demo.skill"


def test_agent_delegate_uses_service(agent_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_agent_principal()
    router_module = importlib.import_module("app.modules.agent_management.router")
    delegation_id = uuid4()
    run_id = uuid4()

    class FakeService:
        async def create_delegation(self, db, agent_id, payload, principal_arg):
            assert agent_id == "agent-a"
            return (
                {
                    "id": delegation_id,
                    "tenant_id": principal_arg.tenant_id,
                    "source_agent_id": agent_id,
                    "target_agent_id": payload.target_agent_id,
                    "skill_run_id": run_id,
                    "status": "requested",
                    "delegation_reason": payload.delegation_reason,
                    "correlation_id": "corr-1",
                    "requested_by": principal_arg.principal_id,
                    "created_at": datetime.now(timezone.utc),
                    "accepted_at": None,
                    "completed_at": None,
                },
                {
                    "id": run_id,
                    "tenant_id": principal_arg.tenant_id,
                    "skill_key": payload.skill_key,
                    "skill_version": 2,
                    "state": "queued",
                    "input_payload": payload.input_payload,
                    "plan_snapshot": {},
                    "provider_selection_snapshot": {},
                    "requested_by": principal_arg.principal_id,
                    "requested_by_type": principal_arg.principal_type.value,
                    "trigger_type": payload.trigger_type.value,
                    "policy_decision": {"allowed": True},
                    "risk_tier": "medium",
                    "correlation_id": "corr-1",
                    "causation_id": None,
                    "idempotency_key": payload.idempotency_key,
                    "mission_id": None,
                    "created_at": datetime.now(timezone.utc),
                    "started_at": None,
                    "finished_at": None,
                    "deadline_at": None,
                    "retry_count": 0,
                    "cost_estimate": 0.0,
                    "cost_actual": None,
                    "output_payload": {},
                    "evaluation_summary": {},
                    "failure_code": None,
                    "failure_reason_sanitized": None,
                },
                None,
            )

    monkeypatch.setattr(router_module, "get_agent_service", lambda: FakeService())
    with override_auth_principal(agent_client, principal):
        response = agent_client.post(
            "/api/agents/agent-a/delegate",
            json={
                "target_agent_id": "agent-b",
                "skill_key": "demo.skill",
                "idempotency_key": "idem-2",
                "delegation_reason": "handoff",
            },
        )
    assert response.status_code == 200
    assert response.json()["delegation"]["target_agent_id"] == "agent-b"
    assert response.json()["skill_run"]["skill_key"] == "demo.skill"


def test_agent_delegation_list_uses_service(agent_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_agent_principal()
    router_module = importlib.import_module("app.modules.agent_management.router")

    class FakeService:
        async def list_delegations(self, db, tenant_id, agent_id=None):
            return [
                {
                    "id": uuid4(),
                    "tenant_id": tenant_id,
                    "source_agent_id": agent_id,
                    "target_agent_id": "agent-b",
                    "skill_run_id": uuid4(),
                    "status": "requested",
                    "delegation_reason": "handoff",
                    "correlation_id": "corr-1",
                    "requested_by": agent_id,
                    "created_at": datetime.now(timezone.utc),
                    "accepted_at": None,
                    "completed_at": None,
                }
            ]

    monkeypatch.setattr(router_module, "get_agent_service", lambda: FakeService())
    with override_auth_principal(agent_client, principal):
        response = agent_client.get("/api/agents/agent-a/delegations")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_agent_invoke_skill_rejects_agent_identity_mismatch(agent_client: TestClient) -> None:
    principal = build_agent_principal(agent_id="agent-x")
    with override_auth_principal(agent_client, principal):
        response = agent_client.post(
            "/api/agents/agent-a/invoke-skill",
            json={"skill_key": "demo.skill", "idempotency_key": "idem-3"},
        )
    assert response.status_code == 403
