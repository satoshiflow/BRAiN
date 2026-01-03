"""
Governance API Endpoints - Compatibility Layer for HITL Approvals

Maps frontend governance endpoints to backend HITL approval system.
Provides a REST API that matches the frontend's expected interface.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

# Import HITL storage and helper from hitl.py
from app.api.routes.hitl import (
    get_hitl_storage,
    ApprovalStatus,
    create_hitl_approval,
    HITL_APPROVALS
)


router = APIRouter(prefix="/api/governance", tags=["governance"])


# ============================================================================
# Schemas
# ============================================================================


class ApprovalSummary(BaseModel):
    """Summary of approval request for governance dashboard."""
    approval_id: str
    approval_type: str
    status: str
    risk_tier: str
    requested_by: str
    requested_at: float  # Unix timestamp
    expires_at: float  # Unix timestamp
    time_until_expiry: int  # Seconds
    action_description: str


class ApproveRequest(BaseModel):
    """Request to approve an action."""
    actor_id: str = Field(..., description="ID of user performing approval")
    notes: Optional[str] = Field(None, description="Optional approval notes")


class RejectRequest(BaseModel):
    """Request to reject an action."""
    actor_id: str = Field(..., description="ID of user performing rejection")
    reason: str = Field(..., description="Rejection reason", min_length=10)


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/approvals/{status}", response_model=List[ApprovalSummary])
async def get_approvals_by_status(
    status: str,
    storage: dict = Depends(get_hitl_storage)
):
    """
    Get approval requests filtered by status.

    Status can be: pending, approved, rejected, expired
    """
    now = datetime.utcnow()
    results = []

    for token, approval in storage.items():
        approval_status = approval.get("status", "pending")

        # Update expired status
        if approval_status == "pending" and approval.get("expires_at"):
            if approval["expires_at"] < now:
                approval_status = "expired"
                approval["status"] = "expired"

        # Map denied to rejected for frontend
        if approval_status == "denied":
            approval_status = "rejected"

        # Filter by requested status
        if status != approval_status:
            continue

        # Calculate time until expiry
        time_until_expiry = 0
        if approval.get("expires_at"):
            delta = approval["expires_at"] - now
            time_until_expiry = max(0, int(delta.total_seconds()))

        # Build summary
        summary = ApprovalSummary(
            approval_id=token,
            approval_type=approval.get("action", "unknown"),
            status=approval_status,
            risk_tier=approval.get("risk_level", "unknown"),
            requested_by=approval.get("requesting_agent", "unknown"),
            requested_at=approval.get("created_at", now).timestamp(),
            expires_at=approval.get("expires_at", now).timestamp(),
            time_until_expiry=time_until_expiry,
            action_description=_build_action_description(approval)
        )

        results.append(summary)

    # Sort by creation time (newest first for pending, oldest for history)
    if status == "pending":
        results.sort(key=lambda x: x.requested_at)
    else:
        results.sort(key=lambda x: x.requested_at, reverse=True)

    return results


@router.post("/approvals/{approval_id}/approve")
async def approve_action(
    approval_id: str,
    request: ApproveRequest,
    storage: dict = Depends(get_hitl_storage)
):
    """
    Approve a pending action.
    """
    # Find approval
    if approval_id not in storage:
        raise HTTPException(
            status_code=404,
            detail=f"Approval {approval_id} not found"
        )

    approval = storage[approval_id]

    # Check if already processed
    if approval["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval already processed (status: {approval['status']})"
        )

    # Check if expired
    now = datetime.utcnow()
    if approval.get("expires_at") and approval["expires_at"] < now:
        approval["status"] = "expired"
        raise HTTPException(
            status_code=400,
            detail="Approval request has expired"
        )

    # Update approval
    approval["status"] = "approved"
    approval["approved_by"] = request.actor_id
    approval["approval_timestamp"] = now
    approval["approval_reason"] = request.notes or "Approved via governance dashboard"

    return {
        "success": True,
        "message": f"Action {approval_id} approved by {request.actor_id}",
        "approval_id": approval_id
    }


@router.post("/approvals/{approval_id}/reject")
async def reject_action(
    approval_id: str,
    request: RejectRequest,
    storage: dict = Depends(get_hitl_storage)
):
    """
    Reject a pending action.
    """
    # Find approval
    if approval_id not in storage:
        raise HTTPException(
            status_code=404,
            detail=f"Approval {approval_id} not found"
        )

    approval = storage[approval_id]

    # Check if already processed
    if approval["status"] != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Approval already processed (status: {approval['status']})"
        )

    # Check if expired
    now = datetime.utcnow()
    if approval.get("expires_at") and approval["expires_at"] < now:
        approval["status"] = "expired"
        raise HTTPException(
            status_code=400,
            detail="Approval request has expired"
        )

    # Update approval
    approval["status"] = "denied"  # Backend uses "denied"
    approval["approved_by"] = request.actor_id
    approval["approval_timestamp"] = now
    approval["approval_reason"] = request.reason

    return {
        "success": True,
        "message": f"Action {approval_id} rejected by {request.actor_id}",
        "approval_id": approval_id,
        "reason": request.reason
    }


@router.get("/approvals/{approval_id}")
async def get_approval_details(
    approval_id: str,
    storage: dict = Depends(get_hitl_storage)
):
    """
    Get detailed information about a specific approval.
    """
    if approval_id not in storage:
        raise HTTPException(
            status_code=404,
            detail=f"Approval {approval_id} not found"
        )

    approval = storage[approval_id]

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


# ============================================================================
# Helper Functions
# ============================================================================


def _build_action_description(approval: dict) -> str:
    """
    Build a human-readable action description from approval data.
    """
    action = approval.get("action", "unknown_action")
    agent = approval.get("requesting_agent", "unknown_agent")
    context = approval.get("context", {})

    # Build description based on action type
    if action == "deploy_application":
        app_name = context.get("app_name", "application")
        environment = context.get("environment", "unknown")
        version = context.get("version", "unknown")
        return f"{agent} wants to deploy {app_name} v{version} to {environment}"

    elif action == "generate_odoo_module":
        module_name = context.get("name", "module")
        return f"{agent} wants to generate Odoo module '{module_name}' with personal data processing"

    elif action == "delete_data":
        data_type = context.get("data_type", "data")
        return f"{agent} wants to delete {data_type}"

    elif action == "modify_configuration":
        config_type = context.get("config_type", "configuration")
        return f"{agent} wants to modify {config_type}"

    else:
        return f"{agent} requests approval for {action.replace('_', ' ')}"


# ============================================================================
# Info Endpoint
# ============================================================================


@router.get("/info")
async def governance_info():
    """
    Get governance system information.
    """
    return {
        "name": "Governance & HITL System",
        "version": "1.0.0",
        "description": "Human-in-the-loop approval system for HIGH/CRITICAL risk actions",
        "endpoints": {
            "approvals_by_status": "/api/governance/approvals/{status}",
            "approve": "/api/governance/approvals/{id}/approve",
            "reject": "/api/governance/approvals/{id}/reject",
            "details": "/api/governance/approvals/{id}"
        },
        "compliance": {
            "DSGVO": "Art. 22 - Right to human oversight for automated decisions",
            "EU_AI_Act": "Art. 16 - Human oversight requirements for high-risk AI systems"
        }
    }
