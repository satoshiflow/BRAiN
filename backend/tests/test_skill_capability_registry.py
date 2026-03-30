from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
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


def test_skill_value_score_endpoint_uses_registry_service(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_principal(roles=["admin"], scopes=["read", "write"], tenant_id="tenant-a")
    route_module = __import__("app.modules.skills_registry.router", fromlist=["router"])

    class FakeService:
        async def resolve_definition(self, db, skill_key, tenant_id, selector, version_value):
            _ = (db, selector, version_value)
            assert skill_key == "demo.skill"
            assert tenant_id == "tenant-a"
            return type(
                "SkillDef",
                (),
                {
                    "skill_key": "demo.skill",
                    "version": 3,
                    "risk_tier": "medium",
                    "value_score": 0.7,
                    "effort_saved_hours": 12.0,
                    "complexity_level": "high",
                    "quality_impact": 0.6,
                },
            )()

        def compute_value_profile(self, definition):
            _ = definition
            return {
                "value_score": 0.7,
                "source": "explicit",
                "breakdown": {"computed_score": 0.64},
            }

    monkeypatch.setattr(route_module, "get_skill_registry_service", lambda: FakeService())
    client.app.dependency_overrides[get_current_principal] = lambda: principal

    with override_auth_principal(client, principal):
        response = client.get("/api/skill-definitions/demo.skill/value-score")

    client.app.dependency_overrides.pop(get_current_principal, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["skill_key"] == "demo.skill"
    assert payload["value_score"] == 0.7
    assert payload["source"] == "explicit"


def test_skill_value_history_endpoint_returns_items(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    principal = build_principal(roles=["admin"], scopes=["read", "write"], tenant_id="tenant-a")
    route_module = __import__("app.modules.skills_registry.router", fromlist=["router"])

    class FakeService:
        async def get_value_history(self, db, *, skill_key, tenant_id, limit):
            _ = db
            assert skill_key == "demo.skill"
            assert tenant_id == "tenant-a"
            assert limit == 20
            return [
                {
                    "run_id": "run-1",
                    "skill_version": 3,
                    "state": "succeeded",
                    "created_at": "2026-03-30T12:00:00Z",
                    "overall_score": 1.0,
                    "value_score": 0.74,
                    "quality_impact": 0.7,
                    "effort_saved_hours": 14.2,
                    "source": "skill_run_feedback",
                }
            ]

    monkeypatch.setattr(route_module, "get_skill_registry_service", lambda: FakeService())
    client.app.dependency_overrides[get_current_principal] = lambda: principal

    with override_auth_principal(client, principal):
        response = client.get("/api/skill-definitions/demo.skill/value-history?limit=20")

    client.app.dependency_overrides.pop(get_current_principal, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload["skill_key"] == "demo.skill"
    assert payload["total"] == 1
    assert payload["items"][0]["value_score"] == 0.74
