from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import cast

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.modules.axe_presence.router import router as axe_presence_router
from app.modules.axe_presence.service import AXEPresenceService


def build_principal(*roles: str) -> Principal:
    return Principal(
        principal_id="axe-user",
        principal_type=PrincipalType.HUMAN,
        email="axe@example.com",
        name="AXE User",
        roles=list(roles),
        scopes=["read"],
        tenant_id="tenant-a",
    )


@contextmanager
def override_auth_principal(client: TestClient, principal: Principal):
    app = cast(FastAPI, client.app)
    app.dependency_overrides[require_auth] = lambda: principal  # type: ignore[attr-defined]
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)  # type: ignore[attr-defined]


@contextmanager
def override_auth_unauthorized(client: TestClient):
    async def _unauthorized():
        raise HTTPException(status_code=401, detail="Authentication required")

    app = cast(FastAPI, client.app)
    app.dependency_overrides[require_auth] = _unauthorized  # type: ignore[attr-defined]
    try:
        yield
    finally:
        app.dependency_overrides.pop(require_auth, None)  # type: ignore[attr-defined]


def build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(axe_presence_router)
    return app


def test_axe_presence_requires_authentication() -> None:
    app = build_test_app()
    client = TestClient(app)

    with override_auth_unauthorized(client):
        response = client.get("/api/axe/presence")

    assert response.status_code == 401


def test_presence_shape_success(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    async def _ok_counts(self, tenant_id: str | None = None):
        _ = self
        _ = tenant_id
        return 3, 2, "ok"

    monkeypatch.setattr(AXEPresenceService, "_safe_runtime_counts", _ok_counts)

    with override_auth_principal(client, build_principal("operator")):
        response = client.get("/api/axe/presence")

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "status",
        "label",
        "signal",
        "capabilities",
        "last_seen",
        "action_hint",
    }
    assert body["status"] == "linked"
    assert body["signal"] == "ok"


def test_relays_shape_success(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    async def _ok_counts(self, tenant_id: str | None = None):
        _ = self
        _ = tenant_id
        return 2, 1, "ok"

    monkeypatch.setattr(AXEPresenceService, "_safe_runtime_counts", _ok_counts)

    with override_auth_principal(client, build_principal("operator")):
        response = client.get("/api/axe/relays")

    assert response.status_code == 200
    body = response.json()
    assert "relays" in body
    assert len(body["relays"]) >= 2
    first = body["relays"][0]
    assert set(first.keys()) == {
        "status",
        "label",
        "signal",
        "capabilities",
        "last_seen",
        "action_hint",
    }


def test_runtime_surface_fallback_path(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    async def _warn_counts(self, tenant_id: str | None = None):
        _ = self
        _ = tenant_id
        return 0, 0, "warn"

    monkeypatch.setattr(AXEPresenceService, "_safe_runtime_counts", _warn_counts)

    with override_auth_principal(client, build_principal("operator")):
        response = client.get("/api/axe/runtime/surface")

    assert response.status_code == 200
    body = response.json()
    assert body["signal"] == "warn"
    assert body["status"] == "degraded"
    assert body["active_agents"] == 0
    assert body["pending_missions"] == 0
    assert "uptime" in body


def test_presence_passes_tenant_to_service(monkeypatch) -> None:
    app = build_test_app()
    client = TestClient(app)

    calls: list[str | None] = []

    async def _fake_get_presence(self, tenant_id: str | None = None):
        _ = self
        calls.append(tenant_id)
        return {
            "status": "linked",
            "label": "BRAiN relay online",
            "signal": "ok",
            "capabilities": ["chat"],
            "last_seen": "2026-03-12T15:31:44Z",
            "action_hint": "safe_to_operate",
        }

    monkeypatch.setattr(AXEPresenceService, "get_presence", _fake_get_presence)

    with override_auth_principal(client, build_principal("operator")):
        response = client.get("/api/axe/presence")

    assert response.status_code == 200
    assert calls == ["tenant-a"]


def test_runtime_surface_warns_when_only_one_aggregate_fails(monkeypatch) -> None:
    service = AXEPresenceService(db=object())

    async def _fake_active_agents(tenant_id: str | None = None):
        _ = tenant_id
        return 4

    async def _fake_pending_missions(tenant_id: str | None = None):
        _ = tenant_id
        return None

    monkeypatch.setattr(service, "_safe_active_agents", _fake_active_agents)
    monkeypatch.setattr(service, "_safe_pending_missions", _fake_pending_missions)

    active_agents, pending_missions, source_signal = asyncio.run(
        service._safe_runtime_counts("tenant-a")
    )

    assert active_agents == 4
    assert pending_missions == 0
    assert source_signal == "warn"
