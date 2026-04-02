from __future__ import annotations

from contextlib import contextmanager

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.external_apps import router as external_apps_router_module
from app.modules.external_apps.router import router as external_apps_router


def _principal(*roles: str) -> Principal:
    return Principal(
        principal_id="external-apps-user",
        principal_type=PrincipalType.HUMAN,
        email="external-apps@example.com",
        name="External Apps User",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id="tenant-a",
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
    app.include_router(external_apps_router)

    async def _fake_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_db
    return app


def test_paperclip_handoff_requires_authentication() -> None:
    client = TestClient(_build_test_app())
    with _override_unauthorized(client):
        response = client.post("/api/external-apps/paperclip/handoff", json={"target_type": "issue", "target_ref": "issue-1"})
    assert response.status_code == 401


def test_paperclip_handoff_returns_signed_url() -> None:
    class _FakeService:
        async def create_handoff(self, db, *, principal, payload, backend_base_url):  # noqa: ANN001
            _ = (db, principal, payload, backend_base_url)
            return {
                "handoff_url": "https://paperclip.example/handoff/paperclip?token=test-token",
                "expires_at": "2026-04-01T20:00:00+00:00",
                "jti": "handoff_test",
                "target_type": "issue",
                "target_ref": "issue-123",
            }

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("viewer")):
        response = client.post(
            "/api/external-apps/paperclip/handoff",
            json={"target_type": "issue", "target_ref": "issue-123", "permissions": ["view"]},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["target_type"] == "issue"
    assert body["target_ref"] == "issue-123"
    assert "token=test-token" in body["handoff_url"]


def test_paperclip_handoff_blocks_when_policy_denies() -> None:
    class _FakeService:
        async def create_handoff(self, db, *, principal, payload, backend_base_url):  # noqa: ANN001
            _ = (db, principal, payload, backend_base_url)
            raise PermissionError("Paperclip executor is currently disabled by runtime policy")

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("viewer")):
        response = client.post(
            "/api/external-apps/paperclip/handoff",
            json={"target_type": "issue", "target_ref": "issue-123"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Paperclip executor is currently disabled by runtime policy"


def test_paperclip_handoff_exchange_returns_validated_context() -> None:
    class _FakeService:
        async def exchange_handoff(self, db, *, payload):  # noqa: ANN001
            _ = (db, payload)
            return {
                "jti": "handoff_test",
                "principal_id": "external-apps-user",
                "tenant_id": "tenant-a",
                "skill_run_id": "run-1",
                "mission_id": "mission-1",
                "decision_id": "rdec-1",
                "correlation_id": "corr-1",
                "target_type": "execution",
                "target_ref": "task-1",
                "permissions": ["view"],
                "suggested_path": "/app/executions/task-1",
                "governance_banner": "Governed by BRAiN.",
                "expires_at": "2026-04-01T20:00:00+00:00",
            }

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("viewer")):
        response = client.post(
            "/api/external-apps/paperclip/handoff/exchange",
            json={"token": "test-token-value-123456"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["target_type"] == "execution"
    assert body["suggested_path"] == "/app/executions/task-1"


def test_paperclip_handoff_exchange_replay_returns_conflict() -> None:
    calls = []

    class _FakeService:
        async def exchange_handoff(self, db, *, payload):  # noqa: ANN001
            _ = (db, payload)
            raise PermissionError("Handoff token already consumed")

        async def record_exchange_failure(self, db, *, payload, reason):  # noqa: ANN001
            _ = (db, payload)
            calls.append(reason)

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    response = client.post(
        "/api/external-apps/paperclip/handoff/exchange",
        json={"token": "test-token-value-123456"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Handoff token already consumed"
    assert calls == ["Handoff token already consumed"]


def test_paperclip_execution_context_returns_canonical_data() -> None:
    class _FakeService:
        async def get_execution_context(self, db, *, task_id, principal):  # noqa: ANN001
            _ = (db, principal)
            return {
                "target_type": "execution",
                "target_ref": task_id,
                "task": {
                    "id": "00000000-0000-0000-0000-000000000001",
                    "task_id": task_id,
                    "name": "Paperclip TaskLease",
                    "description": None,
                    "task_type": "paperclip_work",
                    "category": None,
                    "tags": ["tasklease"],
                    "status": "completed",
                    "priority": 75,
                    "payload": {},
                    "config": {},
                    "tenant_id": "tenant-a",
                    "mission_id": "mission-1",
                    "skill_run_id": "00000000-0000-0000-0000-000000000002",
                    "correlation_id": "corr-1",
                    "scheduled_at": None,
                    "deadline_at": None,
                    "claimed_by": None,
                    "claimed_at": None,
                    "started_at": None,
                    "completed_at": None,
                    "max_retries": 0,
                    "retry_count": 0,
                    "result": None,
                    "error_message": None,
                    "execution_time_ms": None,
                    "wait_time_ms": None,
                    "created_by": None,
                    "created_at": "2026-04-01T20:00:00+00:00",
                    "updated_at": "2026-04-01T20:00:00+00:00",
                },
                "skill_run": None,
                "governance_banner": "Governed by BRAiN. Sensitive actions require BRAiN approval.",
            }

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("viewer")):
        response = client.get("/api/external-apps/paperclip/executions/task-123")

    assert response.status_code == 200
    body = response.json()
    assert body["target_ref"] == "task-123"
    assert body["task"]["task_id"] == "task-123"


def test_paperclip_execution_context_returns_not_found() -> None:
    class _FakeService:
        async def get_execution_context(self, db, *, task_id, principal):  # noqa: ANN001
            _ = (db, task_id, principal)
            raise ValueError("Task task-404 not found")

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("viewer")):
        response = client.get("/api/external-apps/paperclip/executions/task-404")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task task-404 not found"


def test_paperclip_action_request_returns_requested() -> None:
    class _FakeService:
        async def request_action(self, db, *, payload):  # noqa: ANN001
            _ = (db, payload)
            return {
                "request_id": "actreq_123",
                "action": "request_retry",
                "status": "requested",
                "target_ref": "task-123",
                "skill_run_id": "run-123",
                "message": "Retry request recorded for operator review.",
            }

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    response = client.post(
        "/api/external-apps/paperclip/actions",
        json={"token": "test-token-value-123456", "action": "request_retry", "reason": "Please retry"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "actreq_123"
    assert body["action"] == "request_retry"


def test_paperclip_action_request_rejects_forbidden_permission() -> None:
    class _FakeService:
        async def request_action(self, db, *, payload):  # noqa: ANN001
            _ = (db, payload)
            raise PermissionError("Handoff token does not permit request_retry")

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    response = client.post(
        "/api/external-apps/paperclip/actions",
        json={"token": "test-token-value-123456", "action": "request_retry", "reason": "Please retry"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Handoff token does not permit request_retry"


def test_list_paperclip_action_requests_returns_items() -> None:
    class _FakeService:
        async def list_action_requests(self, db, *, principal):  # noqa: ANN001
            _ = (db, principal)
            return {
                "items": [
                    {
                        "request_id": "actreq_1",
                        "tenant_id": "tenant-a",
                        "principal_id": "operator-1",
                        "action": "request_retry",
                        "reason": "retry",
                        "status": "pending",
                        "target_type": "execution",
                        "target_ref": "task-1",
                        "skill_run_id": "run-1",
                        "mission_id": "mission-1",
                        "decision_id": "rdec-1",
                        "correlation_id": "corr-1",
                        "created_at": "2026-04-01T20:00:00+00:00",
                        "updated_at": "2026-04-01T20:00:00+00:00",
                        "execution_result": {},
                    }
                ],
                "total": 1,
            }

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("operator")):
        response = client.get("/api/external-apps/paperclip/action-requests")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_approve_paperclip_action_request_returns_item() -> None:
    class _FakeService:
        async def approve_action_request(self, db, *, principal, request_id, payload):  # noqa: ANN001
            _ = (db, principal, payload)
            return {
                "request_id": request_id,
                "tenant_id": "tenant-a",
                "principal_id": "operator-1",
                "action": "request_retry",
                "reason": "retry",
                "status": "approved",
                "target_type": "execution",
                "target_ref": "task-1",
                "skill_run_id": "run-1",
                "mission_id": "mission-1",
                "decision_id": "rdec-1",
                "correlation_id": "corr-1",
                "created_at": "2026-04-01T20:00:00+00:00",
                "updated_at": "2026-04-01T20:01:00+00:00",
                "approved_by": "operator-1",
                "approved_at": "2026-04-01T20:01:00+00:00",
                "decision_reason": "approved",
                "execution_result": {"new_task_id": "task-2"},
            }

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("operator")):
        response = client.post(
            "/api/external-apps/paperclip/action-requests/actreq_1/approve",
            json={"reason": "approved"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_reject_paperclip_action_request_returns_conflict() -> None:
    class _FakeService:
        async def reject_action_request(self, db, *, principal, request_id, payload):  # noqa: ANN001
            _ = (db, principal, request_id, payload)
            raise ValueError("Action request is not pending")

    external_apps_router_module.get_paperclip_handoff_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("operator")):
        response = client.post(
            "/api/external-apps/paperclip/action-requests/actreq_1/reject",
            json={"reason": "rejected"},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == "Action request is not pending"
