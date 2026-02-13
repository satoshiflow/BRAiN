"""
IR Governance API Router - Sprint 9 (P0)

REST API for IR validation, approvals, and diff-audit.

Endpoints:
- POST /api/ir/validate - Validate IR
- POST /api/ir/approvals - Create approval request
- POST /api/ir/approvals/consume - Consume approval
- GET /api/ir/approvals/{approval_id}/status - Get approval status
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from loguru import logger

from app.modules.ir_governance.schemas import (
    IR,
    IRValidationResult,
    ApprovalRequest,
    ApprovalConsumeRequest,
    ApprovalConsumeResult,
)
from app.modules.ir_governance.validator import get_validator
from app.modules.ir_governance.approvals import get_approvals_service


router = APIRouter(prefix="/api/ir", tags=["ir-governance"])


@router.get("/info")
async def get_ir_info():
    """
    Get IR Governance system information.

    Returns basic information about the IR governance kernel.
    """
    return {
        "name": "BRAiN IR Governance Kernel",
        "version": "1.0.0",
        "sprint": "Sprint 9 (P0)",
        "description": "Deterministic policy enforcement for autonomous business pipelines",
        "features": [
            "Canonical IR (Single Source of Truth)",
            "Deterministic validation (LLM-free)",
            "Risk tier calculation (Tier 0-3)",
            "HITL approvals (single-use, TTL)",
            "Diff-audit gate (IR ↔ DAG integrity)",
            "Fail-closed by default",
        ],
        "endpoints": [
            "POST /api/ir/validate - Validate IR",
            "POST /api/ir/approvals - Create approval request",
            "POST /api/ir/approvals/consume - Consume approval",
            "GET /api/ir/approvals/{approval_id}/status - Get approval status",
        ],
    }


@router.post("/validate")
async def validate_ir(ir: IR) -> IRValidationResult:
    """
    Validate IR against policy rules.

    **Validation includes:**
    - Schema validation (Pydantic)
    - Action/provider vocabulary check (fail-closed)
    - Idempotency key presence
    - Risk tier calculation (action, scope, impact)
    - Auto-escalation rules
    - Budget validation

    **Returns:**
    - status: PASS | ESCALATE | REJECT
    - violations: List of policy violations
    - risk_tier: Effective risk tier (0-3)
    - requires_approval: Whether HITL approval required
    - ir_hash: Canonical IR hash

    **Example Request:**
    ```json
    {
      "tenant_id": "tenant_demo",
      "intent_summary": "Deploy staging website",
      "steps": [
        {
          "action": "deploy.website",
          "provider": "deploy.provider_v1",
          "resource": "site:staging",
          "params": {"repo": "git+https://example/repo.git"},
          "idempotency_key": "deploy-staging-2025-01-01"
        }
      ]
    }
    ```

    **Audit events:**
    - ir.validated_pass
    - ir.validated_escalate
    - ir.validated_reject
    """
    try:
        validator = get_validator()
        result = validator.validate_ir(ir)
        return result

    except Exception as e:
        logger.error(f"[IR] Validation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"IR validation failed: {str(e)}"
        )


@router.post("/approvals")
async def create_approval(
    tenant_id: str,
    ir_hash: str,
    ttl_seconds: int = 3600,
    created_by: str | None = None,
) -> Dict[str, Any]:
    """
    Create HITL approval request.

    **Security:**
    - Token is single-use
    - Token has TTL (default: 1 hour)
    - Token hash stored (never raw token in logs/storage)

    **Args:**
    - tenant_id: Tenant ID
    - ir_hash: IR hash to approve
    - ttl_seconds: Time-to-live (default: 3600s = 1 hour)
    - created_by: User/role creating approval

    **Returns:**
    - approval_id: Approval ID
    - token: Approval token (SINGLE-USE, save it!)
    - expires_at: Expiration timestamp

    **Example Request:**
    ```bash
    POST /api/ir/approvals?tenant_id=tenant_demo&ir_hash=abc123...&ttl_seconds=3600
    ```

    **Audit events:**
    - ir.approval_created
    """
    try:
        approvals_service = get_approvals_service()
        approval, raw_token = approvals_service.create_approval(
            tenant_id=tenant_id,
            ir_hash=ir_hash,
            ttl_seconds=ttl_seconds,
            created_by=created_by,
        )

        return {
            "approval_id": approval.approval_id,
            "token": raw_token,  # ONLY TIME raw token is exposed
            "expires_at": approval.expires_at.isoformat(),
            "tenant_id": approval.tenant_id,
            "ir_hash": approval.ir_hash[:16] + "...",  # Truncated for display
            "message": "Approval request created. Save the token - it will not be shown again.",
        }

    except Exception as e:
        logger.error(f"[IR] Create approval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Create approval failed: {str(e)}"
        )


@router.post("/approvals/consume")
async def consume_approval(
    request: ApprovalConsumeRequest,
    consumed_by: str | None = None,
) -> ApprovalConsumeResult:
    """
    Consume approval token.

    **Validates:**
    - Token exists
    - Not expired
    - Not already consumed
    - Matches tenant_id
    - Matches ir_hash

    **Args:**
    - request: Consume request (tenant_id, ir_hash, token)
    - consumed_by: User/role consuming approval

    **Returns:**
    - success: True if consumed successfully
    - status: Approval status
    - message: Result message
    - approval_id: Approval ID (if successful)

    **Example Request:**
    ```json
    {
      "tenant_id": "tenant_demo",
      "ir_hash": "abc123...",
      "token": "raw_token_from_create"
    }
    ```

    **Audit events:**
    - ir.approval_consumed (success)
    - ir.approval_expired (if expired)
    - ir.approval_invalid (if invalid)
    """
    try:
        approvals_service = get_approvals_service()
        result = approvals_service.consume_approval(request, consumed_by=consumed_by)
        return result

    except Exception as e:
        logger.error(f"[IR] Consume approval failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Consume approval failed: {str(e)}"
        )


@router.get("/approvals/{approval_id}/status")
async def get_approval_status(approval_id: str) -> Dict[str, Any]:
    """
    Get approval status by ID.

    **Args:**
    - approval_id: Approval ID

    **Returns:**
    - approval_id: Approval ID
    - status: Approval status (pending, consumed, expired, invalid)
    - tenant_id: Tenant ID
    - ir_hash: IR hash (truncated)
    - created_at: Creation timestamp
    - expires_at: Expiration timestamp
    - consumed_at: Consumption timestamp (if consumed)

    **Example:**
    ```bash
    GET /api/ir/approvals/approval_123/status
    ```
    """
    try:
        approvals_service = get_approvals_service()
        approval = approvals_service.get_approval_status(approval_id)

        if not approval:
            raise HTTPException(
                status_code=404,
                detail=f"Approval not found: {approval_id}"
            )

        return {
            "approval_id": approval.approval_id,
            "status": approval.status.value,
            "tenant_id": approval.tenant_id,
            "ir_hash": approval.ir_hash[:16] + "...",
            "created_at": approval.created_at.isoformat(),
            "expires_at": approval.expires_at.isoformat(),
            "consumed_at": approval.consumed_at.isoformat() if approval.consumed_at else None,
            "created_by": approval.created_by,
            "consumed_by": approval.consumed_by,
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions

    except Exception as e:
        logger.error(f"[IR] Get approval status failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Get approval status failed: {str(e)}"
        )
