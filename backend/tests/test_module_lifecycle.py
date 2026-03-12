from __future__ import annotations

from types import SimpleNamespace
import asyncio

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.module_lifecycle.router import router as module_lifecycle_router
from app.modules.module_lifecycle.schemas import ModuleClassification, ModuleLifecycleStatus
from app.modules.module_lifecycle.service import ModuleLifecycleService


def build_principal(*roles: str) -> Principal:
    return Principal(
        principal_id="admin-1",
        principal_type=PrincipalType.HUMAN,
        email="admin@example.com",
        name="Admin",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


class FakeDb:
    def __init__(self) -> None:
        self.committed = False
        self.refreshed = False

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, item) -> None:
        self.refreshed = True


def test_module_lifecycle_service_requires_replacement_target_for_deprecation() -> None:
    service = ModuleLifecycleService()
    item = SimpleNamespace(
        module_id="webgenesis",
        lifecycle_status="stable",
        replacement_target=None,
        sunset_phase=None,
        notes=None,
        updated_at=None,
    )

    async def _get_module(db, module_id):
        return item

    service.get_module = _get_module  # type: ignore[method-assign]
    db = FakeDb()

    with pytest.raises(ValueError, match="replacement_target"):
        asyncio.run(
            service.set_status(
                db,
                "webgenesis",
                ModuleLifecycleStatus.DEPRECATED,
                None,
                "epic12",
                "sunset",
            )
        )


def test_module_lifecycle_service_blocks_invalid_transition() -> None:
    service = ModuleLifecycleService()
    item = SimpleNamespace(
        module_id="webgenesis",
        lifecycle_status="retired",
        replacement_target="builder.webgenesis.generate",
        sunset_phase="epic12",
        notes=None,
        updated_at=None,
    )

    async def _get_module(db, module_id):
        return item

    service.get_module = _get_module  # type: ignore[method-assign]
    db = FakeDb()

    with pytest.raises(ValueError, match="Invalid lifecycle transition"):
        asyncio.run(
            service.set_status(
                db,
                "webgenesis",
                ModuleLifecycleStatus.DEPRECATED,
                "builder.webgenesis.generate",
                "epic12",
                "cannot revive retired module",
            )
        )


def test_module_lifecycle_service_requires_kill_switch_for_retired() -> None:
    service = ModuleLifecycleService()
    item = SimpleNamespace(
        module_id="legacy_module",
        lifecycle_status="stable",
        replacement_target="new.module.path",
        sunset_phase="phase_p5",
        kill_switch=None,
        notes=None,
        updated_at=None,
    )

    async def _get_module(db, module_id):
        return item

    service.get_module = _get_module  # type: ignore[method-assign]
    db = FakeDb()

    with pytest.raises(ValueError, match="kill_switch"):
        asyncio.run(
            service.set_status(
                db,
                "legacy_module",
                ModuleLifecycleStatus.RETIRED,
                "new.module.path",
                "phase_p5",
                "retire module",
            )
        )


@pytest.mark.asyncio
async def test_module_lifecycle_service_updates_valid_transition() -> None:
    service = ModuleLifecycleService()
    item = SimpleNamespace(
        module_id="course_factory",
        lifecycle_status="stable",
        replacement_target=None,
        sunset_phase=None,
        notes=None,
        updated_at=None,
    )

    async def _get_module(db, module_id):
        return item

    service.get_module = _get_module  # type: ignore[method-assign]
    db = FakeDb()

    updated = await service.set_status(
        db,
        "course_factory",
        ModuleLifecycleStatus.DEPRECATED,
        "builder.course_factory.generate",
        "epic12",
        "replace with canonical builder skill",
    )

    assert updated is item
    assert item.lifecycle_status == "deprecated"
    assert item.replacement_target == "builder.course_factory.generate"
    assert db.committed is True
    assert db.refreshed is True


