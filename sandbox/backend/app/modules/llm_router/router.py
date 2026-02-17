"""
LLM Router API Router

REST API endpoints for LLM Router functionality
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Header
from loguru import logger

from .service import get_llm_router
from .schemas import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    RouterInfo,
    ProviderStatus,
    OpenWebUICompatibility,
    ChatMessage,
    MessageRole,
)


# Create router
router = APIRouter(
    prefix="/api/llm-router",
    tags=["llm-router"],
)


@router.get(
    "/info",
    response_model=RouterInfo,
    summary="Get LLM Router information",
)
async def get_router_info():
    """
    Get LLM Router system information

    Returns configuration and available providers.
    """

    llm_router = get_llm_router()

    if not llm_router.initialized:
        raise HTTPException(
            status_code=503,
            detail="LLM Router not initialized",
        )

    return RouterInfo(
        providers=[
            LLMProvider.OLLAMA,
            LLMProvider.OPENROUTER,
            LLMProvider.OPENAI,
            LLMProvider.ANTHROPIC,
        ],
        default_provider=llm_router.config.default_provider,
        fallback_enabled=llm_router.config.enable_fallback,
    )


@router.post(
    "/chat",
    response_model=LLMResponse,
    summary="Send chat request to LLM",
)
async def chat(
    request: LLMRequest,
    x_agent_id: Optional[str] = Header(None),
):
    """
    Send chat request to appropriate LLM provider

    Provider selection:
    - AXE Agent: Always uses Ollama (local)
    - Other agents: Use requested provider or default
    - Fallback: Automatic if enabled

    Headers:
    - X-Agent-Id: Optional agent identifier for routing
    """

    llm_router = get_llm_router()

    if not llm_router.initialized:
        raise HTTPException(
            status_code=503,
            detail="LLM Router not initialized",
        )

    try:
        response = await llm_router.chat(request, agent_id=x_agent_id)
        return response

    except Exception as e:
        logger.error(f"Chat request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"LLM request failed: {str(e)}",
        )


@router.get(
    "/providers",
    response_model=List[ProviderStatus],
    summary="Get provider health status",
)
async def get_provider_status():
    """
    Get health status of all configured providers

    Checks:
    - Provider availability
    - Latency
    - Last check time
    - Error status
    """

    llm_router = get_llm_router()

    if not llm_router.initialized:
        raise HTTPException(
            status_code=503,
            detail="LLM Router not initialized",
        )

    providers = [
        LLMProvider.OLLAMA,
        LLMProvider.OPENROUTER,
        LLMProvider.OPENAI,
        LLMProvider.ANTHROPIC,
    ]

    statuses = []
    for provider in providers:
        try:
            status = await llm_router.check_provider_health(provider)
            statuses.append(status)
        except Exception as e:
            logger.error(f"Health check failed for {provider.value}: {e}")
            statuses.append(
                ProviderStatus(
                    provider=provider,
                    available=False,
                    error=str(e),
                )
            )

    return statuses


@router.get(
    "/providers/{provider}/models",
    response_model=List[str],
    summary="List available models for provider",
)
async def list_models(provider: LLMProvider):
    """
    List available models for specific provider

    Providers:
    - ollama: Queries Ollama API
    - openrouter: Returns supported models
    - openai: Returns available OpenAI models
    - anthropic: Returns available Claude models
    """

    llm_router = get_llm_router()

    if not llm_router.initialized:
        raise HTTPException(
            status_code=503,
            detail="LLM Router not initialized",
        )

    try:
        models = await llm_router.list_available_models(provider)
        return models

    except Exception as e:
        logger.error(f"Failed to list models for {provider.value}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}",
        )


@router.get(
    "/health",
    summary="LLM Router health check",
)
async def health_check():
    """
    Check LLM Router system health

    Returns:
    - Initialization status
    - litellm availability
    - Default provider status
    """

    llm_router = get_llm_router()

    return {
        "status": "healthy" if llm_router.initialized else "unhealthy",
        "initialized": llm_router.initialized,
        "default_provider": llm_router.config.default_provider.value
        if llm_router.initialized
        else None,
    }


# OpenWebUI compatibility endpoints


@router.get(
    "/openwebui/compatibility",
    response_model=OpenWebUICompatibility,
    summary="OpenWebUI compatibility information",
    tags=["openwebui"],
)
async def openwebui_compatibility():
    """
    Get OpenWebUI compatibility information

    Returns API base path and supported features.
    """

    return OpenWebUICompatibility()


@router.post(
    "/openwebui/chat/completions",
    summary="OpenWebUI-compatible chat endpoint",
    tags=["openwebui"],
)
async def openwebui_chat_completions(
    messages: List[dict],
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    stream: bool = False,
):
    """
    OpenWebUI-compatible chat completions endpoint

    Accepts OpenWebUI format and translates to LLM Router format.

    Body:
    - messages: List of {role, content} dicts
    - model: Model name (optional)
    - temperature: Sampling temperature
    - max_tokens: Maximum tokens
    - stream: Enable streaming
    """

    llm_router = get_llm_router()

    if not llm_router.initialized:
        raise HTTPException(
            status_code=503,
            detail="LLM Router not initialized",
        )

    try:
        # Convert to LLM Router format
        chat_messages = []
        for msg in messages:
            role = MessageRole(msg.get("role", "user"))
            content = msg.get("content", "")
            chat_messages.append(
                ChatMessage(role=role, content=content)
            )

        request = LLMRequest(
            messages=chat_messages,
            provider=LLMProvider.AUTO,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
        )

        response = await llm_router.chat(request)

        # Return OpenWebUI-compatible format
        return {
            "id": "chatcmpl-brain",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": response.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response.content,
                    },
                    "finish_reason": response.finish_reason or "stop",
                }
            ],
            "usage": response.usage or {},
        }

    except Exception as e:
        logger.error(f"OpenWebUI chat request failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Chat request failed: {str(e)}",
        )


@router.get(
    "/openwebui/models",
    summary="OpenWebUI-compatible models endpoint",
    tags=["openwebui"],
)
async def openwebui_models():
    """
    OpenWebUI-compatible models list endpoint

    Returns all available models from all providers.
    """

    llm_router = get_llm_router()

    if not llm_router.initialized:
        raise HTTPException(
            status_code=503,
            detail="LLM Router not initialized",
        )

    try:
        all_models = []

        # Get models from each provider
        for provider in [
            LLMProvider.OLLAMA,
            LLMProvider.OPENROUTER,
            LLMProvider.OPENAI,
            LLMProvider.ANTHROPIC,
        ]:
            try:
                models = await llm_router.list_available_models(provider)
                for model in models:
                    all_models.append(
                        {
                            "id": f"{provider.value}/{model}",
                            "object": "model",
                            "created": 0,
                            "owned_by": provider.value,
                        }
                    )
            except Exception as e:
                logger.warning(f"Failed to list models for {provider.value}: {e}")

        return {"data": all_models, "object": "list"}

    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}",
        )


# Import time for OpenWebUI compatibility
import time
