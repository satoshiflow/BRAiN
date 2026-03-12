from __future__ import annotations

import pytest

from app.modules.axe_fusion.provider_selector import LLMProvider, ProviderConfig
from app.modules.axe_fusion.service import AXEFusionService, AXEllmClient


class _FakeHttpClient:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code
        self.calls: list[tuple[str, dict[str, str], float]] = []

    async def get(self, url: str, headers: dict[str, str] | None = None, timeout: float = 5.0):
        self.calls.append((url, headers or {}, timeout))

        class _Response:
            def __init__(self, status_code: int):
                self.status_code = status_code

        return _Response(self.status_code)


class _FakeAXEClient:
    def __init__(self, http_client: _FakeHttpClient):
        self.client = http_client


@pytest.mark.asyncio
async def test_health_check_uses_ollama_tags_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AXEFusionService()
    http_client = _FakeHttpClient(status_code=200)
    config = ProviderConfig(
        provider=LLMProvider.OLLAMA,
        base_url="http://localhost:11434/v1",
        api_key="",
        model="llama3.2:3b",
    )

    monkeypatch.setattr(service.selector, "get_active_provider", lambda: LLMProvider.OLLAMA)
    monkeypatch.setattr(service.selector, "get_active_config", lambda: config)
    monkeypatch.setattr(service, "_get_or_create_client", lambda _config: _FakeAXEClient(http_client))

    result = await service.health_check()

    assert result["status"] == "healthy"
    assert http_client.calls[0][0] == "http://localhost:11434/api/tags"


@pytest.mark.asyncio
async def test_health_check_marks_mock_mode_as_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    service = AXEFusionService()
    monkeypatch.setattr(service.selector, "get_active_provider", lambda: LLMProvider.MOCK)
    monkeypatch.setattr(
        service.selector,
        "get_active_config",
        lambda: ProviderConfig(
            provider=LLMProvider.MOCK,
            base_url="http://localhost:8081",
            api_key="",
            model="mock-local",
        ),
    )
    monkeypatch.delenv("AXE_ALLOW_MOCK_FALLBACK", raising=False)

    result = await service.health_check()

    assert result["status"] == "degraded"
    assert result["axellm"] == "not_reachable"


def test_chat_completion_url_avoids_double_v1() -> None:
    client = AXEllmClient(base_url="http://localhost:11434/v1")
    assert client._chat_completion_url() == "http://localhost:11434/v1/chat/completions"

    plain = AXEllmClient(base_url="http://localhost:8081")
    assert plain._chat_completion_url() == "http://localhost:8081/v1/chat/completions"
