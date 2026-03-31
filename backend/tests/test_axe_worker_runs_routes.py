from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.modules.axe_worker_runs.router import get_service
from app.modules.axe_worker_runs.schemas import AXEWorkerRunResponse
from app.modules.axe_worker_runs.service import BoundedApplyPermissionError


class _FakeWorkerService:
    def __init__(self) -> None:
        self.items: dict[str, AXEWorkerRunResponse] = {}

    async def create_worker_run(self, *, principal, payload):  # noqa: ANN001
        _ = principal
        if payload.session_id.hex == "0" * 32:
            raise PermissionError("Session not found")
        if payload.message_id.hex == "f" * 32:
            raise LookupError("Message not found")
        item = AXEWorkerRunResponse(
            worker_run_id=f"wr_{uuid4().hex[:8]}",
            session_id=payload.session_id,
            message_id=payload.message_id,
            worker_type=getattr(payload, "worker_type", "auto"),
            activity_source="worker_run",
            status="queued",
            label="OpenCode worker queued",
            detail="Job accepted by BRAiN orchestrator",
            updated_at=datetime.now(timezone.utc),
            artifacts=[],
        )
        self.items[item.worker_run_id] = item
        return item

    async def get_worker_run(self, *, principal, worker_run_id):  # noqa: ANN001
        _ = principal
        return self.items.get(worker_run_id)

    async def list_worker_runs_for_session(self, *, principal, session_id):  # noqa: ANN001
        _ = principal
        if str(session_id).startswith("00000000"):
            raise PermissionError("Session not found")
        return [item for item in self.items.values() if str(item.session_id) == str(session_id)]

    async def approve_worker_run(self, *, principal, worker_run_id, approval_reason):  # noqa: ANN001
        _ = principal, approval_reason
        item = self.items.get(worker_run_id)
        if item is None:
            raise PermissionError("Worker run not found")
        return item.model_copy(update={"status": "completed", "detail": "approved"})

    async def reject_worker_run(self, *, principal, worker_run_id, rejection_reason):  # noqa: ANN001
        _ = principal, rejection_reason
        item = self.items.get(worker_run_id)
        if item is None:
            raise PermissionError("Worker run not found")
        return item.model_copy(update={"status": "failed", "detail": "rejected"})


def _principal() -> Principal:
    return Principal(
        principal_id="axe-user",
        principal_type=PrincipalType.HUMAN,
        email="axe@example.com",
        name="AXE User",
        roles=["operator"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


@contextmanager
def _override_unauthorized(test_app):
    async def _unauthorized():
        raise HTTPException(status_code=401, detail="Authentication required")

    test_app.dependency_overrides[require_auth] = _unauthorized
    try:
        yield
    finally:
        test_app.dependency_overrides.pop(require_auth, None)


def test_create_worker_run_route(client, test_app):
    service = _FakeWorkerService()
    test_app.dependency_overrides[get_service] = lambda: service

    payload = {
        "session_id": str(uuid4()),
        "message_id": str(uuid4()),
        "prompt": "Fix failing tests",
        "mode": "plan",
    }
    response = client.post("/api/axe/workers", json=payload)
    test_app.dependency_overrides.pop(get_service, None)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "queued"
    assert body["worker_run_id"].startswith("wr_")


def test_get_worker_run_route_not_found(client, test_app):
    service = _FakeWorkerService()
    test_app.dependency_overrides[get_service] = lambda: service

    response = client.get("/api/axe/workers/wr_missing")
    test_app.dependency_overrides.pop(get_service, None)

    assert response.status_code == 404


def test_list_worker_runs_for_session_route(client, test_app):
    service = _FakeWorkerService()
    run = AXEWorkerRunResponse(
        worker_run_id="wr_1234",
        session_id=uuid4(),
        message_id=uuid4(),
        worker_type="opencode",
        activity_source="worker_run",
        status="running",
        label="OpenCode worker active",
        detail="Working",
        updated_at=datetime.now(timezone.utc),
        artifacts=[],
    )
    service.items[run.worker_run_id] = run
    test_app.dependency_overrides[get_service] = lambda: service

    response = client.get(f"/api/axe/sessions/{run.session_id}/workers")
    test_app.dependency_overrides.pop(get_service, None)

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["worker_run_id"] == "wr_1234"


def test_worker_routes_require_auth(client, test_app):
    with _override_unauthorized(test_app):
        response = client.get("/api/axe/workers/wr_any")

    assert response.status_code == 401


def test_approve_worker_run_route(client, test_app):
    service = _FakeWorkerService()
    run = AXEWorkerRunResponse(
        worker_run_id="wr_waiting",
        session_id=uuid4(),
        message_id=uuid4(),
        worker_type="miniworker",
        activity_source="worker_run",
        status="waiting_input",
        label="Waiting",
        detail="Awaiting approval",
        updated_at=datetime.now(timezone.utc),
        artifacts=[],
    )
    service.items[run.worker_run_id] = run
    test_app.dependency_overrides[get_service] = lambda: service

    response = client.post(f"/api/axe/workers/{run.worker_run_id}/approve", json={"approval_reason": "approved"})
    test_app.dependency_overrides.pop(get_service, None)

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_reject_worker_run_route(client, test_app):
    service = _FakeWorkerService()
    run = AXEWorkerRunResponse(
        worker_run_id="wr_waiting",
        session_id=uuid4(),
        message_id=uuid4(),
        worker_type="miniworker",
        activity_source="worker_run",
        status="waiting_input",
        label="Waiting",
        detail="Awaiting approval",
        updated_at=datetime.now(timezone.utc),
        artifacts=[],
    )
    service.items[run.worker_run_id] = run
    test_app.dependency_overrides[get_service] = lambda: service

    response = client.post(f"/api/axe/workers/{run.worker_run_id}/reject", json={"rejection_reason": "rejected"})
    test_app.dependency_overrides.pop(get_service, None)

    assert response.status_code == 200
    assert response.json()["status"] == "failed"


def test_create_worker_run_route_rejects_openclaw_parallel_path(client, test_app):
    class _RejectingService(_FakeWorkerService):
        async def create_worker_run(self, *, principal, payload):  # noqa: ANN001
            _ = principal
            _ = payload
            raise ValueError("openclaw worker runs must use SkillRun/TaskLease runtime path")

    test_app.dependency_overrides[get_service] = lambda: _RejectingService()
    payload = {
        "session_id": str(uuid4()),
        "message_id": str(uuid4()),
        "prompt": "Use openclaw",
        "mode": "plan",
        "worker_type": "openclaw",
    }

    response = client.post("/api/axe/workers", json=payload)
    test_app.dependency_overrides.pop(get_service, None)

    assert response.status_code == 422


def test_approve_worker_run_route_returns_403_on_bounded_apply_permission_error(client, test_app):
    class _RejectingService(_FakeWorkerService):
        async def approve_worker_run(self, *, principal, worker_run_id, approval_reason):  # noqa: ANN001
            _ = principal, worker_run_id, approval_reason
            raise BoundedApplyPermissionError("bounded_apply approval requires operator/admin role")

    test_app.dependency_overrides[get_service] = lambda: _RejectingService()
    response = client.post(f"/api/axe/workers/wr_waiting/approve", json={"approval_reason": "approved"})
    test_app.dependency_overrides.pop(get_service, None)

    assert response.status_code == 403
