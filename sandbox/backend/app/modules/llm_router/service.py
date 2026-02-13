"""
LLM Router Service - Unified LLM access with provider abstraction

Uses litellm for provider abstraction and routing.
"""

import time
from typing import Optional, Dict, Any, List
from loguru import logger
import os

try:
    import litellm
    from litellm import completion, acompletion
    LITELLM_AVAILABLE = True
except ImportError:
    logger.warning("litellm not available - install with: pip install litellm")
    LITELLM_AVAILABLE = False

from .schemas import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    LLMRouterConfig,
    ProviderStatus,
    ChatMessage,
    MessageRole,
    OllamaConfig,
    OpenRouterConfig,
)


class LLMRouterService:
    """
    Unified LLM Router Service

    Routes requests to appropriate LLM providers:
    - Ollama (local) for AXE Agent
    - OpenRouter for Constitutional Agents
    - OpenAI, Anthropic for specific use cases
    """

    def __init__(self, config: Optional[LLMRouterConfig] = None):
        """Initialize LLM Router"""

        if not LITELLM_AVAILABLE:
            logger.error("litellm not installed - LLM Router disabled")
            self.initialized = False
            return

        # Load configuration
        self.config = config or self._load_default_config()

        # Configure litellm
        self._configure_litellm()

        self.initialized = True
        logger.success("LLM Router initialized successfully")

    def _load_default_config(self) -> LLMRouterConfig:
        """Load default configuration from environment"""

        ollama_config = OllamaConfig(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            default_model=os.getenv("OLLAMA_MODEL", "llama3.2:latest"),
        )

        openrouter_config = OpenRouterConfig(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            default_model=os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet"),
            site_url=os.getenv("OPENROUTER_SITE_URL"),
            site_name=os.getenv("OPENROUTER_SITE_NAME", "BRAiN"),
        )

        return LLMRouterConfig(
            default_provider=LLMProvider.OLLAMA,
            ollama=ollama_config,
            openrouter=openrouter_config,
        )

    def _configure_litellm(self):
        """Configure litellm settings"""

        # Set API keys
        if self.config.openrouter.api_key:
            os.environ["OPENROUTER_API_KEY"] = self.config.openrouter.api_key

        if self.config.openai.api_key:
            os.environ["OPENAI_API_KEY"] = self.config.openai.api_key

        if self.config.anthropic.api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.config.anthropic.api_key

        # Configure litellm
        litellm.drop_params = True  # Drop unsupported params
        litellm.set_verbose = False  # Disable verbose logging

        logger.info("litellm configured with providers:")
        if self.config.ollama.enabled:
            logger.info(f"  - Ollama: {self.config.ollama.host}")
        if self.config.openrouter.enabled and self.config.openrouter.api_key:
            logger.info("  - OpenRouter: enabled")
        if self.config.openai.enabled and self.config.openai.api_key:
            logger.info("  - OpenAI: enabled")
        if self.config.anthropic.enabled and self.config.anthropic.api_key:
            logger.info("  - Anthropic: enabled")

    def _get_model_string(
        self,
        provider: LLMProvider,
        model: Optional[str] = None,
    ) -> str:
        """
        Get litellm-compatible model string

        Examples:
            ollama/llama3.2:latest
            openrouter/anthropic/claude-3.5-sonnet
            openai/gpt-4-turbo-preview
            anthropic/claude-3-5-sonnet-20241022
        """

        if provider == LLMProvider.OLLAMA:
            model = model or self.config.ollama.default_model
            return f"ollama/{model}"

        elif provider == LLMProvider.OPENROUTER:
            model = model or self.config.openrouter.default_model
            return f"openrouter/{model}"

        elif provider == LLMProvider.OPENAI:
            model = model or self.config.openai.default_model
            return f"openai/{model}"

        elif provider == LLMProvider.ANTHROPIC:
            model = model or self.config.anthropic.default_model
            return f"anthropic/{model}"

        else:
            # Default to Ollama
            return f"ollama/{self.config.ollama.default_model}"

    def _get_provider_params(self, provider: LLMProvider) -> Dict[str, Any]:
        """Get provider-specific parameters"""

        params = {}

        if provider == LLMProvider.OLLAMA:
            params["api_base"] = self.config.ollama.host

        elif provider == LLMProvider.OPENROUTER:
            params["api_base"] = self.config.openrouter.base_url
            if self.config.openrouter.site_url:
                params["extra_headers"] = {
                    "HTTP-Referer": self.config.openrouter.site_url,
                    "X-Title": self.config.openrouter.site_name,
                }

        elif provider == LLMProvider.OPENAI:
            params["api_base"] = self.config.openai.base_url
            if self.config.openai.organization:
                params["organization"] = self.config.openai.organization

        elif provider == LLMProvider.ANTHROPIC:
            params["api_base"] = self.config.anthropic.base_url

        return params

    async def chat(
        self,
        request: LLMRequest,
        agent_id: Optional[str] = None,
    ) -> LLMResponse:
        """
        Send chat request to appropriate LLM provider

        Args:
            request: LLM request
            agent_id: Optional agent ID for routing logic

        Returns:
            LLM response
        """

        if not self.initialized:
            raise RuntimeError("LLM Router not initialized")

        # Determine provider
        provider = self._select_provider(request.provider, agent_id)

        # Get model string
        model_string = self._get_model_string(provider, request.model)

        # Get provider params
        provider_params = self._get_provider_params(provider)

        # Convert messages
        messages = [
            {"role": msg.role.value, "content": msg.content}
            for msg in request.messages
        ]

        try:
            start_time = time.time()

            # Call litellm
            response = await acompletion(
                model=model_string,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream,
                **provider_params,
            )

            latency = (time.time() - start_time) * 1000

            # Parse response
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            # Get usage stats
            usage = None
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            logger.info(
                f"LLM request completed: {provider.value} ({model_string}) "
                f"in {latency:.2f}ms"
            )

            return LLMResponse(
                content=content,
                provider=provider,
                model=model_string,
                finish_reason=finish_reason,
                usage=usage,
                metadata={
                    "latency_ms": latency,
                    "agent_id": agent_id,
                },
            )

        except Exception as e:
            logger.error(f"LLM request failed ({provider.value}): {e}")

            # Try fallback if enabled
            if self.config.enable_fallback and provider != LLMProvider.OLLAMA:
                logger.warning(f"Falling back to Ollama...")
                request.provider = LLMProvider.OLLAMA
                return await self.chat(request, agent_id)

            raise

    def _select_provider(
        self,
        requested_provider: LLMProvider,
        agent_id: Optional[str] = None,
    ) -> LLMProvider:
        """
        Select LLM provider based on request and agent context

        Rules:
        1. AXE Agent always uses Ollama (local)
        2. If provider explicitly requested, use it
        3. Otherwise use default provider
        """

        # Rule 1: AXE Agent restriction
        if agent_id and "axe" in agent_id.lower():
            logger.debug(f"AXE Agent detected - forcing Ollama provider")
            return LLMProvider.OLLAMA

        # Rule 2: Explicit provider request
        if requested_provider != LLMProvider.AUTO:
            return requested_provider

        # Rule 3: Default provider
        return self.config.default_provider

    async def check_provider_health(
        self,
        provider: LLMProvider,
    ) -> ProviderStatus:
        """
        Check provider health status

        Args:
            provider: Provider to check

        Returns:
            Provider status
        """

        try:
            start_time = time.time()

            # Simple test request
            test_request = LLMRequest(
                messages=[
                    ChatMessage(role=MessageRole.USER, content="ping")
                ],
                provider=provider,
                max_tokens=5,
            )

            response = await self.chat(test_request)

            latency = (time.time() - start_time) * 1000

            return ProviderStatus(
                provider=provider,
                available=True,
                latency_ms=latency,
                last_check=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

        except Exception as e:
            logger.error(f"Provider health check failed ({provider.value}): {e}")

            return ProviderStatus(
                provider=provider,
                available=False,
                error=str(e),
                last_check=time.strftime("%Y-%m-%d %H:%M:%S"),
            )

    async def list_available_models(
        self,
        provider: LLMProvider,
    ) -> List[str]:
        """
        List available models for provider

        Args:
            provider: Provider to query

        Returns:
            List of model names
        """

        if provider == LLMProvider.OLLAMA:
            # Query Ollama API for models
            try:
                import httpx

                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.config.ollama.host}/api/tags"
                    )
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]

            except Exception as e:
                logger.error(f"Failed to list Ollama models: {e}")
                return []

        elif provider == LLMProvider.OPENROUTER:
            # OpenRouter model list
            return [
                "anthropic/claude-3.5-sonnet",
                "anthropic/claude-3-opus",
                "openai/gpt-4-turbo",
                "openai/gpt-4",
                "google/gemini-pro",
                "meta-llama/llama-3-70b-instruct",
            ]

        elif provider == LLMProvider.OPENAI:
            return [
                "gpt-4-turbo-preview",
                "gpt-4",
                "gpt-3.5-turbo",
            ]

        elif provider == LLMProvider.ANTHROPIC:
            return [
                "claude-3-5-sonnet-20241022",
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
            ]

        return []


# Singleton instance
_llm_router: Optional[LLMRouterService] = None


def get_llm_router(
    config: Optional[LLMRouterConfig] = None,
) -> LLMRouterService:
    """
    Get or create LLM Router singleton

    Args:
        config: Optional configuration (only used on first call)

    Returns:
        LLM Router instance
    """

    global _llm_router

    if _llm_router is None:
        _llm_router = LLMRouterService(config)

    return _llm_router
