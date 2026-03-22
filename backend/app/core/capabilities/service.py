from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from loguru import logger

from app.core.capabilities.adapters.connector_health import ConnectorHealthAdapter
from app.core.capabilities.adapters.llm_text_generate import LLMTextGenerateAdapter
from app.core.capabilities.base import CapabilityAdapter
from app.core.capabilities.schemas import (
    CapabilityAdapterHealth,
    CapabilityExecutionError,
    CapabilityExecutionRequest,
    CapabilityExecutionResponse,
    ProviderBindingSpec,
)
from app.modules.capabilities_registry.service import CapabilityRegistryService, get_capability_registry_service
from app.modules.provider_bindings.models import ProviderBindingModel
from app.modules.provider_bindings.service import ProviderBindingService, get_provider_binding_service
from app.modules.skills_registry.schemas import VersionSelector


@dataclass(slots=True)
class BindingLookupResult:
    binding: ProviderBindingSpec
    adapter: CapabilityAdapter


class InMemoryProviderBindingRegistry:
    def __init__(self) -> None:
        self._bindings: dict[str, ProviderBindingSpec] = {
            "binding.text.generate.ollama.v1": ProviderBindingSpec(
                provider_binding_id="binding.text.generate.ollama.v1",
                owner_scope="system",
                capability_key="text.generate",
                capability_version=1,
                adapter_key="llm_text_generate",
                provider_key="ollama",
                config={"provider": "ollama"},
            ),
            "binding.connectors.health.default.v1": ProviderBindingSpec(
                provider_binding_id="binding.connectors.health.default.v1",
                owner_scope="system",
                capability_key="connectors.health.check",
                capability_version=1,
                adapter_key="connector_health",
                provider_key="connector_service",
                config={},
            ),
        }

    def get(self, provider_binding_id: str) -> ProviderBindingSpec | None:
        return self._bindings.get(provider_binding_id)

    def list_for_capability(self, capability_key: str, capability_version: int) -> list[ProviderBindingSpec]:
        return [
            binding
            for binding in self._bindings.values()
            if binding.capability_key == capability_key and binding.capability_version == capability_version and binding.enabled
        ]


