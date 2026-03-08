from __future__ import annotations

from contextlib import contextmanager

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.auth_deps import Principal, PrincipalType, require_auth
from app.core.capabilities.adapters.connector_health import ConnectorHealthAdapter
from app.core.capabilities.adapters.llm_text_generate import LLMTextGenerateAdapter
from app.core.capabilities.schemas import CapabilityExecutionRequest, ProviderBindingSpec
from app.core.capabilities.service import CapabilityExecutionService, InMemoryProviderBindingRegistry
from app.core.database import get_db
from app.modules.capability_runtime.router import router as capability_runtime_router
from app.modules.connectors.schemas import ConnectorHealth, ConnectorStatus


class FakeLLMResponse:
    def __init__(self) -> None:
        self.content = "hello world"
        self.provider = type("Provider", (), {"value": "ollama"})()
        self.model = "ollama/test-model"
        self.finish_reason = "stop"
        self.usage = {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7}
        self.metadata = {"latency_ms": 12.5}


class FakeLLMRouterService:
    initialized = True

    async def chat(self, request, agent_id=None):
        return FakeLLMResponse()

    async def check_provider_health(self, provider):
        return type("Health", (), {"available": True, "latency_ms": 9.0, "message": "ok"})()


class FakeConnectorService:
    async def health_check(self, connector_id: str):
        if connector_id == "missing":
            return None
        return ConnectorHealth(
            connector_id=connector_id,
            status=ConnectorStatus.CONNECTED,
            latency_ms=4.0,
            details={"source": "fake"},
        )


class FakeCapabilityRegistryService:
    async def resolve_definition(self, db, capability_key, tenant_id, selector, version_value):
        return type(
            "CapabilityDefinition",
            (),
            {
                "capability_key": capability_key,
                "version": version_value,
                "status": "active",
            },
        )()


def build_principal() -> Principal:
    return Principal(
        principal_id="operator-123",
        principal_type=PrincipalType.HUMAN,
        email="operator@example.com",
        name="Operator",
        roles=["operator"],
        scopes=["write"],
        tenant_id="tenant-a",
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


@pytest.mark.asyncio
async def test_llm_adapter_normalizes_success() -> None:
    adapter = LLMTextGenerateAdapter(router_service=FakeLLMRouterService())
    request = CapabilityExecutionRequest(
        tenant_id="tenant-a",
        capability_key="text.generate",
        capability_version=1,
        provider_binding_id="binding.text.generate.ollama.v1",
        input_payload={"prompt": "Say hi"},
        correlation_id="corr-1",
    )
    binding = ProviderBindingSpec(
        provider_binding_id="binding.text.generate.ollama.v1",
        capability_key="text.generate",
        capability_version=1,
        adapter_key="llm_text_generate",
        provider_key="ollama",
        config={"provider": "ollama", "model": "test-model"},
    )

    result = await adapter.execute(request, binding)
    assert result.status.value == "succeeded"
    assert result.output["text"] == "hello world"
    assert result.provider_facts["provider"] == "ollama"


@pytest.mark.asyncio
async def test_connector_adapter_returns_normalized_error_for_missing_connector() -> None:
    adapter = ConnectorHealthAdapter(connector_service=FakeConnectorService())
    request = CapabilityExecutionRequest(
        tenant_id="tenant-a",
        capability_key="connectors.health.check",
        capability_version=1,
        provider_binding_id="binding.connectors.health.default.v1",
        input_payload={"connector_id": "missing"},
        correlation_id="corr-2",
    )
    binding = ProviderBindingSpec(
        provider_binding_id="binding.connectors.health.default.v1",
        capability_key="connectors.health.check",
        capability_version=1,
        adapter_key="connector_health",
        provider_key="connector_service",
        config={},
    )

    result = await adapter.execute(request, binding)
    assert result.status.value == "failed"
    assert result.error_code == "CAP-CONNECTOR-NOT-FOUND"


@pytest.mark.asyncio
async def test_capability_execution_service_rejects_binding_mismatch() -> None:
    service = CapabilityExecutionService(capability_registry=FakeCapabilityRegistryService(), binding_registry=InMemoryProviderBindingRegistry())
    request = CapabilityExecutionRequest(
        tenant_id="tenant-a",
        capability_key="text.generate",
        capability_version=1,
        provider_binding_id="binding.connectors.health.default.v1",
        input_payload={"prompt": "hello"},
        correlation_id="corr-3",
    )

    with pytest.raises(ValueError, match="does not match resolved capability version"):
        await service.execute(db=None, request=request)


@pytest.fixture
def capability_runtime_app() -> FastAPI:
    app = FastAPI()
    app.include_router(capability_runtime_router)

    async def _db_override():
        yield None

    app.dependency_overrides[get_db] = _db_override
    return app


@pytest.fixture
def capability_runtime_client(capability_runtime_app: FastAPI) -> TestClient:
    return TestClient(capability_runtime_app)


def test_capability_runtime_routes_require_authentication(capability_runtime_client: TestClient) -> None:
    with override_auth_unauthorized(capability_runtime_client):
        response = capability_runtime_client.get("/api/capabilities/bindings", params={"capability_key": "text.generate", "capability_version": 1})
    assert response.status_code == 401
