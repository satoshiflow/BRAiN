"""API auth and audit tests for quarantine and repair modules."""

from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.genetic_quarantine.router import router as genetic_quarantine_router
from app.modules.opencode_repair.router import router as opencode_repair_router
from app.modules.genetic_quarantine import service as gq_service
from app.modules.opencode_repair import service as or_service


@pytest.fixture(autouse=True)
def reset_singletons():
    gq_service._service = None
    or_service._service = None
    yield
    gq_service._service = None
    or_service._service = None


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    app.include_router(genetic_quarantine_router)
    app.include_router(opencode_repair_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.fixture
def viewer_principal() -> Principal:
    return Principal(
        principal_id="viewer-1",
        principal_type=PrincipalType.HUMAN,
        email="viewer@example.com",
        name="Viewer",
        roles=["viewer"],
        scopes=["read"],
    )


@pytest.fixture
def operator_principal() -> Principal:
    return Principal(
        principal_id="op-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator"],
        scopes=["read", "write"],
    )


@contextmanager
def override_auth(client: TestClient, principal: Principal):
    client.app.dependency_overrides[require_auth] = lambda: principal
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(require_auth, None)


@contextmanager
def override_unauthorized(client: TestClient):
    async def _unauthorized():
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    client.app.dependency_overrides[require_auth] = _unauthorized
    try:
        yield
    finally:
        client.app.dependency_overrides.pop(require_auth, None)


def test_quarantine_unauthenticated_returns_401(client: TestClient):
    with override_unauthorized(client):
        response = client.post(
            "/api/genetic-quarantine/records",
            json={
                "agent_id": "agent-1",
                "snapshot_version": 1,
                "reason": "risk",
            },
        )
    assert response.status_code == 401


def test_quarantine_viewer_forbidden_403(client: TestClient, viewer_principal: Principal):
    with override_auth(client, viewer_principal):
        response = client.post(
            "/api/genetic-quarantine/records",
            json={
                "agent_id": "agent-1",
                "snapshot_version": 1,
                "reason": "risk",
            },
        )
    assert response.status_code == 403


def test_quarantine_operator_create_and_audit(client: TestClient, operator_principal: Principal):
    with override_auth(client, operator_principal):
        create = client.post(
            "/api/genetic-quarantine/records",
            json={
                "agent_id": "agent-1",
                "snapshot_version": 5,
                "reason": "Mutation risk spike",
                "requested_state": "quarantined",
                "severity": "high",
                "source": "immune_orchestrator",
                "correlation_id": "corr-api-gq-1",
            },
        )
        assert create.status_code == 200
        payload = create.json()["record"]
        assert payload["state"] == "quarantined"

        transition = client.post(
            "/api/genetic-quarantine/records/transition",
            json={
                "quarantine_id": payload["quarantine_id"],
                "target_state": "probation",
                "reason": "Controlled retry",
                "correlation_id": "corr-api-gq-1",
            },
        )
        assert transition.status_code == 200
        assert transition.json()["record"]["state"] == "probation"

        audit = client.get("/api/genetic-quarantine/audit")
        assert audit.status_code == 200
        entries = audit.json()["items"]
        assert len(entries) >= 2
        assert any(item["action"] == "quarantine" for item in entries)
        assert any(item["action"] == "transition" for item in entries)


def test_repair_unauthenticated_returns_401(client: TestClient):
    with override_unauthorized(client):
        response = client.post(
            "/api/opencode-repair/tickets/auto",
            json={
                "source_module": "immune_orchestrator",
                "source_event_type": "immune.decision",
                "subject_id": "sig-1",
                "summary": "Repair needed",
            },
        )
    assert response.status_code == 401


def test_repair_viewer_forbidden_403(client: TestClient, viewer_principal: Principal):
    with override_auth(client, viewer_principal):
        response = client.post(
            "/api/opencode-repair/tickets/auto",
            json={
                "source_module": "immune_orchestrator",
                "source_event_type": "immune.decision",
                "subject_id": "sig-1",
                "summary": "Repair needed",
            },
        )
    assert response.status_code == 403


def test_repair_operator_create_update_and_audit(client: TestClient, operator_principal: Principal):
    with override_auth(client, operator_principal):
        create = client.post(
            "/api/opencode-repair/tickets/auto",
            json={
                "source_module": "immune_orchestrator",
                "source_event_type": "immune.decision",
                "subject_id": "sig-9",
                "summary": "Escalated risk requires patch",
                "severity": "critical",
                "correlation_id": "corr-api-rt-1",
                "context": {"action": "escalate"},
            },
        )
        assert create.status_code == 200
        ticket = create.json()["ticket"]
        assert ticket["governance_required"] is True
        assert ticket["status"] == "open"

        update = client.post(
            "/api/opencode-repair/tickets/update",
            json={
                "ticket_id": ticket["ticket_id"],
                "status": "patch_proposed",
                "note": "Patch prepared",
                "evidence": {"patch_ref": "pr-123"},
            },
        )
        assert update.status_code == 200
        updated = update.json()["ticket"]
        assert updated["status"] == "patch_proposed"
        assert updated["evidence"]["patch_ref"] == "pr-123"

        audit = client.get("/api/opencode-repair/audit")
        assert audit.status_code == 200
        entries = audit.json()["items"]
        assert len(entries) >= 2
        assert any(item["action"] == "ticket_created" for item in entries)
        assert any(item["action"] == "ticket_updated" for item in entries)
