from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.runtime_control import router as runtime_control_router_module
from app.modules.runtime_control.router import router as runtime_control_router


def _principal(*roles: str) -> Principal:
    return Principal(
        principal_id="runtime-control-user",
        principal_type=PrincipalType.HUMAN,
        email="runtime-control@example.com",
        name="Runtime Control User",
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


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(runtime_control_router)

    async def _fake_db():
        yield object()

    app.dependency_overrides[get_db] = _fake_db
    return app


def test_create_override_request_operator_allowed() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = []

        async def create_override_request(self, db, *, principal, payload):  # noqa: ANN001
            _ = db
            return {
                "request_id": "rov_1",
                "tenant_id": principal.tenant_id,
                "tenant_scope": payload.tenant_scope,
                "key": payload.key,
                "value": payload.value,
                "reason": payload.reason,
                "status": "pending",
                "created_by": principal.principal_id,
                "created_at": "2026-04-01T10:00:00+00:00",
                "updated_at": "2026-04-01T10:00:00+00:00",
            }

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("operator")):
        response = client.post(
            "/api/runtime-control/overrides/requests",
            json={
                "key": "workers.selection.default_executor",
                "value": "openclaw",
                "reason": "maintenance lane",
                "tenant_scope": "tenant",
            },
        )

    assert response.status_code == 201
    assert response.json()["request_id"] == "rov_1"


def test_create_override_request_viewer_forbidden() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = []

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("viewer")):
        response = client.post(
            "/api/runtime-control/overrides/requests",
            json={
                "key": "workers.selection.default_executor",
                "value": "openclaw",
                "reason": "maintenance lane",
                "tenant_scope": "tenant",
            },
        )

    assert response.status_code == 403


def test_approve_override_request_admin_only() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = []

        async def approve_override_request(self, db, *, principal, request_id, payload):  # noqa: ANN001
            _ = (db, principal, request_id, payload)
            return {
                "request_id": "rov_2",
                "tenant_id": "tenant-a",
                "tenant_scope": "tenant",
                "key": "routing.llm.default_provider",
                "value": "ollama",
                "reason": "risk control",
                "status": "approved",
                "created_by": "operator-1",
                "created_at": "2026-04-01T10:00:00+00:00",
                "updated_at": "2026-04-01T11:00:00+00:00",
                "approved_by": "admin-1",
                "approved_at": "2026-04-01T11:00:00+00:00",
                "decision_reason": "approved for incident",
            }

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("admin")):
        response = client.post(
            "/api/runtime-control/overrides/requests/rov_2/approve",
            json={"reason": "approved for incident"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_reject_override_request_operator_forbidden() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = []

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("operator")):
        response = client.post(
            "/api/runtime-control/overrides/requests/rov_3/reject",
            json={"reason": "reject"},
        )

    assert response.status_code == 403


def test_list_active_overrides_returns_data() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = []

        async def list_active_overrides(self, db, *, tenant_id):  # noqa: ANN001
            _ = (db, tenant_id)
            return {
                "items": [
                    {
                        "request_id": "rov_4",
                        "key": "workers.selection.default_executor",
                        "value": "openclaw",
                        "reason": "approved maintenance",
                        "tenant_id": "tenant-a",
                        "expires_at": None,
                    }
                ],
                "total": 1,
            }

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("viewer")):
        response = client.get("/api/runtime-control/overrides/active")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_registry_version_flow_endpoints() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = []

        async def list_registry_versions(self, db, *, tenant_id):  # noqa: ANN001
            _ = (db, tenant_id)
            return {
                "items": [
                    {
                        "version_id": "rcv_1",
                        "scope": "tenant",
                        "tenant_id": "tenant-a",
                        "status": "draft",
                        "config_patch": {"routing": {"llm": {"default_provider": "ollama"}}},
                        "reason": "baseline",
                        "created_by": "operator-1",
                        "created_at": "2026-04-01T10:00:00+00:00",
                        "updated_at": "2026-04-01T10:00:00+00:00",
                    }
                ],
                "total": 1,
            }

        async def create_registry_version(self, db, *, principal, payload):  # noqa: ANN001
            _ = (db, principal)
            return {
                "version_id": "rcv_2",
                "scope": payload.scope,
                "tenant_id": "tenant-a",
                "status": "draft",
                "config_patch": payload.config_patch,
                "reason": payload.reason,
                "created_by": "operator-1",
                "created_at": "2026-04-01T10:00:00+00:00",
                "updated_at": "2026-04-01T10:00:00+00:00",
            }

        async def promote_registry_version(self, db, *, principal, version_id, payload):  # noqa: ANN001
            _ = (db, principal, payload)
            return {
                "version_id": version_id,
                "scope": "tenant",
                "tenant_id": "tenant-a",
                "status": "promoted",
                "config_patch": {"routing": {"llm": {"default_provider": "openrouter"}}},
                "reason": "baseline",
                "created_by": "operator-1",
                "created_at": "2026-04-01T10:00:00+00:00",
                "updated_at": "2026-04-01T11:00:00+00:00",
                "promoted_by": "admin-1",
                "promoted_at": "2026-04-01T11:00:00+00:00",
                "promotion_reason": "promote",
            }

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("operator")):
        created = client.post(
            "/api/runtime-control/registry/versions",
            json={
                "scope": "tenant",
                "config_patch": {"routing": {"llm": {"default_provider": "openrouter"}}},
                "reason": "baseline",
            },
        )
        listed = client.get("/api/runtime-control/registry/versions")

    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    with _override_principal(client, _principal("admin")):
        promoted = client.post(
            "/api/runtime-control/registry/versions/rcv_2/promote",
            json={"reason": "promote"},
        )
    assert promoted.status_code == 200
    assert promoted.json()["status"] == "promoted"


def test_runtime_control_timeline_endpoint() -> None:
    class _FakeService:
        OVERRIDE_PRIORITY = []

        async def list_timeline(self, db, *, tenant_id, limit):  # noqa: ANN001
            _ = (db, tenant_id, limit)
            return {
                "items": [
                    {
                        "event_id": "evt-1",
                        "event_type": "runtime.override.request.created.v1",
                        "entity_type": "runtime_override_request",
                        "entity_id": "rov_1",
                        "actor_id": "operator-1",
                        "actor_type": "human",
                        "tenant_id": "tenant-a",
                        "correlation_id": "rov_1",
                        "created_at": "2026-04-01T10:00:00+00:00",
                        "payload": {},
                    }
                ],
                "total": 1,
            }

    runtime_control_router_module.get_runtime_control_service = lambda: _FakeService()
    client = TestClient(_build_test_app())
    with _override_principal(client, _principal("viewer")):
        response = client.get("/api/runtime-control/timeline?limit=50")
    assert response.status_code == 200
    assert response.json()["total"] == 1
