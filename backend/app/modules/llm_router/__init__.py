"""
LLM Router Module for BRAiN

Provides unified LLM access with provider abstraction:
- Local LLMs (Ollama) for AXE Agent
- API LLMs (OpenRouter, OpenAI, Anthropic) for Constitutional Agents
- OpenWebUI Integration
- Provider-specific routing and configuration

Architecture:
    ┌─────────────────────────────────────┐
    │       LLM Router Service            │
    ├─────────────────────────────────────┤
    │  Local Provider  │  API Provider    │
    │  (Ollama)       │  (OpenRouter)    │
    │  ↓              │  ↓               │
    │  AXE Agent      │  Const. Agents   │
    │                 │  Knowledge Graph │
    └─────────────────────────────────────┘

Version: 0.1.0
"""

from .service import LLMRouterService, get_llm_router
from .schemas import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ChatMessage,
    ProviderConfig,
    OpenRouterConfig,
    OllamaConfig,
)

__all__ = [
    "LLMRouterService",
    "get_llm_router",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "ChatMessage",
    "ProviderConfig",
    "OpenRouterConfig",
    "OllamaConfig",
]
