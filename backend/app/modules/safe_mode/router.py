"""
Safe Mode Router (Sprint 7.4)

API endpoints for global safe mode control.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger
from datetime import datetime

from app.modules.safe_mode.service import get_safe_mode_service
from app.core.auth_deps import require_auth, require_role, Principal


router = APIRouter(prefix="/api/safe-mode", tags=["safe-mode"])


class SafeModeEnableRequest(BaseModel):
    """Request to enable safe mode."""

    reason: str = Field(..., description="Reason for enabling safe mode")


class SafeModeDisableRequest(BaseModel):
    """Request to disable safe mode."""

    reason: str = Field(..., description="Reason for disabling safe mode")


# ============================================================================
# Audit Logging Helper
# ============================================================================

def _audit_safe_mode_change(
    action: str,
    principal: Principal,
    reason: str,
    success: bool = True,
    details: dict = None
) -> None:
    """
    Log safe mode state changes for audit trail.
    
    Args:
        action: The action performed (enable/disable)
        principal: The authenticated principal who performed the action
        reason: The reason provided for the action
        success: Whether the action was successful
        details: Additional details to log
    """
    audit_event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event_type": f"safe_mode.{action}",
        "principal_id": principal.principal_id,
        "principal_type": principal.principal_type.value,
        "principal_name": principal.name,
        "principal_email": principal.email,
        "reason": reason,
        "success": success,
        "details": details or {}
    }
    
    logger.bind(audit=True).info(f"Safe mode {action} by {principal.principal_id}", **audit_event)


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
async def get_safe_mode_status(
    principal: Principal = Depends(require_auth)
):
    """
    Get current safe mode status.

    Requires authentication. Returns safe mode state, activation time, 
    and blocked/allowed operations.
    """
    try:
        service = get_safe_mode_service()
        status = service.get_status()

        logger.debug(f"Safe mode status retrieved by {principal.principal_id}")
        
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
async def enable_safe_mode(
    request: SafeModeEnableRequest,
    principal: Principal = Depends(require_role("admin"))
):
    """
    Enable safe mode.

    **Requires ADMIN role.**

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
            enabled_by=principal.principal_id
        )

        if was_enabled:
            logger.critical(f"🛑 Safe mode ENABLED by {principal.principal_id}: {request.reason}")
            _audit_safe_mode_change(
                action="enabled",
                principal=principal,
                reason=request.reason,
                success=True
            )
            message = "Safe mode enabled successfully"
        else:
            logger.warning(f"Safe mode already enabled (requested by {principal.principal_id})")
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
        _audit_safe_mode_change(
            action="enabled",
            principal=principal,
            reason=request.reason,
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable safe mode: {str(e)}"
        )


@router.post("/disable")
async def disable_safe_mode(
    request: SafeModeDisableRequest,
    principal: Principal = Depends(require_role("admin"))
):
    """
    Disable safe mode.

    **Requires ADMIN role.**

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
            disabled_by=principal.principal_id
        )

        if was_disabled:
            logger.warning(f"✅ Safe mode DISABLED by {principal.principal_id}: {request.reason}")
            _audit_safe_mode_change(
                action="disabled",
                principal=principal,
                reason=request.reason,
                success=True
            )
            message = "Safe mode disabled successfully"
        else:
            logger.info(f"Safe mode already disabled (requested by {principal.principal_id})")
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
        _audit_safe_mode_change(
            action="disabled",
            principal=principal,
            reason=request.reason,
            success=False,
            details={"error": str(e)}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable safe mode: {str(e)}"
        )
