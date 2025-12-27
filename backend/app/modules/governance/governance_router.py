"""
Governance API Router

Sprint 16: HITL Approvals UI & Governance Cockpit
REST API endpoints for approval workflows and audit trail.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from .governance_models import (
    ApprovalDetail,
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    ApprovalSummary,
    ApprovalType,
    ApproveRequest,
    AuditEntry,
    AuditExport,
    GovernanceStats,
    RejectRequest,
    RiskTier,
)
from .governance_service import GovernanceService


router = APIRouter(prefix="/api/governance", tags=["governance"])


# =========================================================================
# Request/Response Models
# =========================================================================

class HealthResponse(BaseModel):
    """Health check response."""
    name: str
    version: str
    status: str
    pending_approvals: int
    total_approvals: int

    model_config = {"extra": "forbid"}


# =========================================================================
# Dependency Injection
# =========================================================================

def get_governance_service() -> GovernanceService:
    """Get governance service instance."""
    return GovernanceService()


# =========================================================================
# APPROVAL MANAGEMENT
# =========================================================================

@router.post(
    "/approvals",
    response_model=ApprovalResponse,
    summary="Create approval request",
    description="Request approval for critical action (IR, course publish, etc.)",
    status_code=status.HTTP_201_CREATED,
)
async def create_approval(
    request: ApprovalRequest,
    service: GovernanceService = None,
) -> ApprovalResponse:
    """
    Create new approval request.

    Creates a human-in-the-loop approval request for critical actions.

    Args:
        request: Approval request data

    Returns:
        ApprovalResponse with approval_id and optional token

    **Note:** Token is only returned once if required. Store it securely!
    """
    if service is None:
        service = get_governance_service()

    try:
        # Determine if token is required based on risk tier
        require_token = request.context.risk_tier in [
            RiskTier.HIGH,
            RiskTier.CRITICAL
        ]

        approval, token = await service.request_approval(
            approval_type=request.approval_type,
            context=request.context,
            expires_in_hours=request.expires_in_hours,
            require_token=require_token,
        )

        return ApprovalResponse(
            approval_id=approval.approval_id,
            status=approval.status,
            expires_at=approval.expires_at,
            token=token,  # Only returned if require_token=True
            message=f"Approval requested successfully (expires in {request.expires_in_hours}h)"
        )
    except Exception as e:
        logger.error(f"Error creating approval: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create approval request",
        )


@router.get(
    "/approvals",
    response_model=List[ApprovalSummary],
    summary="List approvals",
    description="Get list of approval requests with optional filters.",
)
async def list_approvals(
    status_filter: Optional[ApprovalStatus] = Query(None, alias="status", description="Filter by status"),
    approval_type: Optional[ApprovalType] = Query(None, description="Filter by type"),
    requested_by: Optional[str] = Query(None, description="Filter by requester"),
    risk_tier: Optional[RiskTier] = Query(None, description="Filter by risk tier"),
    include_expired: bool = Query(False, description="Include expired approvals"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    service: GovernanceService = None,
) -> List[ApprovalSummary]:
    """
    List approval requests with optional filters.

    Returns list of approval summaries sorted by request date (newest first).

    Query Parameters:
    - **status**: Filter by status (pending, approved, rejected, expired)
    - **approval_type**: Filter by type (ir_escalation, course_publish, etc.)
    - **requested_by**: Filter by requester actor_id
    - **risk_tier**: Filter by risk tier (low, medium, high, critical)
    - **include_expired**: Include expired approvals (default: false)
    - **limit**: Maximum results (1-500, default: 100)
    """
    if service is None:
        service = get_governance_service()

    try:
        approvals = await service.list_approvals(
            status=status_filter,
            approval_type=approval_type,
            requested_by=requested_by,
            risk_tier=risk_tier,
            include_expired=include_expired,
            limit=limit,
        )
        return approvals
    except Exception as e:
        logger.error(f"Error listing approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list approvals",
        )


@router.get(
    "/approvals/{approval_id}",
    response_model=ApprovalDetail,
    summary="Get approval details",
    description="Get detailed information about specific approval request.",
)
async def get_approval_detail(
    approval_id: str,
    service: GovernanceService = None,
) -> ApprovalDetail:
    """
    Get detailed approval information.

    Returns full approval context including diff, risk tier, timestamps, etc.

    Args:
        approval_id: Approval ID

    Returns:
        ApprovalDetail with complete information

    Raises:
        404: Approval not found
    """
    if service is None:
        service = get_governance_service()

    try:
        detail = await service.get_approval_detail(approval_id)

        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Approval {approval_id} not found",
            )

        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching approval detail for {approval_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch approval details",
        )


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalDetail,
    summary="Approve request",
    description="Approve an approval request (with optional token).",
)
async def approve_approval(
    approval_id: str,
    request: ApproveRequest,
    service: GovernanceService = None,
) -> ApprovalDetail:
    """
    Approve an approval request.

    Approves the specified approval request. If the request requires a token
    (high/critical risk), the token must be provided.

    Args:
        approval_id: Approval ID
        request: Approve request with actor_id and optional token

    Returns:
        Updated ApprovalDetail

    Raises:
        400: Approval not pending, expired, or invalid token
        404: Approval not found
    """
    if service is None:
        service = get_governance_service()

    try:
        approval = await service.approve_approval(
            approval_id=approval_id,
            actor_id=request.actor_id,
            token=request.token,
            notes=request.notes,
        )

        # Return updated detail
        detail = await service.get_approval_detail(approval_id)
        return detail
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error approving {approval_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve request",
        )


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalDetail,
    summary="Reject request",
    description="Reject an approval request (reason required).",
)
async def reject_approval(
    approval_id: str,
    request: RejectRequest,
    service: GovernanceService = None,
) -> ApprovalDetail:
    """
    Reject an approval request.

    Rejects the specified approval request. Rejection reason is mandatory
    and must be at least 10 characters.

    Args:
        approval_id: Approval ID
        request: Reject request with actor_id and reason

    Returns:
        Updated ApprovalDetail

    Raises:
        400: Approval not pending, expired, or invalid reason
        404: Approval not found
    """
    if service is None:
        service = get_governance_service()

    try:
        approval = await service.reject_approval(
            approval_id=approval_id,
            actor_id=request.actor_id,
            reason=request.reason,
            notes=request.notes,
        )

        # Return updated detail
        detail = await service.get_approval_detail(approval_id)
        return detail
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error rejecting {approval_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject request",
        )


# =========================================================================
# AUDIT TRAIL
# =========================================================================

@router.get(
    "/audit",
    response_model=List[AuditEntry],
    summary="Get audit trail",
    description="Get audit trail entries (optionally filtered by approval_id).",
)
async def get_audit_trail(
    approval_id: Optional[str] = Query(None, description="Filter by approval ID"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="Maximum entries"),
    service: GovernanceService = None,
) -> List[AuditEntry]:
    """
    Get audit trail entries.

    Returns chronological audit trail for governance actions.

    Query Parameters:
    - **approval_id**: Filter by specific approval (optional)
    - **limit**: Maximum entries to return (1-1000, default: 100)

    Returns:
        List of audit entries (newest first)
    """
    if service is None:
        service = get_governance_service()

    try:
        if approval_id:
            # Get trail for specific approval
            entries = await service.get_audit_trail(approval_id)
        else:
            # Export all entries
            export = await service.export_audit(
                actor_id="system",  # Could be parameterized
                limit=limit,
            )
            entries = export.entries

        return entries
    except Exception as e:
        logger.error(f"Error fetching audit trail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch audit trail",
        )


@router.get(
    "/audit/export",
    response_model=AuditExport,
    summary="Export audit trail",
    description="Export complete audit trail (auditor-only).",
)
async def export_audit_trail(
    actor_id: str = Query(..., description="Actor performing export"),
    approval_id: Optional[str] = Query(None, description="Filter by approval ID"),
    limit: Optional[int] = Query(None, description="Maximum entries"),
    service: GovernanceService = None,
) -> AuditExport:
    """
    Export audit trail (auditor mode).

    Exports audit trail with metadata about export action.

    Query Parameters:
    - **actor_id**: Actor performing export (required for auditing)
    - **approval_id**: Filter by specific approval (optional)
    - **limit**: Maximum entries (optional)

    Returns:
        AuditExport with entries and export metadata
    """
    if service is None:
        service = get_governance_service()

    try:
        export = await service.export_audit(
            actor_id=actor_id,
            approval_id=approval_id,
            limit=limit,
        )
        return export
    except Exception as e:
        logger.error(f"Error exporting audit trail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit trail",
        )


# =========================================================================
# SPECIALIZED ENDPOINTS (Convenience)
# =========================================================================

@router.get(
    "/approvals/pending",
    response_model=List[ApprovalSummary],
    summary="Get pending approvals",
    description="Convenience endpoint for pending approvals only.",
)
async def get_pending_approvals(
    service: GovernanceService = None,
) -> List[ApprovalSummary]:
    """Get all pending approval requests."""
    if service is None:
        service = get_governance_service()

    try:
        return await service.get_pending_approvals()
    except Exception as e:
        logger.error(f"Error fetching pending approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch pending approvals",
        )


@router.get(
    "/approvals/approved",
    response_model=List[ApprovalSummary],
    summary="Get approved approvals",
    description="Convenience endpoint for approved approvals only.",
)
async def get_approved_approvals(
    service: GovernanceService = None,
) -> List[ApprovalSummary]:
    """Get all approved approval requests."""
    if service is None:
        service = get_governance_service()

    try:
        return await service.get_approved_approvals()
    except Exception as e:
        logger.error(f"Error fetching approved approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch approved approvals",
        )


@router.get(
    "/approvals/rejected",
    response_model=List[ApprovalSummary],
    summary="Get rejected approvals",
    description="Convenience endpoint for rejected approvals only.",
)
async def get_rejected_approvals(
    service: GovernanceService = None,
) -> List[ApprovalSummary]:
    """Get all rejected approval requests."""
    if service is None:
        service = get_governance_service()

    try:
        return await service.get_rejected_approvals()
    except Exception as e:
        logger.error(f"Error fetching rejected approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch rejected approvals",
        )


@router.get(
    "/approvals/expired",
    response_model=List[ApprovalSummary],
    summary="Get expired approvals",
    description="Convenience endpoint for expired approvals only.",
)
async def get_expired_approvals(
    service: GovernanceService = None,
) -> List[ApprovalSummary]:
    """Get all expired approval requests."""
    if service is None:
        service = get_governance_service()

    try:
        return await service.get_expired_approvals()
    except Exception as e:
        logger.error(f"Error fetching expired approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch expired approvals",
        )


# =========================================================================
# STATISTICS & HEALTH
# =========================================================================

@router.get(
    "/stats",
    response_model=GovernanceStats,
    summary="Get governance statistics",
    description="Get system-wide governance statistics.",
)
async def get_governance_stats(
    service: GovernanceService = None,
) -> GovernanceStats:
    """
    Get governance system statistics.

    Returns:
        GovernanceStats with counts by status, type, risk tier, etc.
    """
    if service is None:
        service = get_governance_service()

    try:
        return await service.get_stats()
    except Exception as e:
        logger.error(f"Error fetching governance stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch governance statistics",
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Governance system health",
    description="Health check for governance system.",
)
async def governance_health(
    service: GovernanceService = None,
) -> HealthResponse:
    """
    Health check for governance system.

    Returns:
        System health status with pending/total counts
    """
    if service is None:
        service = get_governance_service()

    try:
        stats = await service.get_stats()

        return HealthResponse(
            name="Governance System",
            version="1.0.0",
            status="healthy",
            pending_approvals=stats.pending_approvals,
            total_approvals=stats.total_approvals,
        )
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return HealthResponse(
            name="Governance System",
            version="1.0.0",
            status="degraded",
            pending_approvals=0,
            total_approvals=0,
        )


# =========================================================================
# MAINTENANCE (Admin Only)
# =========================================================================

@router.post(
    "/maintenance/expire-old",
    response_model=Dict[str, int],
    summary="Expire old approvals",
    description="Maintenance endpoint to expire all old pending approvals. Admin only.",
)
async def expire_old_approvals(
    service: GovernanceService = None,
) -> Dict[str, int]:
    """
    Expire all old pending approvals.

    **Admin only** - Should be called periodically (e.g., via cron).

    Returns:
        Number of approvals expired
    """
    if service is None:
        service = get_governance_service()

    try:
        expired_count = await service.expire_old_approvals()

        return {"expired_count": expired_count}
    except Exception as e:
        logger.error(f"Error expiring old approvals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to expire old approvals",
        )
