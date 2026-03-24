from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.consolidation_layer.router import router as consolidation_router


def build_principal(*roles: str, tenant_id: str | None = "tenant-a") -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id=tenant_id,
    )


def test_consolidation_derive_and_get(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(consolidation_router)

    async def _db_override():
        yield None

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.consolidation_layer.router", fromlist=["router"])
    run_id = uuid4()
    pattern_id = uuid4()
    now = datetime.now(timezone.utc)
    pattern = SimpleNamespace(
        id=pattern_id,
        tenant_id="tenant-a",
        insight_id=uuid4(),
        skill_run_id=run_id,
        status="proposed",
        confidence=0.8,
        recurrence_support=0.7,
        pattern_summary="Pattern from insight",
        failure_modes=[],
        evidence={"insight_id": "x"},
        created_at=now,
        updated_at=now,
    )

    class FakeService:
        async def derive_from_skill_run(self, db, skill_run_id, principal):
            assert skill_run_id == run_id
            return pattern

        async def get_by_id(self, db, pattern_id_param, tenant_id):
            assert pattern_id_param == pattern_id
            assert tenant_id == "tenant-a"
            return pattern

        async def get_by_skill_run_id(self, db, skill_run_id_param, tenant_id):
            assert skill_run_id_param == run_id
            assert tenant_id == "tenant-a"
            return pattern

    monkeypatch.setattr(route_module, "get_consolidation_layer_service", lambda: FakeService())

    derive_response = client.post(f"/api/consolidation/skill-runs/{run_id}/derive")
    assert derive_response.status_code == 201
    assert derive_response.json()["pattern"]["id"] == str(pattern_id)

    by_id_response = client.get(f"/api/consolidation/{pattern_id}")
    assert by_id_response.status_code == 200

    by_run_response = client.get(f"/api/consolidation/skill-runs/{run_id}")
    assert by_run_response.status_code == 200


def test_consolidation_write_blocked_when_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(consolidation_router)
    fake_db = object()

    async def _db_override():
        yield fake_db

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.consolidation_layer.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "consolidation_layer"
            return SimpleNamespace(lifecycle_status="retired")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    response = client.post(f"/api/consolidation/skill-runs/{uuid4()}/derive")
    assert response.status_code == 409
