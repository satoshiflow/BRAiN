from __future__ import annotations

from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.missions import router as legacy_missions_router
from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.missions.router import router as mission_templates_router


def _principal() -> Principal:
    return Principal(
        principal_id="operator-1",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator", "admin"],
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


def test_legacy_mission_enqueue_blocked_when_module_retired(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(legacy_missions_router)
    fake_db = object()

    async def _db_override():
        yield fake_db

    app.dependency_overrides[get_db] = _db_override
    client = TestClient(app)

    route_module = __import__("api.routes.missions", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "missions"
            return SimpleNamespace(lifecycle_status="retired")

    class FailIfCalledRuntime:
        async def enqueue_mission(self, payload, created_by):  # pragma: no cover
            raise AssertionError("runtime enqueue should not be called when lifecycle blocks writes")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())
    monkeypatch.setattr(route_module, "get_mission_runtime", lambda: FailIfCalledRuntime())

    response = client.post(
        "/api/missions/enqueue",
        json={"type": "agent.chat", "payload": {"message": "hello"}, "priority": 20, "created_by": "pytest"},
    )
    assert response.status_code == 409


def test_mission_templates_create_blocked_when_deprecated(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(mission_templates_router)
    fake_db = object()
    principal = _principal()

    async def _db_override():
        yield fake_db

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.missions.router", fromlist=["router"])

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert db is fake_db
            assert module_id == "missions"
            return SimpleNamespace(lifecycle_status="deprecated")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    response = client.post(
        "/api/missions/templates",
        json={
            "name": "Blocked Template",
            "description": "write should be blocked",
            "category": "general",
            "steps": [{"order": 1, "action": "noop", "config": {}}],
            "variables": {},
        },
    )
    assert response.status_code == 409
