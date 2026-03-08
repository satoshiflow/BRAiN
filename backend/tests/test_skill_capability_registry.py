from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.database import get_db
from app.modules.capabilities_registry.router import router as capabilities_registry_router
from app.modules.capabilities_registry.service import CapabilityCandidate, CapabilityRegistryService
from app.modules.skills_registry.router import router as skills_registry_router
from app.modules.skills_registry.service import ResolutionCandidate, SkillRegistryService


def build_principal(*, roles: list[str], scopes: list[str], tenant_id: str | None = "tenant-a") -> Principal:
    return Principal(
        principal_id="user-123",
        principal_type=PrincipalType.HUMAN,
        email="user@example.com",
        name="Test User",
        roles=roles,
        scopes=scopes,
        tenant_id=tenant_id,
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


@pytest.fixture
def registry_app() -> FastAPI:
    app = FastAPI()
    app.include_router(skills_registry_router)
    app.include_router(capabilities_registry_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    return app


@pytest.fixture
def client(registry_app: FastAPI) -> TestClient:
    return TestClient(registry_app)


def test_skill_registry_transition_rules() -> None:
    assert SkillRegistryService.is_transition_allowed("draft", "review") is True
    assert SkillRegistryService.is_transition_allowed("approved", "active") is True
    assert SkillRegistryService.is_transition_allowed("draft", "active") is False


def test_skill_registry_resolution_prefers_tenant_active() -> None:
    picked = SkillRegistryService.pick_resolution_candidate(
        [
            ResolutionCandidate(owner_scope="system", tenant_id=None, version=3, status="active"),
            ResolutionCandidate(owner_scope="tenant", tenant_id="tenant-a", version=2, status="active"),
        ]
    )
    assert picked is not None
    assert picked.owner_scope == "tenant"
    assert picked.version == 2


def test_capability_registry_transition_rules() -> None:
    assert CapabilityRegistryService.is_transition_allowed("draft", "active") is True
    assert CapabilityRegistryService.is_transition_allowed("blocked", "active") is True
    assert CapabilityRegistryService.is_transition_allowed("draft", "blocked") is False


def test_capability_registry_resolution_prefers_tenant_active() -> None:
    picked = CapabilityRegistryService.pick_resolution_candidate(
        [
            CapabilityCandidate(owner_scope="system", tenant_id=None, version=4, status="active"),
            CapabilityCandidate(owner_scope="tenant", tenant_id="tenant-a", version=1, status="active"),
        ]
    )
    assert picked is not None
    assert picked.owner_scope == "tenant"
    assert picked.version == 1


def test_registry_routes_require_authentication(client: TestClient) -> None:
    with override_auth_unauthorized(client):
        response = client.get("/api/skill-definitions")
    assert response.status_code == 401


def test_registry_creation_requires_admin_for_capabilities(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_principal(roles=["operator"], scopes=["capabilities:read", "skills:write"])

    with override_auth_principal(client, principal):
        response = client.post(
            "/api/capability-definitions",
            json={
                "capability_key": "text.generate",
                "domain": "generation",
                "description": "Generate text",
            },
        )

    assert response.status_code == 403
