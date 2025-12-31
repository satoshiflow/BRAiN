"""
Human-in-the-Loop (HITL) Approval API Endpoints

Provides REST API for managing human oversight approvals for HIGH/CRITICAL risk actions.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, timedelta
from enum import Enum


router = APIRouter(prefix="/api/hitl", tags=["human-oversight"])


# ============================================================================
# Schemas
# ============================================================================


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"


class HITLApprovalRequest(BaseModel):
    """Request to approve or deny a HITL token."""
    token: str = Field(..., description="Human oversight token (HITL-xxxxx)")
    approved: bool = Field(..., description="True to approve, False to deny")
    approved_by: str = Field(..., description="Name/ID of approver")
    reason: Optional[str] = Field(None, description="Reason for decision")


class HITLApprovalDetails(BaseModel):
    """Full details of a HITL approval request."""
    id: int
    token: str
    audit_id: str
    status: ApprovalStatus

    # Original request
    requesting_agent: str
    action: str
    risk_level: str
    context: dict

    # Approval info
    approved_by: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    approval_reason: Optional[str] = None

    # Metadata
    created_at: datetime
    expires_at: Optional[datetime] = None

    # Computed
    is_expired: bool = False
    time_remaining: Optional[int] = None  # seconds


class HITLQueueResponse(BaseModel):
    """List of pending HITL approvals."""
    total: int
    pending: List[HITLApprovalDetails]
    expired: int


class HITLHistoryResponse(BaseModel):
    """Historical HITL approvals."""
    total: int
    approvals: List[HITLApprovalDetails]


class HITLStatsResponse(BaseModel):
    """HITL statistics."""
    total_requests: int
    pending: int
    approved: int
    denied: int
    expired: int
    avg_approval_time_seconds: Optional[float] = None


# ============================================================================
# In-Memory Storage (Replace with Database in Production)
# ============================================================================

# Mock storage - in production, use the database tables
HITL_APPROVALS = {}


def get_hitl_storage():
    """Dependency for HITL storage."""
    return HITL_APPROVALS


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/queue", response_model=HITLQueueResponse)
async def get_hitl_queue(
    storage: dict = Depends(get_hitl_storage)
):
    """
    Get all pending HITL approval requests.

    Returns requests awaiting human oversight, excluding expired ones.
    """
    now = datetime.utcnow()

    pending = []
    expired_count = 0

    for token, approval in storage.items():
        if approval["status"] != "pending":
            continue

        # Check if expired
        if approval.get("expires_at") and approval["expires_at"] < now:
            approval["status"] = "expired"
            approval["is_expired"] = True
            expired_count += 1
            continue

        # Calculate time remaining
        time_remaining = None
        if approval.get("expires_at"):
            time_remaining = int((approval["expires_at"] - now).total_seconds())

        approval["time_remaining"] = time_remaining
        approval["is_expired"] = False

        pending.append(approval)

    # Sort by creation time (oldest first)
    pending.sort(key=lambda x: x["created_at"])

    return {
        "total": len(pending),
        "pending": pending,
        "expired": expired_count
    }


@router.post("/approve", response_model=HITLApprovalDetails)
async def approve_hitl_request(
    request: HITLApprovalRequest,
    storage: dict = Depends(get_hitl_storage)
):
    """
    Approve or deny a HITL request.

    Updates the approval status and records who made the decision.
    """
    token = request.token

    # Find approval request
    if token not in storage:
        raise HTTPException(
            status_code=404,
            detail=f"HITL token '{token}' not found"
        )

    approval = storage[token]

    # Check if already processed
    if approval["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"HITL request already processed (status: {approval['status']})"
        )

    # Check if expired
    now = datetime.utcnow()
    if approval.get("expires_at") and approval["expires_at"] < now:
        approval["status"] = "expired"
        raise HTTPException(
            status_code=400,
            detail="HITL request has expired"
        )

    # Update approval
    approval["status"] = "approved" if request.approved else "denied"
    approval["approved_by"] = request.approved_by
    approval["approval_timestamp"] = now
    approval["approval_reason"] = request.reason

    # TODO: Trigger action execution if approved
    # This would notify the original agent that approval was granted

    return approval


@router.get("/token/{token}", response_model=HITLApprovalDetails)
async def get_hitl_by_token(
    token: str,
    storage: dict = Depends(get_hitl_storage)
):
    """
    Get details of a specific HITL request by token.
    """
    if token not in storage:
        raise HTTPException(
            status_code=404,
            detail=f"HITL token '{token}' not found"
        )

    approval = storage[token]

    # Check if expired
    now = datetime.utcnow()
    if approval.get("expires_at"):
        if approval["expires_at"] < now:
            approval["is_expired"] = True
            approval["time_remaining"] = 0
        else:
            approval["is_expired"] = False
            approval["time_remaining"] = int((approval["expires_at"] - now).total_seconds())

    return approval


@router.get("/history", response_model=HITLHistoryResponse)
async def get_hitl_history(
    limit: int = 50,
    status: Optional[ApprovalStatus] = None,
    storage: dict = Depends(get_hitl_storage)
):
    """
    Get historical HITL approvals.

    Query parameters:
    - limit: Maximum number of results (default: 50)
    - status: Filter by status (approved/denied/expired)
    """
    approvals = list(storage.values())

    # Filter by status if provided
    if status:
        approvals = [a for a in approvals if a["status"] == status]

    # Sort by approval timestamp (most recent first)
    approvals.sort(
        key=lambda x: x.get("approval_timestamp") or x["created_at"],
        reverse=True
    )

    # Limit results
    approvals = approvals[:limit]

    return {
        "total": len(approvals),
        "approvals": approvals
    }


@router.get("/stats", response_model=HITLStatsResponse)
async def get_hitl_stats(
    storage: dict = Depends(get_hitl_storage)
):
    """
    Get HITL approval statistics.
    """
    now = datetime.utcnow()

    total = len(storage)
    pending = 0
    approved = 0
    denied = 0
    expired = 0

    approval_times = []

    for approval in storage.values():
        status = approval["status"]

        # Update expired status
        if status == "pending" and approval.get("expires_at") and approval["expires_at"] < now:
            status = "expired"
            approval["status"] = "expired"

        if status == "pending":
            pending += 1
        elif status == "approved":
            approved += 1
            # Calculate approval time
            if approval.get("approval_timestamp"):
                delta = approval["approval_timestamp"] - approval["created_at"]
                approval_times.append(delta.total_seconds())
        elif status == "denied":
            denied += 1
        elif status == "expired":
            expired += 1

    # Calculate average approval time
    avg_approval_time = None
    if approval_times:
        avg_approval_time = sum(approval_times) / len(approval_times)

    return {
        "total_requests": total,
        "pending": pending,
        "approved": approved,
        "denied": denied,
        "expired": expired,
        "avg_approval_time_seconds": avg_approval_time
    }


@router.delete("/token/{token}")
async def delete_hitl_request(
    token: str,
    storage: dict = Depends(get_hitl_storage)
):
    """
    Delete a HITL request (admin only).

    This should be restricted to administrators in production.
    """
    if token not in storage:
        raise HTTPException(
            status_code=404,
            detail=f"HITL token '{token}' not found"
        )

    del storage[token]

    return {"message": f"HITL request '{token}' deleted"}


# ============================================================================
# Helper Functions
# ============================================================================


def create_hitl_approval(
    token: str,
    audit_id: str,
    requesting_agent: str,
    action: str,
    risk_level: str,
    context: dict,
    expires_in_seconds: int = 3600
) -> dict:
    """
    Create a new HITL approval request.

    This is called by the SupervisorAgent when human oversight is required.
    """
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=expires_in_seconds)

    approval = {
        "id": len(HITL_APPROVALS) + 1,
        "token": token,
        "audit_id": audit_id,
        "status": "pending",

        # Original request
        "requesting_agent": requesting_agent,
        "action": action,
        "risk_level": risk_level,
        "context": context,

        # Approval info
        "approved_by": None,
        "approval_timestamp": None,
        "approval_reason": None,

        # Metadata
        "created_at": now,
        "expires_at": expires_at,

        # Computed
        "is_expired": False,
        "time_remaining": expires_in_seconds
    }

    HITL_APPROVALS[token] = approval

    return approval


# ============================================================================
# Auto-Include Router
# ============================================================================

# This router will be auto-discovered by backend/main.py
