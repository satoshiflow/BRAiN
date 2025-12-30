"""
Pydantic schemas for LLM Router module
"""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    # Local providers
    OLLAMA = "ollama"

    # API providers
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"

    # Special
    AUTO = "auto"  # Auto-select based on context


class MessageRole(str, Enum):
    """Chat message roles"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class ChatMessage(BaseModel):
    """Single chat message"""

    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None


class LLMRequest(BaseModel):
    """Unified LLM request"""

    messages: List[ChatMessage] = Field(
        ...,
        description="Chat messages",
    )

    provider: LLMProvider = Field(
        LLMProvider.AUTO,
        description="LLM provider to use",
    )

    model: Optional[str] = Field(
        None,
        description="Model name (provider-specific)",
    )

    temperature: float = Field(
        0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )

    max_tokens: Optional[int] = Field(
        None,
        description="Maximum tokens to generate",
    )

    stream: bool = Field(
        False,
        description="Enable streaming responses",
    )

    tools: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Available tools/functions",
    )

    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional request metadata",
    )


class LLMResponse(BaseModel):
    """Unified LLM response"""

    content: str = Field(
        ...,
        description="Generated response",
    )

    provider: LLMProvider = Field(
        ...,
        description="Provider that generated response",
    )

    model: str = Field(
        ...,
        description="Model that generated response",
    )

    finish_reason: Optional[str] = Field(
        None,
        description="Reason for completion (stop, length, etc.)",
    )

    usage: Optional[Dict[str, int]] = Field(
        None,
        description="Token usage statistics",
    )

    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional response metadata",
    )


class ProviderConfig(BaseModel):
    """Base provider configuration"""

    enabled: bool = Field(
        True,
        description="Enable this provider",
    )

    priority: int = Field(
        100,
        description="Provider priority (higher = preferred)",
    )

    fallback_providers: List[LLMProvider] = Field(
        default_factory=list,
        description="Fallback providers if this one fails",
    )


class OllamaConfig(ProviderConfig):
    """Ollama (local) provider configuration"""

    host: str = Field(
        "http://localhost:11434",
        description="Ollama server host",
    )

    default_model: str = Field(
        "llama3.2:latest",
        description="Default Ollama model",
    )

    timeout: float = Field(
        120.0,
        description="Request timeout in seconds",
    )

    # AXE agent restrictions
    restrict_to_agents: List[str] = Field(
        default_factory=lambda: ["axe_agent"],
        description="Restrict to specific agents (e.g., AXE)",
    )


class OpenRouterConfig(ProviderConfig):
    """OpenRouter (API) provider configuration"""

    api_key: Optional[str] = Field(
        None,
        description="OpenRouter API key",
    )

    base_url: str = Field(
        "https://openrouter.ai/api/v1",
        description="OpenRouter API base URL",
    )

    default_model: str = Field(
        "anthropic/claude-3.5-sonnet",
        description="Default model",
    )

    site_url: Optional[str] = Field(
        None,
        description="Your site URL (for OpenRouter analytics)",
    )

    site_name: Optional[str] = Field(
        "BRAiN",
        description="Your site name",
    )

    # Budget controls
    max_cost_per_request: Optional[float] = Field(
        None,
        description="Maximum cost per request ($)",
    )


class OpenAIConfig(ProviderConfig):
    """OpenAI provider configuration"""

    api_key: Optional[str] = Field(
        None,
        description="OpenAI API key",
    )

    base_url: str = Field(
        "https://api.openai.com/v1",
        description="OpenAI API base URL",
    )

    default_model: str = Field(
        "gpt-4-turbo-preview",
        description="Default model",
    )

    organization: Optional[str] = Field(
        None,
        description="OpenAI organization ID",
    )


class AnthropicConfig(ProviderConfig):
    """Anthropic (Claude) provider configuration"""

    api_key: Optional[str] = Field(
        None,
        description="Anthropic API key",
    )

    base_url: str = Field(
        "https://api.anthropic.com/v1",
        description="Anthropic API base URL",
    )

    default_model: str = Field(
        "claude-3-5-sonnet-20241022",
        description="Default model",
    )

    version: str = Field(
        "2023-06-01",
        description="Anthropic API version",
    )


class LLMRouterConfig(BaseModel):
    """Complete LLM Router configuration"""

    default_provider: LLMProvider = Field(
        LLMProvider.OLLAMA,
        description="Default provider if none specified",
    )

    enable_fallback: bool = Field(
        True,
        description="Enable automatic fallback to other providers",
    )

    enable_caching: bool = Field(
        True,
        description="Enable response caching",
    )

    cache_ttl: int = Field(
        3600,
        description="Cache TTL in seconds",
    )

    # Provider configs
    ollama: OllamaConfig = Field(
        default_factory=OllamaConfig,
    )

    openrouter: OpenRouterConfig = Field(
        default_factory=OpenRouterConfig,
    )

    openai: OpenAIConfig = Field(
        default_factory=OpenAIConfig,
    )

    anthropic: AnthropicConfig = Field(
        default_factory=AnthropicConfig,
    )


class ProviderStatus(BaseModel):
    """Provider health status"""

    provider: LLMProvider
    available: bool
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    last_check: Optional[str] = None


class RouterInfo(BaseModel):
    """LLM Router system information"""

    name: str = "BRAiN LLM Router"
    version: str = "0.1.0"
    description: str = "Unified LLM access with provider abstraction"
    providers: List[LLMProvider]
    default_provider: LLMProvider
    fallback_enabled: bool


class OpenWebUICompatibility(BaseModel):
    """OpenWebUI compatibility information"""

    compatible: bool = True
    api_base: str = "/api/llm-router"
    supported_features: List[str] = [
        "chat",
        "streaming",
        "model_selection",
        "multi_provider",
    ]
