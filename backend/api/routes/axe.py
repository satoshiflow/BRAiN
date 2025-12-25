# backend/api/routes/axe.py

"""
AXE (Auxiliary Execution Engine) API

SECURITY GOVERNANCE (G3):
- AXE ist NUR über DMZ Gateways erreichbar
- Direkter Core-Zugriff ist VERBOTEN
- Alle Requests werden auf Trust Tier validiert
- EXTERNAL Requests werden BLOCKIERT (fail-closed)
- Alle Zugriffe werden auditiert

Trust Tiers:
- LOCAL: Localhost (für Admin/Testing) - ALLOWED
- DMZ: Authentifizierte DMZ Gateways - ALLOWED
- EXTERNAL: Unbekannte Quellen - BLOCKED
"""

from __future__ import annotations

import uuid
import inspect
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Header, Depends
from pydantic import BaseModel

from backend.modules.connector_hub.services import get_gateway
from backend.modules.llm_client import get_llm_client
from backend.app.modules.axe_governance import (
    get_axe_trust_validator,
    TrustTier,
    AXERequestContext,
)
from backend.app.modules.sovereign_mode.schemas import (
    AuditEventType,
    AuditSeverity,
)
from backend.app.modules.sovereign_mode.governance_metrics import (
    get_governance_metrics,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/axe",
    tags=["axe"],
)


class AxeMessage(BaseModel):
    message: str
    metadata: Dict[str, Any] | None = None


# ============================================================================
# AUDIT EVENT EMITTER
# ============================================================================


def _emit_axe_audit_event(
    event_type: AuditEventType,
    context: AXERequestContext,
    success: bool,
    reason: str,
    **extra_metadata,
):
    """
    Emit AXE audit event.

    Uses sovereign_mode audit system for governance tracking.
    """
    try:
        from backend.app.modules.sovereign_mode.service import get_sovereign_service

        service = get_sovereign_service()

        metadata = {
            "trust_tier": context.trust_tier.value,
            "source_service": context.source_service,
            "source_ip": context.source_ip,
            "authenticated": context.authenticated,
            "request_id": context.request_id,
            **extra_metadata,
        }

        service._audit(
            event_type=event_type.value,
            success=success,
            severity=(
                AuditSeverity.INFO
                if success
                else (
                    AuditSeverity.ERROR
                    if context.trust_tier == TrustTier.EXTERNAL
                    else AuditSeverity.WARNING
                )
            ),
            reason=reason,
            metadata=metadata,
        )

    except Exception as e:
        logger.error(f"Failed to emit AXE audit event: {e}")


# ============================================================================
# TRUST TIER VALIDATION DEPENDENCY
# ============================================================================


async def validate_axe_request(
    request: Request,
    x_dmz_gateway_id: Optional[str] = Header(None),
    x_dmz_gateway_token: Optional[str] = Header(None),
) -> AXERequestContext:
    """
    Validate AXE request and determine trust tier.

    This is a FastAPI dependency that MUST be used by all AXE endpoints.

    FAIL-CLOSED: EXTERNAL requests are blocked.

    Args:
        request: FastAPI Request
        x_dmz_gateway_id: DMZ Gateway Identifier (Header)
        x_dmz_gateway_token: DMZ Gateway Auth Token (Header)

    Returns:
        AXERequestContext with trust tier

    Raises:
        HTTPException 403: If request is EXTERNAL (untrusted)
    """
    request_id = str(uuid.uuid4())
    client_host = request.client.host if request.client else None

    # Build headers dict
    headers = dict(request.headers)

    # Validate trust tier
    validator = get_axe_trust_validator()
    context = await validator.validate_request(
        headers=headers,
        client_host=client_host,
        request_id=request_id,
    )

    # Emit RECEIVED audit event
    _emit_axe_audit_event(
        event_type=AuditEventType.AXE_REQUEST_RECEIVED,
        context=context,
        success=True,
        reason=f"AXE request received from {context.trust_tier.value} source",
    )

    # Check if request is allowed
    if not validator.is_request_allowed(context):
        # Emit BLOCKED audit event
        _emit_axe_audit_event(
            event_type=AuditEventType.AXE_REQUEST_BLOCKED,
            context=context,
            success=False,
            reason=f"AXE request BLOCKED - trust tier: {context.trust_tier.value}",
        )

        # Emit TRUST TIER VIOLATION
        _emit_axe_audit_event(
            event_type=AuditEventType.AXE_TRUST_TIER_VIOLATION,
            context=context,
            success=False,
            reason=f"EXTERNAL request blocked - source: {context.source_ip}",
        )

        # G4: Record AXE trust tier violation metric
        try:
            metrics = get_governance_metrics()
            metrics.record_axe_trust_violation(context.trust_tier.value)
        except Exception as e:
            logger.warning(f"[G4] Failed to record AXE trust violation metric: {e}")

        raise HTTPException(
            status_code=403,
            detail={
                "error": "Forbidden",
                "message": "AXE is only accessible via DMZ gateways",
                "trust_tier": context.trust_tier.value,
                "request_id": context.request_id,
            },
        )

    return context


# ============================================================================
# LEGACY GATEWAY HELPER (Internal Use Only)
# ============================================================================


