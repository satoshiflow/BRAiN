from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.observer_core.router import router as observer_core_router


def build_principal(*roles: str, tenant_id: str | None = "tenant-a") -> Principal:
    return Principal(
        principal_id="viewer-1",
        principal_type=PrincipalType.HUMAN,
        email="viewer@example.com",
        name="Viewer",
        roles=list(roles),
        scopes=["read"],
        tenant_id=tenant_id,
    )


def test_observer_list_and_summary(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(observer_core_router)

    async def _db_override():
        yield None

    principal = build_principal("viewer", "operator")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.observer_core.router", fromlist=["router"])
    signal_id = uuid4()
    now = datetime.now(timezone.utc)
    signal = SimpleNamespace(
        id=signal_id,
        tenant_id="tenant-a",
        source_module="skill_engine",
        source_event_type="skill.run.completed.v1",
        source_event_id="evt-1",
        correlation_id="corr-1",
        entity_type="skill_run",
        entity_id="run-1",
        signal_class="state_change",
        severity="info",
        occurred_at=now,
        ingested_at=now,
        payload={"state": "succeeded"},
        payload_hash="abc123",
        ordering_key="run-1:1",
    )
    state = SimpleNamespace(
        id=uuid4(),
        tenant_id="tenant-a",
        scope_type="tenant_global",
        scope_entity_type="",
        scope_entity_id="",
        snapshot_version=3,
        last_signal_id=signal_id,
        last_occurred_at=now,
        health_summary={"status": "healthy"},
        risk_summary={"critical": 0},
        execution_summary={"success_rate": 0.98},
        queue_summary={"pending": 2},
        audit_refs=[],
        snapshot_payload={"ok": True},
        created_at=now,
        updated_at=now,
    )

    class FakeService:
        async def list_signals(self, **kwargs):
            assert kwargs["tenant_id"] == "tenant-a"
            return [signal]

        async def get_signal(self, db, signal_id_param, tenant_id):
            assert signal_id_param == signal_id
            assert tenant_id == "tenant-a"
            return signal

        async def get_tenant_state(self, db, tenant_id):
            assert tenant_id == "tenant-a"
            return state

        async def get_entity_state(self, db, tenant_id, entity_type, entity_id):
            assert tenant_id == "tenant-a"
            assert entity_type == "skill_run"
            assert entity_id == "run-1"
            return state

    monkeypatch.setattr(route_module, "get_observer_core_service", lambda: FakeService())

    list_response = client.get("/api/observer/signals")
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    signal_response = client.get(f"/api/observer/signals/{signal_id}")
    assert signal_response.status_code == 200
    assert signal_response.json()["source_module"] == "skill_engine"

    state_response = client.get("/api/observer/state")
    assert state_response.status_code == 200
    assert state_response.json()["snapshot_version"] == 3

    entity_state_response = client.get("/api/observer/state/entities/skill_run/run-1")
    assert entity_state_response.status_code == 200

    summary_response = client.get("/api/observer/summary")
    assert summary_response.status_code == 200
    assert summary_response.json()["tenant_id"] == "tenant-a"


def test_observer_signal_not_found(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(observer_core_router)

    async def _db_override():
        yield None

    principal = build_principal("viewer")
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    route_module = __import__("app.modules.observer_core.router", fromlist=["router"])

    class FakeService:
        async def get_signal(self, db, signal_id, tenant_id):
            return None

    monkeypatch.setattr(route_module, "get_observer_core_service", lambda: FakeService())

    response = client.get(f"/api/observer/signals/{uuid4()}")
    assert response.status_code == 404


def test_observer_requires_tenant_context() -> None:
    app = FastAPI()
    app.include_router(observer_core_router)

    async def _db_override():
        yield None

    principal = build_principal("viewer", tenant_id=None)
    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: principal
    app.dependency_overrides[get_current_principal] = lambda: principal
    client = TestClient(app)

    response = client.get("/api/observer/signals")
    assert response.status_code == 403


def test_observer_router_is_read_only() -> None:
    app = FastAPI()
    app.include_router(observer_core_router)

    unsafe_methods = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set())
        if not path.startswith("/api/observer"):
            continue
        for method in methods:
            if method not in {"GET", "HEAD", "OPTIONS"}:
                unsafe_methods.add(method)

    assert unsafe_methods == set()
