from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.insight_layer.router import router as insight_layer_router


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


def test_insight_derive_and_get(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(insight_layer_router)

    async def _db_override():
        yield None

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.insight_layer.router", fromlist=["router"])
    run_id = uuid4()
    insight_id = uuid4()
    now = datetime.now(timezone.utc)
    insight = SimpleNamespace(
        id=insight_id,
        tenant_id="tenant-a",
        experience_id=uuid4(),
        skill_run_id=run_id,
        status="proposed",
        confidence=0.8,
        scope="skill_run",
        hypothesis="Run pattern",
        evidence={"experience_state": "succeeded"},
        created_at=now,
        updated_at=now,
    )

    class FakeService:
        async def derive_from_skill_run(self, db, skill_run_id, principal):
            assert skill_run_id == run_id
            assert principal.tenant_id == "tenant-a"
            return insight

        async def get_by_id(self, db, insight_id_param, tenant_id):
            assert insight_id_param == insight_id
            assert tenant_id == "tenant-a"
            return insight

        async def get_by_skill_run_id(self, db, skill_run_id_param, tenant_id):
            assert skill_run_id_param == run_id
            assert tenant_id == "tenant-a"
            return insight

    monkeypatch.setattr(route_module, "get_insight_layer_service", lambda: FakeService())

    derive_response = client.post(f"/api/insights/skill-runs/{run_id}/derive")
    assert derive_response.status_code == 201
    assert derive_response.json()["insight"]["id"] == str(insight_id)

    by_id_response = client.get(f"/api/insights/{insight_id}")
    assert by_id_response.status_code == 200

    by_run_response = client.get(f"/api/insights/skill-runs/{run_id}")
    assert by_run_response.status_code == 200


def test_insight_write_blocked_when_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(insight_layer_router)
    fake_db = object()

    async def _db_override():
        yield fake_db

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.insight_layer.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "insight_layer"
            return SimpleNamespace(lifecycle_status="retired")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    response = client.post(f"/api/insights/skill-runs/{uuid4()}/derive")
    assert response.status_code == 409


def test_insight_requires_tenant_context() -> None:
    app = FastAPI()
    app.include_router(insight_layer_router)

    async def _db_override():
        yield None

    principal = build_principal("operator", tenant_id=None)
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    response = client.post(f"/api/insights/skill-runs/{uuid4()}/derive")
    assert response.status_code == 403
