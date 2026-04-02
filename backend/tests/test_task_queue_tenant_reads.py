from __future__ import annotations

import importlib
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.task_queue.router import router as task_queue_router
from app.modules.task_queue.schemas import TaskResponse, TaskStatus


task_queue_router_module = importlib.import_module("app.modules.task_queue.router")


def _principal(*roles: str, tenant_id: str | None) -> Principal:
    return Principal(
        principal_id="task-reader",
        principal_type=PrincipalType.HUMAN,
        email="task-reader@example.com",
        name="Task Reader",
        roles=list(roles),
        scopes=["read"],
        tenant_id=tenant_id,
    )


def _task(task_id: str, tenant_id: str | None) -> TaskResponse:
    now = datetime.now(timezone.utc)
    return TaskResponse(
        id=uuid4(),
        task_id=task_id,
        name=f"Task {task_id}",
        description=None,
        task_type="paperclip_work",
        category=None,
        tags=[],
        status=TaskStatus.PENDING,
        priority=50,
        payload={},
        config={},
        tenant_id=tenant_id,
        mission_id=None,
        skill_run_id=None,
        correlation_id=None,
        scheduled_at=None,
        deadline_at=None,
        claimed_by=None,
        claimed_at=None,
        started_at=None,
        completed_at=None,
        max_retries=0,
        retry_count=0,
        result=None,
        error_message=None,
        execution_time_ms=None,
        wait_time_ms=None,
        created_by=None,
        created_at=now,
        updated_at=now,
    )


@contextmanager
def _override_principal(client: TestClient, principal: Principal):
    async def _principal_override() -> Principal:
        return principal

    app = client.app
    app.dependency_overrides[require_auth] = _principal_override
    app.dependency_overrides[get_current_principal] = _principal_override
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)
        app.dependency_overrides.pop(get_current_principal, None)


@contextmanager
def _override_unauthorized(client: TestClient):
    async def _unauthorized() -> Principal:
        raise HTTPException(status_code=401, detail="Authentication required")

    app = client.app
    app.dependency_overrides[require_auth] = _unauthorized
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(task_queue_router)

    async def _fake_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_db
    return app


def test_list_tasks_is_tenant_scoped_for_non_admin_reads() -> None:
    class _FakeService:
        async def get_tasks(self, db, status=None, task_type=None, limit=100, offset=0):  # noqa: ANN001
            _ = (db, status, task_type, limit, offset)
            return [
                _task("task-tenant-a", "tenant-a"),
                _task("task-tenant-b", "tenant-b"),
                _task("task-system", None),
            ]

    original = task_queue_router_module.get_task_queue_service
    task_queue_router_module.get_task_queue_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    try:
        with _override_principal(client, _principal("viewer", tenant_id="tenant-a")):
            response = client.get("/api/tasks")
    finally:
        task_queue_router_module.get_task_queue_service = original

    assert response.status_code == 200
    body = response.json()
    assert [item["task_id"] for item in body["items"]] == ["task-tenant-a", "task-system"]
    assert body["total"] == 2


def test_get_task_hides_other_tenant_when_reader_has_no_cross_tenant_role() -> None:
    class _FakeService:
        async def get_task(self, db, task_id):  # noqa: ANN001
            _ = (db, task_id)
            return _task("task-tenant-b", "tenant-b")

    original = task_queue_router_module.get_task_queue_service
    task_queue_router_module.get_task_queue_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    try:
        with _override_principal(client, _principal("viewer", tenant_id="tenant-a")):
            response = client.get("/api/tasks/task-tenant-b")
    finally:
        task_queue_router_module.get_task_queue_service = original

    assert response.status_code == 404


def test_list_tasks_requires_authentication() -> None:
    client = TestClient(_build_test_app())
    with _override_unauthorized(client):
        response = client.get("/api/tasks")
    assert response.status_code == 401
