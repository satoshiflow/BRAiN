from __future__ import annotations

import pytest

from app.modules.axe_fusion.provider_selector import (
    LLMProvider,
    ProviderSelector,
    SanitizationLevel,
)


def test_provider_selector_uses_auto_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOCAL_LLM_MODE", raising=False)
    selector = ProviderSelector()

    provider = selector.get_active_provider()
    config = selector.get_active_config()

    assert provider == LLMProvider.AUTO
    assert config.provider == LLMProvider.OLLAMA


def test_provider_selector_reads_groq_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_MODE", "groq")
    monkeypatch.setenv("GROQ_API_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b")

    selector = ProviderSelector()
    config = selector.get_active_config()

    assert config.provider == LLMProvider.GROQ
    assert config.base_url == "https://api.groq.com/openai/v1"
    assert config.api_key == "test-groq-key"
    assert config.model == "llama-3.3-70b"


def test_provider_selector_reads_openai_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_MODE", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

    selector = ProviderSelector()
    config = selector.get_active_config()

    assert config.provider == LLMProvider.OPENAI
    assert config.base_url == "https://api.openai.com/v1"
    assert config.api_key == "test-openai-key"
    assert config.model == "gpt-4o-mini"


def test_sanitization_defaults_and_force_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FORCE_SANITIZATION_LEVEL", raising=False)
    selector = ProviderSelector()

    assert selector.get_sanitization_level(LLMProvider.GROQ) == SanitizationLevel.STRICT
    assert selector.get_sanitization_level(LLMProvider.OLLAMA) == SanitizationLevel.NONE

    monkeypatch.setenv("FORCE_SANITIZATION_LEVEL", "moderate")
    assert selector.get_sanitization_level(LLMProvider.OLLAMA) == SanitizationLevel.MODERATE


def test_auto_candidates_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCAL_LLM_MODE", "auto")
    selector = ProviderSelector()

    providers = [item.provider for item in selector.get_auto_candidates()]

    assert providers == [LLMProvider.OLLAMA, LLMProvider.OPENAI, LLMProvider.GROQ]
