from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.llm_router.schemas import ChatMessage, LLMProvider, LLMRequest, LLMRouterConfig, MessageRole
from app.modules.llm_router.service import LLMRouterService


def _service_stub() -> LLMRouterService:
    service = LLMRouterService.__new__(LLMRouterService)
    service.config = LLMRouterConfig(default_provider=LLMProvider.OPENAI)
    service.initialized = True
    return service


def test_select_provider_prefers_runtime_override() -> None:
    service = _service_stub()
    selected = service._select_provider(LLMProvider.OPENAI, agent_id="axe-agent", runtime_provider=LLMProvider.OLLAMA)
    assert selected == LLMProvider.OLLAMA


def test_resolve_runtime_provider_reads_runtime_control(monkeypatch: pytest.MonkeyPatch) -> None:
    service = _service_stub()

    class _FakeResolver:
        def resolve(self, context):  # noqa: ANN001
            _ = context
            return SimpleNamespace(
                decision_id="rdec_test_1",
                effective_config={"routing": {"llm": {"default_provider": "openrouter"}}},
            )

    import app.modules.llm_router.service as module

    monkeypatch.setattr(module, "get_runtime_control_service", lambda: _FakeResolver())

    request = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="hi")],
        metadata={"environment": "local", "risk_score": 0.2},
    )

    provider, decision_id = service._resolve_runtime_provider(request, agent_id="axe-agent")
    assert provider == LLMProvider.OPENROUTER
    assert decision_id == "rdec_test_1"


def test_resolve_runtime_provider_can_be_disabled_per_request() -> None:
    service = _service_stub()
    request = LLMRequest(
        messages=[ChatMessage(role=MessageRole.USER, content="hi")],
        metadata={"runtime_control_disable": True},
    )

    provider, decision_id = service._resolve_runtime_provider(request, agent_id=None)
    assert provider is None
    assert decision_id is None