class CapabilityExecutionService:
    def __init__(
        self,
        capability_registry: CapabilityRegistryService | None = None,
        binding_registry: InMemoryProviderBindingRegistry | None = None,
        provider_binding_service: ProviderBindingService | None = None,
    ) -> None:
        self.capability_registry = capability_registry or get_capability_registry_service()
        self.binding_registry = binding_registry or InMemoryProviderBindingRegistry()
        self.provider_binding_service = provider_binding_service or get_provider_binding_service()
        self._adapters: dict[str, CapabilityAdapter] = {}
        self.register_adapter(LLMTextGenerateAdapter())
        self.register_adapter(ConnectorHealthAdapter())

    def register_adapter(self, adapter: CapabilityAdapter) -> None:
        self._adapters[adapter.adapter_key] = adapter

    def _resolve_binding(self, tenant_id: str | None, provider_binding_id: str, capability_key: str, capability_version: int) -> BindingLookupResult:
        binding = self.binding_registry.get(provider_binding_id)
        if binding is None:
            raise ValueError(f"Unknown provider binding '{provider_binding_id}'")
        if binding.owner_scope == "tenant" and binding.tenant_id != tenant_id:
            raise ValueError("Provider binding is not accessible for the current tenant")
        if binding.capability_key != capability_key or binding.capability_version != capability_version:
            raise ValueError("Provider binding does not match resolved capability version")
        adapter = self._adapters.get(binding.adapter_key)
        if adapter is None:
            raise ValueError(f"No adapter registered for '{binding.adapter_key}'")
        if not adapter.supports(capability_key):
            raise ValueError(f"Adapter '{binding.adapter_key}' does not support '{capability_key}'")
        return BindingLookupResult(binding=binding, adapter=adapter)

    async def _resolve_binding_from_db(self, db, tenant_id: str | None, provider_binding_id: str, capability_key: str, capability_version: int) -> BindingLookupResult | None:
        binding_model = await db.get(ProviderBindingModel, provider_binding_id)
        if binding_model is None:
            return None
        if binding_model.owner_scope == "tenant" and binding_model.tenant_id != tenant_id:
            raise ValueError("Provider binding is not accessible for the current tenant")
        if binding_model.capability_key != capability_key or binding_model.capability_version != capability_version:
            raise ValueError("Provider binding does not match resolved capability version")
        if binding_model.status != "enabled":
            raise ValueError("Provider binding is not enabled")
        binding = self._binding_from_model(binding_model)
        adapter = self._adapters.get(binding.adapter_key)
        if adapter is None:
            raise ValueError(f"No adapter registered for '{binding.adapter_key}'")
        if not adapter.supports(capability_key):
            raise ValueError(f"Adapter '{binding.adapter_key}' does not support '{capability_key}'")
        return BindingLookupResult(binding=binding, adapter=adapter)

    @staticmethod
    def _binding_from_model(binding) -> ProviderBindingSpec:
        return ProviderBindingSpec(
            provider_binding_id=str(binding.id),
            tenant_id=binding.tenant_id,
            owner_scope=binding.owner_scope,
            capability_key=binding.capability_key,
            capability_version=binding.capability_version,
            adapter_key=binding.adapter_key,
            provider_key=binding.provider_key,
            provider_type=binding.provider_type,
            endpoint_ref=binding.endpoint_ref,
            model_or_tool_ref=binding.model_or_tool_ref,
            priority=binding.priority,
            config=binding.config,
            enabled=binding.status == "enabled",
        )

    async def resolve_binding_for_execution(
        self,
        db,
        *,
        tenant_id: str | None,
        capability_key: str,
        capability_version: int,
        policy_context: dict[str, object],
    ):
        resolved = await self.provider_binding_service.resolve_binding_for_execution(
            db,
            capability_key=capability_key,
            capability_version=capability_version,
            tenant_id=tenant_id,
            policy_context=policy_context,
        )
        if resolved is not None:
            binding = ProviderBindingSpec.model_validate(resolved.binding_snapshot)
            adapter = self._adapters.get(binding.adapter_key)
            if adapter is None:
                raise ValueError(f"No adapter registered for '{binding.adapter_key}'")
            return BindingLookupResult(binding=binding, adapter=adapter), resolved
        bindings = self.list_bindings(capability_key, capability_version)
        if not bindings:
            return None, None
        binding = bindings[0]
        adapter = self._adapters.get(binding.adapter_key)
        if adapter is None:
            raise ValueError(f"No adapter registered for '{binding.adapter_key}'")
        return BindingLookupResult(binding=binding, adapter=adapter), {
            "provider_binding_id": binding.provider_binding_id,
            "selection_strategy": "compatibility_fallback",
            "selection_reason": "compat_in_memory_fallback",
            "policy_context": policy_context,
            "binding_snapshot": binding.model_dump(mode="json"),
        }

    async def execute(self, db, request: CapabilityExecutionRequest) -> CapabilityExecutionResponse:
        definition = await self.capability_registry.resolve_definition(
            db,
            request.capability_key,
            request.tenant_id,
            selector=VersionSelector.EXACT,
            version_value=request.capability_version,
        )
        if definition.status not in {"active", "deprecated"}:
            raise ValueError(f"Capability '{request.capability_key}' is not execution-eligible")

        binding_result = await self._resolve_binding_from_db(
            db,
            request.tenant_id,
            request.provider_binding_id,
            definition.capability_key,
            definition.version,
        )
        if binding_result is None:
            binding_result = self._resolve_binding(request.tenant_id, request.provider_binding_id, definition.capability_key, definition.version)
        result = await binding_result.adapter.execute(request, binding_result.binding)
        logger.info(
            "Capability execution completed for {} via {} with status {}",
            request.capability_key,
            request.provider_binding_id,
            result.status.value,
        )
        return CapabilityExecutionResponse(
            capability_key=definition.capability_key,
            capability_version=definition.version,
            provider_binding_id=binding_result.binding.provider_binding_id,
            result=result,
        )

    async def health_check(self, provider_binding_id: str) -> CapabilityAdapterHealth:
        binding = self.binding_registry.get(provider_binding_id)
        if binding is None:
            raise ValueError(f"Unknown provider binding '{provider_binding_id}'")
        adapter = self._adapters.get(binding.adapter_key)
        if adapter is None:
            raise ValueError(f"No adapter registered for '{binding.adapter_key}'")
        return await adapter.health_check(binding)

    def list_bindings(self, capability_key: str, capability_version: int) -> list[ProviderBindingSpec]:
        return self.binding_registry.list_for_capability(capability_key, capability_version)


_capability_execution_service: CapabilityExecutionService | None = None


def get_capability_execution_service() -> CapabilityExecutionService:
    global _capability_execution_service
    if _capability_execution_service is None:
        _capability_execution_service = CapabilityExecutionService()
    return _capability_execution_service
