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
import json
import asyncio
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Header, Depends, WebSocket, WebSocketDisconnect
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

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/axe",
    tags=["axe"],
)


# ============================================================================
# WEBSOCKET CONNECTION MANAGER
# ============================================================================


class AxeConnectionManager:
    """
    Manages WebSocket connections for real-time AXE communication.

    Each session can have one active WebSocket connection for:
    - Real-time code diff streaming
    - Live chat updates
    - File change notifications
    """

    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket):
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            # Disconnect existing connection for this session
            if session_id in self.active_connections:
                try:
                    await self.active_connections[session_id].close()
                except Exception:
                    pass
            self.active_connections[session_id] = websocket
        logger.info(f"AXE WebSocket connected: session={session_id}")

    async def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if session_id in self.active_connections:
                del self.active_connections[session_id]
        logger.info(f"AXE WebSocket disconnected: session={session_id}")

    async def send_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """
        Send a message to a specific session.

        Returns True if sent successfully, False if session not connected.
        """
        async with self._lock:
            websocket = self.active_connections.get(session_id)

        if not websocket:
            return False

        try:
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send WebSocket message to {session_id}: {e}")
            await self.disconnect(session_id)
            return False

    async def send_diff(self, session_id: str, diff: Dict[str, Any]):
        """Send a code diff to the client for Apply/Reject workflow."""
        return await self.send_message(session_id, {
            "type": "diff",
            "payload": diff
        })

    async def send_file_update(self, session_id: str, file_id: str, content: str):
        """Notify client of a file content update."""
        return await self.send_message(session_id, {
            "type": "file_update",
            "payload": {
                "file_id": file_id,
                "content": content
            }
        })

    async def send_chat_response(self, session_id: str, message: str, metadata: Optional[Dict] = None):
        """Send a chat response message."""
        return await self.send_message(session_id, {
            "type": "chat_response",
            "payload": {
                "message": message,
                "metadata": metadata or {}
            }
        })

    def is_connected(self, session_id: str) -> bool:
        """Check if a session has an active WebSocket connection."""
        return session_id in self.active_connections


# Global connection manager instance
connection_manager = AxeConnectionManager()


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


# ============================================================================
# AXE WIDGET CONFIG ENDPOINT
# ============================================================================


@router.get("/config/{app_id}")
async def axe_config(
    app_id: str,
    context: AXERequestContext = Depends(validate_axe_request),
) -> Dict[str, Any]:
    """
    Get AXE widget configuration for a specific app.

    **GOVERNANCE**: Trust tier validated, audit logged.

    Args:
        app_id: Application identifier (e.g., 'fewoheros', 'satoshiflow')
        context: Validated request context (injected)

    Returns:
        Widget configuration
    """
    # Default configuration
    config = {
        "app_id": app_id,
        "display_name": f"{app_id.replace('_', ' ').title()} Assistant",
        "avatar_url": None,
        "theme": "dark",
        "position": {"bottom": 20, "right": 20},
        "default_open": False,
        "mode": "assistant",
        "training_mode": "per_app",
        "allowed_scopes": [],
        "knowledge_spaces": [],
        "rate_limits": {
            "requests_per_minute": 10,
            "burst": 5
        },
        "telemetry": {
            "enabled": True,
            "anonymization_level": "pseudonymized",
            "training_mode": "per_app",
            "collect_context_snapshots": True,
            "upload_interval_ms": 30000
        },
        "permissions": {
            "can_run_tools": True,
            "can_trigger_actions": False,
            "can_access_apis": []
        },
        "ui": {
            "show_context_panel": True,
            "show_mode_selector": True,
            "enable_canvas": True
        },
        "governance": {
            "trust_tier": context.trust_tier.value,
            "source_service": context.source_service,
            "request_id": context.request_id,
        }
    }

    # App-specific configurations
    if app_id == "fewoheros":
        config.update({
            "display_name": "FeWoHeroes Assistant",
            "allowed_scopes": ["bookings", "properties", "guests"],
            "knowledge_spaces": ["fewoheros_docs", "booking_faq"],
            "permissions": {
                "can_run_tools": True,
                "can_trigger_actions": True,
                "can_access_apis": ["bookings", "properties"]
            }
        })
    elif app_id == "satoshiflow":
        config.update({
            "display_name": "SatoshiFlow Assistant",
            "allowed_scopes": ["transactions", "wallets", "analytics"],
            "knowledge_spaces": ["satoshiflow_docs", "crypto_faq"],
            "permissions": {
                "can_run_tools": True,
                "can_trigger_actions": False,
                "can_access_apis": ["transactions", "wallets"]
            }
        })
    elif app_id in ["widget-test", "axe-test"]:
        config.update({
            "display_name": "AXE Test Mode",
            "mode": "builder",
            "ui": {
                "show_context_panel": True,
                "show_mode_selector": True,
                "enable_canvas": True
            }
        })

    # Emit audit event
    _emit_axe_audit_event(
        event_type=AuditEventType.AXE_REQUEST_RECEIVED,
        context=context,
        success=True,
        reason=f"AXE config requested for app: {app_id}",
        app_id=app_id,
    )

    return config


