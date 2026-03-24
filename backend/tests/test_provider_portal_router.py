from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.auth_deps import Principal, PrincipalType, get_current_principal, require_auth
from app.core.database import get_db
from app.modules.provider_portal.credential_service import ProviderCredentialService
from app.modules.provider_portal.router import router as provider_portal_router
from app.modules.provider_portal import router as provider_portal_router_module
from app.modules.provider_portal.schemas import ProviderCredentialSetRequest, ProviderTestRequest


def _principal(*roles: str) -> Principal:
    return Principal(
        principal_id="provider-portal-user",
        principal_type=PrincipalType.HUMAN,
        email="provider-portal@example.com",
        name="Provider Portal User",
        roles=list(roles),
        scopes=["read", "write"],
        tenant_id="tenant-a",
    )


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


class _FakeProviderPortalService:
    def __init__(self) -> None:
        self.provider_id = uuid4()
        self.last_secret_payload: dict | None = None
        self.test_result_none = False

    async def list_providers(self, db, tenant_id):  # noqa: ANN001
        _ = db
        _ = tenant_id
        return []

    async def _active_credential(self, db, provider_id):  # noqa: ANN001
        _ = db
        _ = provider_id
        return None

    async def create_provider(self, db, payload, principal):  # noqa: ANN001
        _ = db
        _ = payload
        _ = principal
        return SimpleNamespace(
            id=self.provider_id,
            tenant_id="tenant-a",
            owner_scope="tenant",
            slug="openai",
            display_name="OpenAI",
            provider_type="cloud",
            base_url="https://api.openai.com/v1",
            auth_mode="api_key",
            is_enabled=True,
            is_local=False,
            supports_chat=True,
            supports_embeddings=False,
            supports_responses=True,
            notes=None,
            health_status="unknown",
            last_health_at=None,
            last_health_error=None,
            secret_configured=False,
            key_hint_masked=None,
            created_by="provider-portal-user",
            updated_by="provider-portal-user",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    async def set_credential(self, db, provider_id, payload, principal):  # noqa: ANN001
        _ = db
        _ = provider_id
        _ = principal
        self.last_secret_payload = payload.model_dump()
        return SimpleNamespace(
            provider_id=self.provider_id,
            is_active=True,
            key_hint_last4="****1234",
            updated_at=datetime.now(timezone.utc),
        )

    async def test_provider(self, db, provider_id, payload, principal):  # noqa: ANN001
        _ = db
        _ = provider_id
        _ = payload
        _ = principal
        if self.test_result_none:
            return None
        return {
            "provider_id": self.provider_id,
            "status": "healthy",
            "success": True,
            "latency_ms": 37,
            "error_code": None,
            "error_message": None,
            "checked_at": datetime.now(timezone.utc),
            "binding_projection": {
                "provider_key": "openai",
                "capability_key": "text.generate",
                "config": {"provider": "openai"},
            },
        }


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(provider_portal_router)

    async def _fake_get_db():  # noqa: ANN202
        yield object()

    app.dependency_overrides[get_db] = _fake_get_db
    return app


def test_provider_portal_requires_authentication(monkeypatch) -> None:
    fake_service = _FakeProviderPortalService()
    monkeypatch.setattr(provider_portal_router_module, "get_provider_portal_service", lambda: fake_service)
    client = TestClient(_build_test_app())

    with _override_unauthorized(client):
        response = client.get("/api/llm/providers")

    assert response.status_code == 401


def test_provider_create_requires_admin_role(monkeypatch) -> None:
    fake_service = _FakeProviderPortalService()
    monkeypatch.setattr(provider_portal_router_module, "get_provider_portal_service", lambda: fake_service)
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("viewer")):
        response = client.post(
            "/api/llm/providers",
            json={
                "owner_scope": "tenant",
                "slug": "openai",
                "display_name": "OpenAI",
                "provider_type": "cloud",
                "base_url": "https://api.openai.com/v1",
                "auth_mode": "api_key",
            },
        )

    assert response.status_code == 403


def test_set_secret_masks_output_and_never_echoes_plaintext(monkeypatch) -> None:
    fake_service = _FakeProviderPortalService()
    monkeypatch.setattr(provider_portal_router_module, "get_provider_portal_service", lambda: fake_service)
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("admin")):
        raw_key = "sk-live-provider-portal-test-1234"
        response = client.post(
            f"/api/llm/providers/{fake_service.provider_id}/secret",
            json={"api_key": raw_key, "activate": True},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["key_hint_masked"] == "****1234"
    assert "api_key" not in body
    assert raw_key not in response.text
    assert fake_service.last_secret_payload == {"api_key": "sk-live-provider-portal-test-1234", "activate": True}


def test_provider_test_endpoint_returns_health_projection(monkeypatch) -> None:
    fake_service = _FakeProviderPortalService()
    monkeypatch.setattr(provider_portal_router_module, "get_provider_portal_service", lambda: fake_service)
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("operator")):
        response = client.post(
            f"/api/llm/providers/{fake_service.provider_id}/test",
            json={"model_name": "gpt-4o-mini", "timeout_seconds": 5.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["success"] is True
    assert body["binding_projection"]["provider_key"] == "openai"


def test_provider_test_endpoint_returns_not_found_when_provider_missing(monkeypatch) -> None:
    fake_service = _FakeProviderPortalService()
    fake_service.test_result_none = True
    monkeypatch.setattr(provider_portal_router_module, "get_provider_portal_service", lambda: fake_service)
    client = TestClient(_build_test_app())

    with _override_principal(client, _principal("operator")):
        response = client.post(
            f"/api/llm/providers/{fake_service.provider_id}/test",
            json={"timeout_seconds": 5.0},
        )

    assert response.status_code == 404


def test_provider_credential_schema_validation_rejects_short_key() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProviderCredentialSetRequest(api_key="short", activate=True)
    assert "at least 10 characters" in str(exc_info.value)


def test_provider_test_schema_validation_enforces_timeout_bounds() -> None:
    with pytest.raises(ValidationError) as exc_info:
        ProviderTestRequest(timeout_seconds=0.1)
    assert "greater than or equal to 1" in str(exc_info.value)


def test_credential_service_masks_and_encrypts_secret() -> None:
    service = ProviderCredentialService()
    raw_secret = "sk-provider-portal-example-9876"
    ciphertext = service.encrypt(raw_secret)
    assert raw_secret not in ciphertext
    assert service.masked_hint(raw_secret) == "****9876"