def test_module_lifecycle_routes_support_filters_and_matrix(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(module_lifecycle_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: build_principal("admin")
    client = TestClient(app)

    router_module = __import__("app.modules.module_lifecycle.router", fromlist=["router"])
    item = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        module_id="webgenesis",
        owner_scope="system",
        classification="CONSOLIDATE",
        lifecycle_status="deprecated",
        canonical_path="backend/app/modules/webgenesis",
        active_routes=["/api/webgenesis/{site_id}/deploy"],
        data_owner="skillrun",
        auth_surface="operator+dmz",
        event_contract_status="partial",
        audit_policy="audit_required",
        migration_adapter="app.modules.webgenesis",
        kill_switch="webgenesis.write.disabled",
        replacement_target="builder.webgenesis.deploy",
        sunset_phase="epic12",
        notes="sunset in progress",
        created_at="2026-03-08T00:00:00Z",
        updated_at="2026-03-08T00:00:00Z",
    )

    class FakeService:
        async def list_modules(self, db, **filters):
            assert filters["classification"] == ModuleClassification.CONSOLIDATE
            assert filters["lifecycle_status"] == ModuleLifecycleStatus.DEPRECATED
            return [item]

        async def get_module(self, db, module_id):
            assert module_id == "webgenesis"
            return item

    monkeypatch.setattr(router_module, "get_module_lifecycle_service", lambda: FakeService())

    list_response = client.get("/api/module-lifecycle", params={"classification": "CONSOLIDATE", "lifecycle_status": "deprecated"})
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    matrix_response = client.get("/api/module-lifecycle/webgenesis/decommission-matrix")
    assert matrix_response.status_code == 200
    assert matrix_response.json()["replacement_target"] == "builder.webgenesis.deploy"


def test_module_lifecycle_decommission_ledger(monkeypatch) -> None:
    app = FastAPI()
    app.include_router(module_lifecycle_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    app.dependency_overrides[require_auth] = lambda: build_principal("admin")
    client = TestClient(app)

    router_module = __import__("app.modules.module_lifecycle.router", fromlist=["router"])

    class FakeService:
        async def list_decommission_ledger(self, db):
            return [
                {
                    "module_id": "webgenesis",
                    "lifecycle_status": ModuleLifecycleStatus.DEPRECATED,
                    "replacement_target": "builder.webgenesis.deploy",
                    "kill_switch": None,
                    "sunset_phase": "phase_p5",
                    "migration_adapter": "app.modules.webgenesis",
                    "decommission_ready": True,
                    "blockers": [],
                }
            ]

    monkeypatch.setattr(router_module, "get_module_lifecycle_service", lambda: FakeService())

    response = client.get("/api/module-lifecycle/decommission/ledger")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["module_id"] == "webgenesis"


@pytest.mark.asyncio
async def test_course_factory_write_guard_blocks_retired_module(monkeypatch) -> None:
    route_module = __import__("app.modules.course_factory.router", fromlist=["router"])
    monkeypatch.setenv("BRAIN_TEST_COMPAT_MODE", "false")

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert module_id == "course_factory"
            return SimpleNamespace(lifecycle_status="retired")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    with pytest.raises(Exception, match="course_factory is retired"):
        await route_module._ensure_course_factory_writable(None)


@pytest.mark.asyncio
async def test_webgenesis_write_guard_blocks_deprecated_module(monkeypatch) -> None:
    route_module = __import__("app.modules.webgenesis.router", fromlist=["router"])
    monkeypatch.setenv("BRAIN_TEST_COMPAT_MODE", "false")

    class FakeLifecycleService:
        async def get_module(self, db, module_id):
            assert module_id == "webgenesis"
            return SimpleNamespace(lifecycle_status="deprecated")

    monkeypatch.setattr(route_module, "get_module_lifecycle_service", lambda: FakeLifecycleService())

    with pytest.raises(Exception, match="webgenesis is deprecated"):
        await route_module._ensure_webgenesis_writable(None)
