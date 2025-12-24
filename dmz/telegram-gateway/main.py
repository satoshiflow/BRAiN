"""
BRAiN DMZ - Telegram Gateway (Minimal Stub)

Transport-only gateway for Telegram Bot API.
No business logic - only message forwarding to Core API.

Security:
- ENV-based configuration only
- No secrets in code
- Authentication via header token
- Stateless design

Version: 1.0.0
Phase: B.2 - DMZ Gateway Foundation
"""

import os
import sys
from typing import Any, Dict, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Request, status
from pydantic import BaseModel, Field
import httpx
from loguru import logger

# ============================================================================
# Configuration
# ============================================================================

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_MODE = os.getenv("TELEGRAM_MODE", "polling")  # polling or webhook
BRAIN_CORE_API_URL = os.getenv("BRAIN_CORE_API_URL", "http://brain-backend:8000")
BRAIN_CORE_API_TOKEN = os.getenv("BRAIN_CORE_API_TOKEN", "")
GATEWAY_NAME = os.getenv("DMZ_GATEWAY_NAME", "telegram-gateway")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    level=LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
)

# ============================================================================
# Models
# ============================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    gateway: str
    version: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    core_api_reachable: bool = False


class TelegramWebhookPayload(BaseModel):
    """Telegram webhook payload (simplified)."""
    update_id: int
    message: Optional[Dict[str, Any]] = None
    edited_message: Optional[Dict[str, Any]] = None
    callback_query: Optional[Dict[str, Any]] = None


class ForwardResponse(BaseModel):
    """Forward response from core."""
    success: bool
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="BRAiN DMZ - Telegram Gateway",
    description="Transport-only gateway for Telegram Bot API",
    version="1.0.0",
    docs_url="/docs" if LOG_LEVEL == "DEBUG" else None,
    redoc_url=None,
)


# ============================================================================
# HTTP Client for Core API
# ============================================================================

async def call_core_api(
    method: str,
    endpoint: str,
    payload: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Call BRAiN Core API.

    Args:
        method: HTTP method (GET, POST, etc.)
        endpoint: API endpoint path (e.g., /api/telegram/webhook)
        payload: Request payload
        timeout: Request timeout

    Returns:
        Response data from core API

    Raises:
        HTTPException: If core API is unreachable or returns error
    """
    url = f"{BRAIN_CORE_API_URL}{endpoint}"
    headers = {}

    if BRAIN_CORE_API_TOKEN:
        headers["Authorization"] = f"Bearer {BRAIN_CORE_API_TOKEN}"

    try:
        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, timeout=timeout)
            elif method.upper() == "POST":
                response = await client.post(
                    url, json=payload, headers=headers, timeout=timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        logger.error(f"Core API timeout: {url}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Core API timeout",
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"Core API error: {e.response.status_code} - {url}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Core API error: {e.response.text}",
        )
    except Exception as e:
        logger.error(f"Failed to call core API: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Core API unreachable",
        )


# ============================================================================
# Endpoints
# ============================================================================

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint."""
    return {
        "name": GATEWAY_NAME,
        "version": "1.0.0",
        "type": "transport-only",
        "status": "active",
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    core_reachable = False

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BRAIN_CORE_API_URL}/health",
                timeout=5.0,
            )
            core_reachable = response.status_code == 200
    except Exception:
        pass

    return HealthResponse(
        status="healthy",
        gateway=GATEWAY_NAME,
        version="1.0.0",
        core_api_reachable=core_reachable,
    )


@app.post("/webhook/telegram")
async def telegram_webhook(payload: TelegramWebhookPayload):
    """
    Telegram webhook endpoint.

    Receives updates from Telegram Bot API and forwards to Core API.
    No business logic - pure transport layer.

    Security:
    - Telegram validates webhook via HTTPS + secret token
    - Core API validates via Bearer token
    """
    logger.info(f"Received Telegram update: {payload.update_id}")

    # Forward to Core API
    try:
        response = await call_core_api(
            method="POST",
            endpoint="/api/telegram/webhook",  # Core API endpoint
            payload=payload.model_dump(),
            timeout=30.0,
        )

        logger.info(f"Forwarded to Core API, response: {response}")
        return response

    except HTTPException as e:
        logger.error(f"Failed to forward to Core: {e.detail}")
        raise


@app.get("/status")
async def gateway_status():
    """
    Gateway status endpoint.

    Returns:
        Gateway status and configuration (no secrets).
    """
    return {
        "gateway": GATEWAY_NAME,
        "version": "1.0.0",
        "mode": TELEGRAM_MODE,
        "core_api_url": BRAIN_CORE_API_URL,
        "telegram_configured": bool(TELEGRAM_BOT_TOKEN),
        "core_token_configured": bool(BRAIN_CORE_API_TOKEN),
    }


# ============================================================================
# Startup / Shutdown
# ============================================================================

@app.on_event("startup")
async def startup():
    """Startup tasks."""
    logger.info(f"Starting {GATEWAY_NAME} v1.0.0")
    logger.info(f"Mode: {TELEGRAM_MODE}")
    logger.info(f"Core API: {BRAIN_CORE_API_URL}")

    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set - webhook will fail")

    if not BRAIN_CORE_API_TOKEN:
        logger.warning("BRAIN_CORE_API_TOKEN not set - authentication disabled")


@app.on_event("shutdown")
async def shutdown():
    """Shutdown tasks."""
    logger.info(f"Shutting down {GATEWAY_NAME}")


# ============================================================================
# Run (for local development only)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level=LOG_LEVEL.lower(),
    )
