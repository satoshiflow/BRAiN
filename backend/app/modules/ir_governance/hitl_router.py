"""
HITL (Human-in-the-Loop) API Router - Sprint 11

REST API endpoints for approval UI.

Endpoints:
- GET /api/ir/approvals/pending - List pending approvals
- GET /api/ir/approvals/{approval_id} - Get approval details
- GET /api/ir/approvals/stats - Get approval statistics
- GET /api/ir/approvals/health - Health check for approval system
- POST /api/ir/approvals/{approval_id}/acknowledge - Acknowledge approval (for UI tracking)

WebSocket:
- /ws/ir/approvals - Real-time approval notifications
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field
from loguru import logger

from backend.app.modules.ir_governance.schemas import (
    ApprovalRequest,
    ApprovalStatus,
)
from backend.app.modules.ir_governance.approvals import get_approvals_service
from backend.app.modules.ir_governance.approval_cleanup_worker import get_cleanup_worker
from backend.app.modules.ir_governance.redis_approval_store import RedisApprovalStore


router = APIRouter(prefix="/api/ir/approvals", tags=["HITL Approvals"])


# ============================================================================
# SCHEMAS
# ============================================================================


class ApprovalListResponse(BaseModel):
    """Response for approval list."""
    approvals: List[ApprovalRequest]
    total: int = Field(..., description="Total approvals in list")
    pending: int = Field(..., description="Number of pending approvals")
    consumed: int = Field(..., description="Number of consumed approvals")
    expired: int = Field(..., description="Number of expired approvals")


class ApprovalStatsResponse(BaseModel):
    """Approval system statistics."""
    by_status: Dict[str, int] = Field(..., description="Count by status")
    cleanup_worker: Optional[Dict[str, Any]] = Field(None, description="Cleanup worker stats")


class ApprovalHealthResponse(BaseModel):
    """Health check response."""
    healthy: bool
    redis_available: bool
    cleanup_worker: Optional[Dict[str, Any]] = None
    message: str


class AcknowledgeRequest(BaseModel):
    """Request to acknowledge approval (UI tracking)."""
    acknowledged_by: str = Field(..., description="User/email who acknowledged")


# ============================================================================
# REST ENDPOINTS
# ============================================================================


@router.get("/pending")
async def list_pending_approvals(
    tenant_id: str = Query(..., description="Tenant ID"),
    limit: int = Query(100, ge=1, le=1000, description="Max results")
) -> ApprovalListResponse:
    """
    List pending approvals for a tenant.

    Returns approvals with status=PENDING, sorted by created_at descending.

    Args:
        tenant_id: Tenant ID
        limit: Maximum number of results (default: 100, max: 1000)

    Returns:
        List of pending approvals with counts
    """
    service = get_approvals_service()
    store = service.store

    # Check if using Redis store (for list_by_tenant method)
    if not isinstance(store, RedisApprovalStore):
        raise HTTPException(
            status_code=501,
            detail="Listing approvals requires RedisApprovalStore (Sprint 11)"
        )

    try:
        # Get all approvals for tenant
        all_approvals = await store.list_by_tenant(tenant_id, limit=limit)

        # Count by status
        counts = {
            ApprovalStatus.PENDING: 0,
            ApprovalStatus.CONSUMED: 0,
            ApprovalStatus.EXPIRED: 0,
        }
        for approval in all_approvals:
            counts[approval.status] = counts.get(approval.status, 0) + 1

        # Filter pending
        pending_approvals = [
            a for a in all_approvals if a.status == ApprovalStatus.PENDING
        ]

        return ApprovalListResponse(
            approvals=pending_approvals,
            total=len(all_approvals),
            pending=counts[ApprovalStatus.PENDING],
            consumed=counts[ApprovalStatus.CONSUMED],
            expired=counts[ApprovalStatus.EXPIRED],
        )

    except Exception as e:
        logger.error(f"[HITL API] Failed to list pending approvals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{approval_id}")
async def get_approval(approval_id: str) -> ApprovalRequest:
    """
    Get approval details by ID.

    Args:
        approval_id: Approval ID

    Returns:
        ApprovalRequest

    Raises:
        404: If approval not found
    """
    service = get_approvals_service()

    try:
        approval = service.get_approval_status(approval_id)

        if not approval:
            raise HTTPException(
                status_code=404,
                detail=f"Approval not found: {approval_id}"
            )

        return approval

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HITL API] Failed to get approval {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_approval_stats(
    tenant_id: str = Query(..., description="Tenant ID")
) -> ApprovalStatsResponse:
    """
    Get approval statistics for a tenant.

    Args:
        tenant_id: Tenant ID

    Returns:
        Statistics including counts by status and cleanup worker stats
    """
    service = get_approvals_service()
    store = service.store

    # Check if using Redis store
    if not isinstance(store, RedisApprovalStore):
        raise HTTPException(
            status_code=501,
            detail="Approval stats require RedisApprovalStore (Sprint 11)"
        )

    try:
        # Get counts by status
        counts = await store.count_by_status(tenant_id)

        # Get cleanup worker stats (if available)
        cleanup_worker = get_cleanup_worker()
        cleanup_stats = cleanup_worker.get_stats() if cleanup_worker else None

        return ApprovalStatsResponse(
            by_status=counts,
            cleanup_worker=cleanup_stats,
        )

    except Exception as e:
        logger.error(f"[HITL API] Failed to get approval stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check() -> ApprovalHealthResponse:
    """
    Health check for approval system.

    Checks:
    - Redis availability (if using RedisApprovalStore)
    - Cleanup worker status

    Returns:
        Health status with details
    """
    service = get_approvals_service()
    store = service.store

    # Check Redis health
    redis_healthy = True
    if isinstance(store, RedisApprovalStore):
        redis_healthy = await store.health_check()

    # Check cleanup worker health
    cleanup_worker = get_cleanup_worker()
    cleanup_health = None
    if cleanup_worker:
        cleanup_health = await cleanup_worker.health_check()

    # Overall health
    healthy = redis_healthy and (cleanup_health is None or cleanup_health.get("healthy", True))

    message = "Approval system is healthy"
    if not redis_healthy:
        message = "Redis is unhealthy"
    elif cleanup_health and not cleanup_health.get("healthy"):
        message = cleanup_health.get("message", "Cleanup worker is unhealthy")

    return ApprovalHealthResponse(
        healthy=healthy,
        redis_available=redis_healthy,
        cleanup_worker=cleanup_health,
        message=message,
    )


@router.post("/{approval_id}/acknowledge")
async def acknowledge_approval(
    approval_id: str,
    request: AcknowledgeRequest
) -> Dict[str, Any]:
    """
    Acknowledge approval (UI tracking).

    This doesn't consume the approval, just marks that a human has seen it.
    Useful for UI tracking and audit trail.

    Args:
        approval_id: Approval ID
        request: Acknowledge request

    Returns:
        Success response

    Raises:
        404: If approval not found
    """
    service = get_approvals_service()

    try:
        approval = service.get_approval_status(approval_id)

        if not approval:
            raise HTTPException(
                status_code=404,
                detail=f"Approval not found: {approval_id}"
            )

        # Log acknowledgement (audit trail)
        logger.info(
            f"[HITL API] ir.approval_acknowledged: "
            f"approval_id={approval_id}, "
            f"tenant_id={approval.tenant_id}, "
            f"ir_hash={approval.ir_hash[:16]}..., "
            f"acknowledged_by={request.acknowledged_by}"
        )

        return {
            "success": True,
            "approval_id": approval_id,
            "acknowledged_by": request.acknowledged_by,
            "message": "Approval acknowledged successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[HITL API] Failed to acknowledge approval {approval_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================


class ApprovalConnectionManager:
    """Manages WebSocket connections for approval notifications."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}  # tenant_id -> [websockets]

    async def connect(self, websocket: WebSocket, tenant_id: str):
        """Connect WebSocket for tenant."""
        await websocket.accept()
        if tenant_id not in self.active_connections:
            self.active_connections[tenant_id] = []
        self.active_connections[tenant_id].append(websocket)
        logger.info(f"[HITL WebSocket] Client connected: tenant_id={tenant_id}")

    def disconnect(self, websocket: WebSocket, tenant_id: str):
        """Disconnect WebSocket."""
        if tenant_id in self.active_connections:
            self.active_connections[tenant_id].remove(websocket)
            if not self.active_connections[tenant_id]:
                del self.active_connections[tenant_id]
        logger.info(f"[HITL WebSocket] Client disconnected: tenant_id={tenant_id}")

    async def broadcast_to_tenant(self, tenant_id: str, message: dict):
        """Broadcast message to all connections for a tenant."""
        if tenant_id not in self.active_connections:
            return

        for connection in self.active_connections[tenant_id]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"[HITL WebSocket] Failed to send message: {e}")


# Singleton
_connection_manager = ApprovalConnectionManager()


def get_connection_manager() -> ApprovalConnectionManager:
    """Get WebSocket connection manager."""
    return _connection_manager


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    """
    WebSocket endpoint for real-time approval notifications.

    Query params:
        tenant_id: Tenant ID to subscribe to

    Messages sent to client:
        - approval_created: New approval created (ESCALATE)
        - approval_consumed: Approval consumed
        - approval_expired: Approval expired
        - heartbeat: Keep-alive ping

    Example:
        ws://localhost:8000/api/ir/approvals/ws?tenant_id=tenant_123
    """
    manager = get_connection_manager()
    await manager.connect(websocket, tenant_id)

    try:
        while True:
            # Keep connection alive, receive any client messages
            data = await websocket.receive_text()
            logger.debug(f"[HITL WebSocket] Received: {data}")

            # Echo heartbeat
            if data == "ping":
                await websocket.send_json({"type": "heartbeat", "message": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(websocket, tenant_id)
