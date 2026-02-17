"""
LLM Configuration API for Admin

Allows administrators to configure LLM provider settings
for AXE Chat and other AI features.
"""

from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth_deps import require_role

router = APIRouter(prefix="/api/admin/llm-config", tags=["admin", "llm"])


class LLMConfig(BaseModel):
    provider: str = "ollama"  # "ollama" or "openrouter"
    ollamaHost: str = "http://localhost:11434"
    ollamaModel: str = "llama3.2:latest"
    openrouterModel: str = "moonshotai/kimi-k2.5"


# In-memory config storage (replace with database in production)
_current_config = LLMConfig()


@router.get("")
async def get_llm_config(
    principal=Depends(require_role("admin"))
):
    """
    Get current LLM configuration.
    
    Requires admin role.
    """
    return {
        "config": _current_config.dict(),
        "available_providers": ["ollama", "openrouter"],
        "recommendation": "ollama"  # For F&E security
    }


@router.post("")
async def update_llm_config(
    config: LLMConfig,
    principal=Depends(require_role("admin"))
):
    """
    Update LLM configuration.
    
    Requires admin role.
    Validates configuration before saving.
    """
    global _current_config
    
    # Validate provider
    if config.provider not in ["ollama", "openrouter"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider: {config.provider}. Must be 'ollama' or 'openrouter'"
        )
    
    # Security warning for external provider
    if config.provider == "openrouter":
        # Log security warning
        print(f"[SECURITY] Admin {principal.email} configured OpenRouter (external) as LLM provider")
    
    _current_config = config
    
    return {
        "success": True,
        "config": _current_config.dict(),
        "message": f"LLM provider set to {config.provider}"
    }


@router.get("/status")
async def get_llm_status(
    principal=Depends(require_role("admin"))
):
    """
    Get LLM provider status (health check).
    
    Tests connection to configured provider.
    """
    import os
    
    provider = _current_config.provider
    
    status = {
        "provider": provider,
        "configured": True,
        "environment": {
            "OLLAMA_HOST": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            "OPENROUTER_API_KEY": "configured" if os.getenv("OPENROUTER_API_KEY") else "missing",
        }
    }
    
    # Test Ollama connection if selected
    if provider == "ollama":
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{_current_config.ollamaHost}/api/tags")
                if response.status_code == 200:
                    status["health"] = "healthy"
                    status["available_models"] = [m["name"] for m in response.json().get("models", [])]
                else:
                    status["health"] = "unhealthy"
                    status["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            status["health"] = "unreachable"
            status["error"] = str(e)
    
    # Check OpenRouter if selected
    elif provider == "openrouter":
        if os.getenv("OPENROUTER_API_KEY"):
            status["health"] = "configured"
            status["note"] = "API key present. Health check requires actual request."
        else:
            status["health"] = "not_configured"
            status["error"] = "OPENROUTER_API_KEY not set in environment"
    
    return status