# ============================================================================
# AXE WEBSOCKET ENDPOINT
# ============================================================================


@router.websocket("/ws/{session_id}")
async def axe_websocket(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time AXE communication.

    **Features**:
    - Real-time code diff streaming
    - Live chat responses
    - File change notifications
    - Apply/Reject feedback

    **Message Types from Client**:
    - `chat`: User chat message
    - `diff_applied`: User applied a diff
    - `diff_rejected`: User rejected a diff
    - `file_updated`: File content changed
    - `ping`: Keep-alive ping

    **Message Types to Client**:
    - `chat_response`: Assistant response
    - `diff`: Code diff for Apply/Reject
    - `file_update`: File content update
    - `pong`: Keep-alive pong

    Args:
        websocket: WebSocket connection
        session_id: Client session identifier
    """
    await connection_manager.connect(session_id, websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": "Invalid JSON"}
                })
                continue

            message_type = message.get("type")
            payload = message.get("payload", {})

            # ----------------------------------------------------------------
            # Handle: chat
            # ----------------------------------------------------------------
            if message_type == "chat":
                user_message = payload.get("message", "")
                metadata = payload.get("metadata", {})

                # Process chat message via LLM
                client = get_llm_client()
                system_prompt = (
                    "Du bist AXE, die Execution-Engine von BRAiN. "
                    "Beantworte kurz und präzise. Du kannst Code vorschlagen."
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ]

                try:
                    reply_text, raw = await client.simple_chat(
                        messages=messages,
                        extra_params=None,
                    )

                    # Send chat response back
                    await connection_manager.send_chat_response(
                        session_id,
                        message=reply_text,
                        metadata={"raw_llm": raw}
                    )

                    # Example: Generate a mock diff for demonstration
                    # In production, parse LLM response for code blocks
                    if "code" in user_message.lower() or "function" in user_message.lower():
                        mock_diff = {
                            "id": str(uuid.uuid4()),
                            "fileId": "demo-file-1",
                            "fileName": "example.tsx",
                            "language": "typescript",
                            "oldContent": "// Old code\n",
                            "newContent": f"// Generated by AXE\n{reply_text}\n",
                            "description": "Code suggestion from AXE"
                        }
                        await connection_manager.send_diff(session_id, mock_diff)

                except Exception as exc:
                    logger.error(f"WebSocket chat error: {exc}")
                    await websocket.send_json({
                        "type": "error",
                        "payload": {"message": str(exc)}
                    })

            # ----------------------------------------------------------------
            # Handle: diff_applied
            # ----------------------------------------------------------------
            elif message_type == "diff_applied":
                diff_id = payload.get("diff_id")
                logger.info(f"Diff applied: {diff_id} in session {session_id}")

                # Send confirmation
                await websocket.send_json({
                    "type": "diff_applied_confirmed",
                    "payload": {"diff_id": diff_id}
                })

            # ----------------------------------------------------------------
            # Handle: diff_rejected
            # ----------------------------------------------------------------
            elif message_type == "diff_rejected":
                diff_id = payload.get("diff_id")
                logger.info(f"Diff rejected: {diff_id} in session {session_id}")

                # Send confirmation
                await websocket.send_json({
                    "type": "diff_rejected_confirmed",
                    "payload": {"diff_id": diff_id}
                })

            # ----------------------------------------------------------------
            # Handle: file_updated
            # ----------------------------------------------------------------
            elif message_type == "file_updated":
                file_id = payload.get("file_id")
                content = payload.get("content")
                logger.info(f"File updated: {file_id} in session {session_id}")

                # Could trigger analysis, linting, etc.
                # For now, just acknowledge
                await websocket.send_json({
                    "type": "file_updated_confirmed",
                    "payload": {"file_id": file_id}
                })

            # ----------------------------------------------------------------
            # Handle: ping (keep-alive)
            # ----------------------------------------------------------------
            elif message_type == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "payload": {"timestamp": payload.get("timestamp")}
                })

            # ----------------------------------------------------------------
            # Unknown message type
            # ----------------------------------------------------------------
            else:
                logger.warning(f"Unknown WebSocket message type: {message_type}")
                await websocket.send_json({
                    "type": "error",
                    "payload": {"message": f"Unknown message type: {message_type}"}
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
    finally:
        await connection_manager.disconnect(session_id)


# ============================================================================
# EVENT TELEMETRY ENDPOINTS (Phase 3)
# ============================================================================

from backend.app.modules.telemetry.schemas import (
    AxeEventCreate,
    AxeEventBatchCreate,
    AxeEventResponse,
    AxeEventStats,
    AxeEventQuery,
)
from backend.app.modules.telemetry.service import get_telemetry_service
from backend.app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession


@router.post("/events", response_model=list[AxeEventResponse])
async def create_axe_events(
    payload: AxeEventCreate | AxeEventBatchCreate,
    context: AXERequestContext = Depends(validate_axe_request),
    db: AsyncSession = Depends(get_db),
) -> list[AxeEventResponse]:
    """
    Create AXE event(s) for telemetry tracking.

    **Features:**
    - Single event or batch upload (up to 100 events)
    - Automatic anonymization based on privacy settings
    - DSGVO-compliant data storage
    - Training data opt-in support

    **Example (Single Event):**
    ```json
    {
      "event_type": "axe_message",
      "session_id": "session-abc123",
      "app_id": "widget-test",
      "event_data": {
        "message": "Hello AXE",
        "role": "user"
      },
      "anonymization_level": "pseudonymized"
    }
    ```

    **Example (Batch):**
    ```json
    {
      "events": [
        { "event_type": "axe_message", ... },
        { "event_type": "axe_click", ... }
      ]
    }
    ```

    **Returns:**
    List of created events with IDs and timestamps.
    """
    telemetry_service = get_telemetry_service()

    # Determine if single event or batch
    if isinstance(payload, AxeEventBatchCreate):
        # Batch upload
        logger.info(f"Batch telemetry upload: {len(payload.events)} events from {context.trust_tier}")
        created_events = await telemetry_service.create_events_batch(db, payload.events)
        return created_events
    else:
        # Single event
        logger.info(f"Single telemetry event: {payload.event_type} from {context.trust_tier}")
        created_event = await telemetry_service.create_event(db, payload)
        return [created_event]


@router.get("/events", response_model=list[AxeEventResponse])
async def query_axe_events(
    session_id: Optional[str] = None,
    app_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    context: AXERequestContext = Depends(validate_axe_request),
    db: AsyncSession = Depends(get_db),
) -> list[AxeEventResponse]:
    """
    Query AXE events with filters.

    **Query Parameters:**
    - session_id: Filter by session
    - app_id: Filter by app
    - user_id: Filter by user (anonymized)
    - limit: Max results (1-1000, default 100)
    - offset: Pagination offset

    **Example:**
    ```
    GET /api/axe/events?session_id=session-abc123&limit=50
    ```

    **Returns:**
    List of matching events, ordered by created_at DESC.
    """
    telemetry_service = get_telemetry_service()

    query_params = AxeEventQuery(
        session_id=session_id,
        app_id=app_id,
        user_id=user_id,
        limit=limit,
        offset=offset,
    )

    events = await telemetry_service.query_events(db, query_params)
    logger.info(f"Queried {len(events)} events for session={session_id}, app={app_id}")
    return events


@router.get("/events/stats", response_model=AxeEventStats)
async def get_axe_event_stats(
    session_id: Optional[str] = None,
    app_id: Optional[str] = None,
    context: AXERequestContext = Depends(validate_axe_request),
    db: AsyncSession = Depends(get_db),
) -> AxeEventStats:
    """
    Get statistics for AXE events.

    **Query Parameters:**
    - session_id: Filter by session
    - app_id: Filter by app

    **Example:**
    ```
    GET /api/axe/events/stats?app_id=widget-test
    ```

    **Returns:**
    ```json
    {
      "total_events": 1234,
      "event_type_counts": {
        "axe_message": 567,
        "axe_click": 345,
        "axe_diff_applied": 89
      },
      "sessions": 42,
      "apps": ["widget-test", "fewoheros"],
      "date_range": {
        "start": "2026-01-01T00:00:00Z",
        "end": "2026-01-10T23:59:59Z"
      },
      "anonymization_breakdown": {
        "pseudonymized": 1100,
        "strict": 134
      }
    }
    ```
    """
    telemetry_service = get_telemetry_service()
    stats = await telemetry_service.get_stats(db, session_id=session_id, app_id=app_id)
    logger.info(f"Event stats: {stats.total_events} events, {stats.sessions} sessions")
    return stats


# End of file
