from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.evolution_control.router import router as evolution_router


def build_principal(*roles: str, tenant_id: str | None = "tenant-a") -> Principal:
    return Principal(
        principal_id="admin-1",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id=tenant_id,
    )


def test_evolution_create_get_transition(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(evolution_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.evolution_control.router", fromlist=["router"])
    proposal_id = uuid4()
    pattern_id = uuid4()
    now = datetime.now(timezone.utc)
    proposal = SimpleNamespace(
        id=proposal_id,
        tenant_id="tenant-a",
        pattern_id=pattern_id,
        skill_run_id=uuid4(),
        status="draft",
        target_skill_key="builder.webgenesis.generate",
        summary="Proposal",
        governance_required="true",
        validation_state="required",
        proposal_metadata={"pattern_confidence": 0.8},
        created_at=now,
        updated_at=now,
    )
    proposal_review = SimpleNamespace(**{**proposal.__dict__, "status": "review"})

    class FakeService:
        async def create_from_pattern(self, db, pattern_id_param, principal):
            assert pattern_id_param == pattern_id
            return proposal

        async def get_by_id(self, db, proposal_id_param, tenant_id):
            assert proposal_id_param == proposal_id
            assert tenant_id == "tenant-a"
            return proposal

        async def transition_status(self, db, proposal_id_param, principal, status):
            assert proposal_id_param == proposal_id
            assert status == "review"
            return proposal_review

    monkeypatch.setattr(route_module, "get_evolution_control_service", lambda: FakeService())

    create_response = client.post(f"/api/evolution/proposals/patterns/{pattern_id}")
    assert create_response.status_code == 201
    assert create_response.json()["proposal"]["id"] == str(proposal_id)

    get_response = client.get(f"/api/evolution/proposals/{proposal_id}")
    assert get_response.status_code == 200

    transition_response = client.post(
        f"/api/evolution/proposals/{proposal_id}/transition",
        json={"status": "review"},
    )
    assert transition_response.status_code == 200
    assert transition_response.json()["status"] == "review"


def test_evolution_transition_invalid_returns_400(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(evolution_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.evolution_control.router", fromlist=["router"])

    class FakeService:
        async def transition_status(self, db, proposal_id, principal, status):
            raise ValueError("Invalid proposal transition")

    monkeypatch.setattr(route_module, "get_evolution_control_service", lambda: FakeService())

    response = client.post(
        f"/api/evolution/proposals/{uuid4()}/transition",
        json={"status": "applied"},
    )
    assert response.status_code == 400


def test_evolution_requires_tenant_context() -> None:
    app = FastAPI()
    app.include_router(evolution_router)

    async def _db_override():
        yield None

    principal = build_principal("admin", "SYSTEM_ADMIN", tenant_id=None)
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    response = client.get(f"/api/evolution/proposals/{uuid4()}")
    assert response.status_code == 403
