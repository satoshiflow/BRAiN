"""
Connectors Module - FastAPI Router

REST endpoints for connector management, health, and messaging.
Auto-discovered by main.py via router attribute.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from loguru import logger

from app.core.auth_deps import require_auth, require_operator, get_current_principal, Principal

from app.modules.connectors.schemas import (
    ConnectorActionRequest,
    ConnectorActionResponse,
    ConnectorHealth,
    ConnectorInfo,
    ConnectorListResponse,
    ConnectorType,
    SendMessageRequest,
    SendMessageResponse,
)
from app.modules.connectors.service import get_connector_service

router = APIRouter(
    prefix="/api/connectors/v2",
    tags=["connectors-v2"],
    dependencies=[Depends(require_auth)]
)


# ============================================================================
# Info
# ============================================================================


@router.get("/info")
async def get_info() -> Dict[str, Any]:
    """Get connector system information."""
    service = get_connector_service()
    return {
        "name": "BRAIN Connectors",
        "version": "1.0.0",
        "description": "Multi-Interface Connector System",
        "supported_types": [t.value for t in ConnectorType],
        "stats": service.get_aggregate_stats(),
    }


# ============================================================================
# Registry
# ============================================================================


@router.get("/list", response_model=ConnectorListResponse)
async def list_connectors(
    connector_type: Optional[ConnectorType] = None,
    active_only: bool = False,
) -> ConnectorListResponse:
    """List all registered connectors with optional filters."""
    service = get_connector_service()

    if active_only:
        connectors = service.list_active()
    elif connector_type:
        connectors = service.list_by_type(connector_type)
    else:
        connectors = service.list_connectors()

    return ConnectorListResponse(connectors=connectors, total=len(connectors))


@router.get("/{connector_id}", response_model=ConnectorInfo)
async def get_connector(connector_id: str) -> ConnectorInfo:
    """Get details for a specific connector."""
    service = get_connector_service()
    connector = service.get(connector_id)
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")
    return connector.info


# ============================================================================
# Lifecycle
# ============================================================================


@router.post("/{connector_id}/action", response_model=ConnectorActionResponse)
async def connector_action(
    connector_id: str,
    request: ConnectorActionRequest,
) -> ConnectorActionResponse:
    """Perform an action on a connector (start, stop, restart)."""
    service = get_connector_service()
    connector = service.get(connector_id)

    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")

    action = request.action.lower()

    try:
        if action == "start":
            success = await service.start_connector(connector_id)
        elif action == "stop":
            success = await service.stop_connector(connector_id)
        elif action == "restart":
            success = await service.restart_connector(connector_id)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action: {action}. Use start, stop, or restart.",
            )

        return ConnectorActionResponse(
            connector_id=connector_id,
            action=action,
            success=success,
            message=f"Connector {action} {'succeeded' if success else 'failed'}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Connector action failed: {e}")
        return ConnectorActionResponse(
            connector_id=connector_id,
            action=action,
            success=False,
            error=str(e),
        )


# ============================================================================
# Health
# ============================================================================


@router.get("/{connector_id}/health", response_model=ConnectorHealth)
async def connector_health(connector_id: str) -> ConnectorHealth:
    """Run health check on a specific connector."""
    service = get_connector_service()
    health = await service.health_check(connector_id)
    if not health:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")
    return health


@router.get("/health/all", response_model=List[ConnectorHealth])
async def all_health() -> List[ConnectorHealth]:
    """Run health checks on all connectors."""
    service = get_connector_service()
    return await service.health_check_all()


# ============================================================================
# Stats
# ============================================================================


@router.get("/stats/aggregate")
async def aggregate_stats() -> Dict[str, Any]:
    """Get aggregated statistics across all connectors."""
    service = get_connector_service()
    return service.get_aggregate_stats()


@router.get("/{connector_id}/stats")
async def connector_stats(connector_id: str) -> Dict[str, Any]:
    """Get statistics for a specific connector."""
    service = get_connector_service()
    stats = service.get_stats(connector_id)
    if not stats:
        raise HTTPException(status_code=404, detail=f"Connector not found: {connector_id}")
    return stats.model_dump()


# ============================================================================
# Messaging
# ============================================================================


@router.post("/send", response_model=SendMessageResponse)
async def send_message(request: SendMessageRequest) -> SendMessageResponse:
    """Send a message through a specific connector to a user."""
    service = get_connector_service()
    connector = service.get(request.connector_id)

    if not connector:
        raise HTTPException(
            status_code=404,
            detail=f"Connector not found: {request.connector_id}",
        )

    from app.modules.connectors.schemas import OutgoingMessage

    message = OutgoingMessage(
        content=request.content,
        content_type=request.content_type,
        metadata=request.metadata,
    )

    try:
        success = await connector.send_to_user(request.user_id, message)
        return SendMessageResponse(
            success=success,
            message_id=message.message_id,
        )
    except Exception as e:
        logger.error(f"Failed to send message via {request.connector_id}: {e}")
        return SendMessageResponse(
            success=False,
            error=str(e),
        )