async def _call_gateway_send_message(
    gateway: Any,
    *,
    message: str,
    metadata: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """
    Internal helper: Call gateway.send_message().

    Returns None if gateway doesn't implement send_message.
    """
    send = getattr(gateway, "send_message", None)
    if send is None or not callable(send):
        return None

    if inspect.iscoroutinefunction(send):
        result = await send(message=message, metadata=metadata)
    else:
        result = send(message=message, metadata=metadata)
        if inspect.isawaitable(result):
            result = await result

    if isinstance(result, dict):
        return result

    return {"result": result}


# ============================================================================
# AXE API ENDPOINTS
# ============================================================================


@router.get("/info")
async def axe_info(context: AXERequestContext = Depends(validate_axe_request)) -> Dict[str, Any]:
    """
    Get AXE system information.

    **GOVERNANCE**: Trust tier validated, audit logged.

    Returns:
        AXE system info including trust tier
    """
    gateway = get_gateway()
    gateway_name = getattr(gateway, "name", None) if gateway is not None else None

    return {
        "name": "AXE",
        "version": "2.0-governance",
        "status": "online" if gateway is not None else "degraded",
        "description": "Auxiliary Execution Engine (DMZ-Only, Governance-Hardened)",
        "gateway": gateway_name or "none",
        "governance": {
            "trust_tier": context.trust_tier.value,
            "source_service": context.source_service,
            "authenticated": context.authenticated,
            "request_id": context.request_id,
        },
    }


@router.post("/message")
async def axe_message(
    payload: AxeMessage,
    context: AXERequestContext = Depends(validate_axe_request),
) -> Dict[str, Any]:
    """
    Process AXE message.

    **GOVERNANCE**:
    - Only DMZ/LOCAL requests allowed
    - Trust tier validated
    - All requests audited

    **Flow**:
    1. Try Gateway (Connector Hub)
    2. Fallback to LLM

    Args:
        payload: Message payload
        context: Validated request context (injected)

    Returns:
        AXE response with governance metadata
    """
    metadata: Dict[str, Any] = payload.metadata or {}

    # Add governance metadata
    metadata["governance"] = {
        "trust_tier": context.trust_tier.value,
        "source_service": context.source_service,
        "request_id": context.request_id,
    }

    # ---------------------------------------------------------------------
    # 1) Try Gateway (Connector Hub)
    # ---------------------------------------------------------------------
    gateway = get_gateway()
    if gateway is not None:
        try:
            gw_result = await _call_gateway_send_message(
                gateway,
                message=payload.message,
                metadata=metadata,
            )
        except Exception as exc:
            logger.error(f"AXE gateway send_message failed: {exc}")
            gw_result = None

        if gw_result is not None:
            reply_text = (
                gw_result.get("reply")
                or gw_result.get("message")
                or gw_result.get("text")
                or ""
            )

            # Emit FORWARDED audit event
            _emit_axe_audit_event(
                event_type=AuditEventType.AXE_REQUEST_FORWARDED,
                context=context,
                success=True,
                reason=f"AXE request forwarded to gateway: {getattr(gateway, 'name', 'unknown')}",
                gateway=getattr(gateway, "name", "unknown"),
            )

            return {
                "mode": "gateway",
                "gateway": getattr(gateway, "name", "unknown"),
                "input_message": payload.message,
                "reply": reply_text,
                "metadata": metadata,
                "result": gw_result,
                "governance": {
                    "trust_tier": context.trust_tier.value,
                    "source_service": context.source_service,
                    "request_id": context.request_id,
                },
            }

    # ---------------------------------------------------------------------
    # 2) Fallback: LLM
    # ---------------------------------------------------------------------
    client = get_llm_client()
    system_prompt = (
        "Du bist AXE, die Execution-Engine von BRAiN. "
        "Beantworte oder kommentiere die Nachricht kurz und präzise."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": payload.message},
    ]

    try:
        reply_text, raw = await client.simple_chat(
            messages=messages,
            extra_params=None,
        )
    except Exception as exc:
        logger.error(f"AXE LLM fallback failed: {exc}")
        return {
            "mode": "llm-fallback-error",
            "gateway": getattr(gateway, "name", "none") if gateway else "none",
            "input_message": payload.message,
            "reply": "",
            "metadata": metadata,
            "error": str(exc),
            "governance": {
                "trust_tier": context.trust_tier.value,
                "source_service": context.source_service,
                "request_id": context.request_id,
            },
        }

    # Emit FORWARDED audit event (LLM fallback)
    _emit_axe_audit_event(
        event_type=AuditEventType.AXE_REQUEST_FORWARDED,
        context=context,
        success=True,
        reason="AXE request processed via LLM fallback",
        mode="llm_fallback",
    )

    return {
        "mode": "llm-fallback",
        "gateway": getattr(gateway, "name", "none") if gateway else "none",
        "input_message": payload.message,
        "reply": reply_text,
        "metadata": metadata,
        "result": {
            "raw_llm": raw,
        },
        "governance": {
            "trust_tier": context.trust_tier.value,
            "source_service": context.source_service,
            "request_id": context.request_id,
        },
    }


# End of file
