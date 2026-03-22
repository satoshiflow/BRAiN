from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.experience_layer.router import router as experience_layer_router


def build_principal(*roles: str) -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


def test_experience_ingest_and_get(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(experience_layer_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    principal = build_principal("operator", "admin")
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.experience_layer.router", fromlist=["router"])
    run_id = uuid4()
    exp_id = uuid4()
    record = SimpleNamespace(
        id=exp_id,
        tenant_id="tenant-a",
        skill_run_id=run_id,
        evaluation_result_id=None,
        idempotency_key=f"experience:tenant-a:{run_id}",
        state="succeeded",
        failure_code=None,
        summary="SkillRun builder.webgenesis.generate completed",
        evaluation_summary={"score": 0.91},
        signals={"skill_key": "builder.webgenesis.generate"},
        created_at=datetime.now(timezone.utc),
    )

    class FakeService:
        async def ingest_skill_run(self, db, skill_run_id, principal):
            assert skill_run_id == run_id
            assert principal.tenant_id == "tenant-a"
            return record

        async def get_by_id(self, db, experience_id, tenant_id):
            assert experience_id == exp_id
            assert tenant_id == "tenant-a"
            return record

        async def get_by_skill_run_id(self, db, skill_run_id, tenant_id):
            assert skill_run_id == run_id
            assert tenant_id == "tenant-a"
            return record

    monkeypatch.setattr(route_module, "get_experience_layer_service", lambda: FakeService())

    ingest_response = client.post(f"/api/experience/skill-runs/{run_id}/ingest")
    assert ingest_response.status_code == 201
    assert ingest_response.json()["experience"]["id"] == str(exp_id)

    by_id_response = client.get(f"/api/experience/{exp_id}")
    assert by_id_response.status_code == 200
    assert by_id_response.json()["skill_run_id"] == str(run_id)

    by_run_response = client.get(f"/api/experience/skill-runs/{run_id}")
    assert by_run_response.status_code == 200
    assert by_run_response.json()["id"] == str(exp_id)


def test_experience_ingest_returns_not_found(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(experience_layer_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    principal = build_principal("operator", "admin")
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.experience_layer.router", fromlist=["router"])

    class FakeService:
        async def ingest_skill_run(self, db, skill_run_id, principal):
            raise ValueError("Skill run not found")

    monkeypatch.setattr(route_module, "get_experience_layer_service", lambda: FakeService())

    response = client.post(f"/api/experience/skill-runs/{uuid4()}/ingest")
    assert response.status_code == 404


def test_experience_write_blocked_when_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(experience_layer_router)

    fake_db = object()

    async def _db_override():
        yield fake_db

    principal = build_principal("operator", "admin")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.experience_layer.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "experience_layer"
            return SimpleNamespace(lifecycle_status="retired")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    response = client.post(f"/api/experience/skill-runs/{uuid4()}/ingest")
    assert response.status_code == 409


def test_experience_requires_tenant_context() -> None:
    app = FastAPI()
    app.include_router(experience_layer_router)

    async def _db_override():
        yield None

    principal = Principal(
        principal_id="system-admin-1",
        principal_type=PrincipalType.HUMAN,
        email="sysadmin@example.com",
        name="SysAdmin",
        roles=["system_admin"],
        scopes=["read", "write"],
        tenant_id=None,
    )

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    response = client.post(f"/api/experience/skill-runs/{uuid4()}/ingest")
    assert response.status_code == 403
