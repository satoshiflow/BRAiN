from __future__ import annotations

from abc import ABC, abstractmethod

from .schemas import CapabilityAdapterHealth, CapabilityExecutionError, CapabilityExecutionRequest, CapabilityExecutionSuccess, ProviderBindingSpec


class CapabilityAdapter(ABC):
    adapter_key: str
    supported_capability_keys: tuple[str, ...]
    adapter_version: str = "v1"

    def supports(self, capability_key: str) -> bool:
        return capability_key in self.supported_capability_keys

    @abstractmethod
    async def execute(
        self,
        request: CapabilityExecutionRequest,
        binding: ProviderBindingSpec,
    ) -> CapabilityExecutionSuccess | CapabilityExecutionError:
        raise NotImplementedError

    @abstractmethod
    async def health_check(self, binding: ProviderBindingSpec) -> CapabilityAdapterHealth:
        raise NotImplementedError
