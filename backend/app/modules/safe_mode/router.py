"""
Safe Mode Router (Sprint 7.4)

API endpoints for global safe mode control.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from backend.app.modules.safe_mode.service import get_safe_mode_service


router = APIRouter(prefix="/api/safe-mode", tags=["safe-mode"])


class SafeModeEnableRequest(BaseModel):
    """Request to enable safe mode."""

    reason: str = Field(..., description="Reason for enabling safe mode")


class SafeModeDisableRequest(BaseModel):
    """Request to disable safe mode."""

    reason: str = Field(..., description="Reason for disabling safe mode")


@router.get("/info")
async def get_safe_mode_info():
    """
    Get safe mode information.

    Returns basic information about the safe mode system.
    """
    return {
        "name": "BRAiN Safe Mode",
        "version": "1.0.0",
        "description": "Global kill-switch for instant read-only mode",
        "features": [
            "Instant activation (no restart required)",
            "Blocks all executions and deployments",
            "Allows read-only APIs and monitoring",
            "Full audit trail",
            "Environment variable support",
        ],
        "endpoints": [
            "GET /api/safe-mode/status - Get safe mode status",
            "POST /api/safe-mode/enable - Enable safe mode",
            "POST /api/safe-mode/disable - Disable safe mode",
        ]
    }


@router.get("/status")
async def get_safe_mode_status():
    """
    Get current safe mode status.

    Returns safe mode state, activation time, and blocked/allowed operations.
    """
    try:
        service = get_safe_mode_service()
        status = service.get_status()

        return {
            "success": True,
            **status
        }

    except Exception as e:
        logger.error(f"Failed to get safe mode status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status: {str(e)}"
        )


@router.post("/enable")
async def enable_safe_mode(request: SafeModeEnableRequest):
    """
    Enable safe mode.

    **Blocks:**
    - Factory executions
    - Deployments
    - Bundle loads

    **Allows:**
    - Read-only APIs
    - Monitoring
    - Audit log access
    - Metrics

    **Idempotent:** Can be called multiple times without error.

    **Example Request:**
    ```json
    {
      "reason": "Emergency maintenance"
    }
    ```
    """
    try:
        service = get_safe_mode_service()

        was_enabled = service.enable_safe_mode(
            reason=request.reason,
            enabled_by="api"
        )

        if was_enabled:
            logger.critical(f"🛑 Safe mode ENABLED: {request.reason}")
            message = "Safe mode enabled successfully"
        else:
            logger.warning("Safe mode already enabled")
            message = "Safe mode was already enabled"

        status = service.get_status()

        return {
            "success": True,
            "message": message,
            "was_enabled": was_enabled,
            **status
        }

    except Exception as e:
        logger.error(f"Failed to enable safe mode: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable safe mode: {str(e)}"
        )


@router.post("/disable")
async def disable_safe_mode(request: SafeModeDisableRequest):
    """
    Disable safe mode.

    **Restores:**
    - Factory executions
    - Deployments
    - Bundle loads

    **Idempotent:** Can be called multiple times without error.

    **Example Request:**
    ```json
    {
      "reason": "Maintenance complete"
    }
    ```
    """
    try:
        service = get_safe_mode_service()

        was_disabled = service.disable_safe_mode(
            reason=request.reason,
            disabled_by="api"
        )

        if was_disabled:
            logger.warning(f"✅ Safe mode DISABLED: {request.reason}")
            message = "Safe mode disabled successfully"
        else:
            logger.info("Safe mode already disabled")
            message = "Safe mode was already disabled"

        status = service.get_status()

        return {
            "success": True,
            "message": message,
            "was_disabled": was_disabled,
            **status
        }

    except Exception as e:
        logger.error(f"Failed to disable safe mode: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable safe mode: {str(e)}"
        )
