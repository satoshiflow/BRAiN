from __future__ import annotations

import time

from app.core.capabilities.base import CapabilityAdapter
from app.core.capabilities.schemas import CapabilityAdapterHealth, CapabilityExecutionError, CapabilityExecutionRequest, CapabilityExecutionSuccess, ProviderBindingSpec
from app.modules.llm_router.schemas import ChatMessage, LLMProvider, LLMRequest, MessageRole
from app.modules.llm_router.service import LLMRouterService


class LLMTextGenerateAdapter(CapabilityAdapter):
    adapter_key = "llm_text_generate"
    supported_capability_keys = ("text.generate",)

    def __init__(self, router_service: LLMRouterService | None = None) -> None:
        self.router_service = router_service

    def _get_router_service(self) -> LLMRouterService | None:
        if self.router_service is not None:
            return self.router_service
        try:
            self.router_service = LLMRouterService()
        except Exception:
            self.router_service = None
        return self.router_service

    async def execute(
        self,
        request: CapabilityExecutionRequest,
        binding: ProviderBindingSpec,
    ) -> CapabilityExecutionSuccess | CapabilityExecutionError:
        prompt = str(request.input_payload.get("prompt", "")).strip()
        if not prompt:
            return CapabilityExecutionError(
                error_code="CAP-INPUT-001",
                sanitized_message="Missing required prompt input",
                retryable=False,
                adapter_version=self.adapter_version,
            )

        router_service = self._get_router_service()
        if router_service is None or not getattr(router_service, "initialized", False):
            return CapabilityExecutionError(
                error_code="CAP-LLM-INIT-001",
                sanitized_message="LLM router is not initialized",
                provider_unavailable=True,
                retryable=False,
                adapter_version=self.adapter_version,
            )

        provider_name = binding.config.get("provider") or binding.provider_key
        try:
            provider = LLMProvider(provider_name)
        except ValueError:
            return CapabilityExecutionError(
                error_code="CAP-LLM-PROVIDER-001",
                sanitized_message=f"Unsupported LLM provider '{provider_name}'",
                provider_unavailable=True,
                retryable=False,
                adapter_version=self.adapter_version,
            )

        messages = []
        system_prompt = binding.config.get("system_prompt")
        if system_prompt:
            messages.append(ChatMessage(role=MessageRole.SYSTEM, content=str(system_prompt)))
        messages.append(ChatMessage(role=MessageRole.USER, content=prompt))

        start = time.time()
        try:
            response = await router_service.chat(
                LLMRequest(
                    messages=messages,
                    provider=provider,
                    model=binding.config.get("model"),
                    temperature=float(request.input_payload.get("temperature", binding.config.get("temperature", 0.7))),
                    max_tokens=request.input_payload.get("max_tokens", binding.config.get("max_tokens")),
                    metadata={"capability_key": request.capability_key, "provider_binding_id": binding.provider_binding_id},
                ),
                agent_id=request.actor_id,
            )
        except Exception as exc:
            return CapabilityExecutionError(
                error_code="CAP-LLM-EXEC-001",
                sanitized_message="Text generation provider request failed",
                provider_unavailable=True,
                retryable=True,
                provider_error_ref=str(type(exc).__name__),
                trace_refs={"provider_key": binding.provider_key},
                adapter_version=self.adapter_version,
            )

        latency_ms = float(response.metadata.get("latency_ms", (time.time() - start) * 1000.0)) if response.metadata else (time.time() - start) * 1000.0
        usage = response.usage or {}
        return CapabilityExecutionSuccess(
            output={"text": response.content, "finish_reason": response.finish_reason},
            usage=usage,
            latency_ms=latency_ms,
            cost_actual=None,
            provider_facts={"provider": response.provider.value, "model": response.model},
            trace_refs={"provider_binding_id": binding.provider_binding_id},
            adapter_version=self.adapter_version,
        )

    async def health_check(self, binding: ProviderBindingSpec) -> CapabilityAdapterHealth:
        provider_name = binding.config.get("provider") or binding.provider_key
        try:
            provider = LLMProvider(provider_name)
            router_service = self._get_router_service()
            if router_service is None or not getattr(router_service, "initialized", False):
                raise RuntimeError("LLM router is not initialized")
            status = await router_service.check_provider_health(provider)
            return CapabilityAdapterHealth(
                provider_binding_id=binding.provider_binding_id,
                capability_key=binding.capability_key,
                healthy=bool(status.available),
                latency_ms=status.latency_ms,
                details={"provider": provider.value, "message": status.message},
            )
        except Exception as exc:
            return CapabilityAdapterHealth(
                provider_binding_id=binding.provider_binding_id,
                capability_key=binding.capability_key,
                healthy=False,
                details={"error": str(exc), "provider": provider_name},
            )
