from __future__ import annotations

from app.core.capabilities.base import CapabilityAdapter
from app.core.capabilities.schemas import CapabilityAdapterHealth, CapabilityExecutionError, CapabilityExecutionRequest, CapabilityExecutionSuccess, ProviderBindingSpec
from app.modules.connectors.service import ConnectorService, get_connector_service


class ConnectorHealthAdapter(CapabilityAdapter):
    adapter_key = "connector_health"
    supported_capability_keys = ("connectors.health.check",)

    def __init__(self, connector_service: ConnectorService | None = None) -> None:
        self.connector_service = connector_service or get_connector_service()

    async def execute(
        self,
        request: CapabilityExecutionRequest,
        binding: ProviderBindingSpec,
    ) -> CapabilityExecutionSuccess | CapabilityExecutionError:
        connector_id = str(request.input_payload.get("connector_id") or binding.config.get("connector_id") or "").strip()
        if not connector_id:
            return CapabilityExecutionError(
                error_code="CAP-CONNECTOR-INPUT-001",
                sanitized_message="Missing connector_id for connector health check",
                retryable=False,
                adapter_version=self.adapter_version,
            )

        health = await self.connector_service.health_check(connector_id)
        if health is None:
            return CapabilityExecutionError(
                error_code="CAP-CONNECTOR-NOT-FOUND",
                sanitized_message=f"Connector '{connector_id}' not found",
                retryable=False,
                adapter_version=self.adapter_version,
            )

        return CapabilityExecutionSuccess(
            output={
                "connector_id": health.connector_id,
                "status": health.status.value,
                "healthy": health.status.value == "connected",
                "error": health.error,
                "details": health.details,
            },
            usage={},
            latency_ms=float(health.latency_ms or 0.0),
            cost_actual=0.0,
            provider_facts={"provider": binding.provider_key, "connector_id": connector_id},
            trace_refs={"provider_binding_id": binding.provider_binding_id},
            adapter_version=self.adapter_version,
        )

    async def health_check(self, binding: ProviderBindingSpec) -> CapabilityAdapterHealth:
        connector_id = str(binding.config.get("connector_id") or "").strip()
        if not connector_id:
            return CapabilityAdapterHealth(
                provider_binding_id=binding.provider_binding_id,
                capability_key=binding.capability_key,
                healthy=False,
                details={"error": "Missing connector_id binding config"},
            )
        health = await self.connector_service.health_check(connector_id)
        if health is None:
            return CapabilityAdapterHealth(
                provider_binding_id=binding.provider_binding_id,
                capability_key=binding.capability_key,
                healthy=False,
                details={"error": f"Connector '{connector_id}' not found"},
            )
        return CapabilityAdapterHealth(
            provider_binding_id=binding.provider_binding_id,
            capability_key=binding.capability_key,
            healthy=health.status.value == "connected",
            latency_ms=health.latency_ms,
            details={"connector_id": connector_id, "status": health.status.value},
        )
