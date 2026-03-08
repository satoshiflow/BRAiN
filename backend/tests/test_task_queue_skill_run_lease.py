from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.task_queue.router import router as task_queue_router


def build_principal() -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator"],
        scopes=["write"],
        tenant_id="tenant-a",
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


def test_skill_run_lease_route_requires_authentication(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(task_queue_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    client = TestClient(app)

    with override_auth_unauthorized(client):
        response = client.post(f"/api/tasks/skill-runs/{uuid4()}/lease")

    assert response.status_code == 401


def test_skill_run_lease_route_returns_created_task(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(task_queue_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    client = TestClient(app)
    principal = build_principal()

    router_module = __import__("app.modules.task_queue.router", fromlist=["router"])
    run_id = uuid4()
    task_id = uuid4()

    class FakeSkillEngineService:
        async def get_run(self, db, run_id_arg, tenant_id):
            assert run_id_arg == run_id
            assert tenant_id == principal.tenant_id
            return SimpleNamespace(
                id=run_id,
                skill_key="builder.webgenesis.generate",
                skill_version=1,
                tenant_id=tenant_id,
                mission_id=None,
                correlation_id="corr-1",
                deadline_at=None,
            )

    class FakeTaskQueueService:
        async def create_task_lease_for_skill_run(self, db, run, principal_arg):
            assert run.id == run_id
            assert principal_arg.principal_id == principal.principal_id
            return SimpleNamespace(
                id=task_id,
                task_id="task-lease-1",
                name="SkillRun lease: builder.webgenesis.generate",
                description="Worker lease",
                task_type="skill_run_lease",
                category="skill_engine",
                tags=["skillrun", "builder.webgenesis.generate"],
                status="pending",
                priority=75,
                payload={"skill_run_id": str(run_id)},
                config={"lease_only": True},
                tenant_id=principal.tenant_id,
                mission_id=None,
                skill_run_id=run_id,
                correlation_id="corr-1",
                scheduled_at=None,
                deadline_at=None,
                claimed_by=None,
                claimed_at=None,
                started_at=None,
                completed_at=None,
                max_retries=3,
                retry_count=0,
                result=None,
                error_message=None,
                execution_time_ms=None,
                wait_time_ms=None,
                created_by=principal.principal_id,
                created_at="2026-03-08T00:00:00Z",
                updated_at="2026-03-08T00:00:00Z",
            )

    monkeypatch.setattr(router_module, "get_skill_engine_service", lambda: FakeSkillEngineService())
    monkeypatch.setattr(router_module, "get_task_queue_service", lambda: FakeTaskQueueService())

    with override_auth_principal(client, principal):
        response = client.post(f"/api/tasks/skill-runs/{run_id}/lease")

    assert response.status_code == 201
    body = response.json()
    assert body["skill_run_id"] == str(run_id)
    assert body["task"]["task_id"] == "task-lease-1"
    assert body["task"]["skill_run_id"] == str(run_id)
