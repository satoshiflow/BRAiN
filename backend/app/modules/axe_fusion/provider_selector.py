"""Provider selection for AXE Fusion LLM backends."""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum


class LLMProvider(str, Enum):
    AUTO = "auto"
    OPENAI = "openai"
    GROQ = "groq"
    OLLAMA = "ollama"
    MOCK = "mock"


class SanitizationLevel(str, Enum):
    NONE = "none"
    MODERATE = "moderate"
    STRICT = "strict"


@dataclass(frozen=True)
class ProviderConfig:
    provider: LLMProvider
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 60.0

    def to_dict(self) -> dict:
        return {
            "provider": self.provider.value,
            "base_url": self.base_url,
            "api_key_configured": bool(self.api_key),
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
        }


class ProviderSelector:
    """Resolves active provider and config from environment variables."""

    def __init__(self) -> None:
        self._default_timeout = float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))

    def get_active_provider(self) -> LLMProvider:
        raw_mode = os.getenv("LOCAL_LLM_MODE", "auto").strip().lower()
        if raw_mode in {member.value for member in LLMProvider}:
            return LLMProvider(raw_mode)
        return LLMProvider.AUTO

    def _openai_config(self) -> ProviderConfig:
        return ProviderConfig(
            provider=LLMProvider.OPENAI,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            timeout_seconds=self._default_timeout,
        )

    def _groq_config(self) -> ProviderConfig:
        return ProviderConfig(
            provider=LLMProvider.GROQ,
            base_url=os.getenv("GROQ_API_URL", "https://api.groq.com/openai/v1"),
            api_key=os.getenv("GROQ_API_KEY", ""),
            model=os.getenv(
                "GROQ_MODEL",
                os.getenv("LLM_MODEL", "llama-3.2-90b-vision-preview"),
            ),
            timeout_seconds=self._default_timeout,
        )

    def _ollama_config(self) -> ProviderConfig:
        return ProviderConfig(
            provider=LLMProvider.OLLAMA,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("OLLAMA_API_KEY", ""),
            model=os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b"),
            timeout_seconds=self._default_timeout,
        )

    def _mock_config(self) -> ProviderConfig:
        return ProviderConfig(
            provider=LLMProvider.MOCK,
            base_url=os.getenv("MOCK_BASE_URL", "http://localhost:8081"),
            api_key=os.getenv("MOCK_API_KEY", ""),
            model=os.getenv("MOCK_MODEL", "mock-local"),
            timeout_seconds=self._default_timeout,
        )

    def get_auto_candidates(self) -> list[ProviderConfig]:
        """Provider candidates in preferred order for automatic mode."""
        return [
            self._ollama_config(),
            self._openai_config(),
            self._groq_config(),
        ]

    def get_active_config(self) -> ProviderConfig:
        provider = self.get_active_provider()
        if provider == LLMProvider.AUTO:
            # Runtime service resolves effective provider from these candidates.
            return self._ollama_config()

        if provider == LLMProvider.OPENAI:
            return self._openai_config()

        if provider == LLMProvider.GROQ:
            return self._groq_config()

        if provider == LLMProvider.OLLAMA:
            return self._ollama_config()

        return self._mock_config()

    def get_sanitization_level(self, provider: LLMProvider) -> SanitizationLevel:
        forced = os.getenv("FORCE_SANITIZATION_LEVEL", "").strip().lower()
        if forced in {member.value for member in SanitizationLevel}:
            return SanitizationLevel(forced)

        if provider == LLMProvider.GROQ:
            return SanitizationLevel.STRICT
        return SanitizationLevel.NONE

    def set_runtime_mode(self, provider: LLMProvider) -> None:
        os.environ["LOCAL_LLM_MODE"] = provider.value

    def set_force_sanitization_level(self, level: SanitizationLevel | None) -> None:
        if level is None:
            os.environ.pop("FORCE_SANITIZATION_LEVEL", None)
            return
        os.environ["FORCE_SANITIZATION_LEVEL"] = level.value
