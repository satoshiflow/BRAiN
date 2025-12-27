"""
Governance Data Models

Sprint 16: HITL Approvals UI & Governance Cockpit
Models for human-in-the-loop approval workflows.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ApprovalType(str, Enum):
    """Types of approvals."""
    IR_ESCALATION = "ir_escalation"
    COURSE_PUBLISH = "course_publish"
    CERTIFICATE_ISSUANCE = "certificate_issuance"
    POLICY_OVERRIDE = "policy_override"


class ApprovalStatus(str, Enum):
    """Approval workflow states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class RiskTier(str, Enum):
    """Risk tiers for approvals."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalContext(BaseModel):
    """
    Context information for approval request.

    Contains all relevant information for human reviewer to make informed decision.
    """
    # What is being approved
    action_type: ApprovalType
    action_description: str
    risk_tier: RiskTier

    # Requester information
    requested_by: str = Field(..., description="Actor ID who requested approval")
    requested_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    # Diff / Changes (if applicable)
    diff: Optional[Dict[str, Any]] = Field(None, description="Changes being approved")
    before: Optional[Dict[str, Any]] = Field(None, description="State before change")
    after: Optional[Dict[str, Any]] = Field(None, description="State after change")

    # Additional context
    reason: Optional[str] = Field(None, description="Reason for request")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = {"extra": "forbid"}


class Approval(BaseModel):
    """
    Approval record.

    Represents a human-in-the-loop approval request with full context and lifecycle tracking.
    """
    # Identity
    approval_id: str = Field(default_factory=lambda: f"approval_{uuid4().hex[:16]}")

    # Type & Status
    approval_type: ApprovalType
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)

    # Context
    context: ApprovalContext

    # Decision
    approved_by: Optional[str] = Field(None, description="Actor ID who approved/rejected")
    approved_at: Optional[float] = Field(None, description="Approval/rejection timestamp")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")

    # Expiry
    expires_at: float = Field(
        default_factory=lambda: (datetime.utcnow() + timedelta(hours=24)).timestamp(),
        description="Expiry timestamp (24h default)"
    )

    # Token (single-use)
    token_hash: Optional[str] = Field(None, description="SHA-256 hash of single-use token")
    token_used: bool = Field(default=False, description="Whether token was used")

    # Timestamps
    created_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    model_config = {"extra": "forbid"}

    def is_pending(self) -> bool:
        """Check if approval is pending."""
        return self.status == ApprovalStatus.PENDING

    def is_approved(self) -> bool:
        """Check if approval was approved."""
        return self.status == ApprovalStatus.APPROVED

    def is_rejected(self) -> bool:
        """Check if approval was rejected."""
        return self.status == ApprovalStatus.REJECTED

    def is_expired(self) -> bool:
        """Check if approval has expired."""
        now = datetime.utcnow().timestamp()
        return self.status == ApprovalStatus.PENDING and now > self.expires_at

    def time_until_expiry(self) -> float:
        """Get seconds until expiry (negative if already expired)."""
        now = datetime.utcnow().timestamp()
        return self.expires_at - now


class ApprovalAction(str, Enum):
    """Actions that can be taken on approvals."""
    APPROVE = "approve"
    REJECT = "reject"
    EXPIRE = "expire"
    VIEW = "view"
    EXPORT = "export"


class AuditEntry(BaseModel):
    """
    Audit trail entry for governance actions.

    Records all actions taken on approvals for full accountability.
    """
    # Identity
    audit_id: str = Field(default_factory=lambda: f"audit_{uuid4().hex[:16]}")

    # What happened
    approval_id: str
    action: ApprovalAction
    action_description: str

    # Who did it
    actor_id: str
    actor_role: Optional[str] = Field(None, description="Role of actor (admin, auditor, etc.)")

    # When
    timestamp: float = Field(default_factory=lambda: datetime.utcnow().timestamp())

    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


# Request/Response Models for API

class ApprovalRequest(BaseModel):
    """Request to create approval."""
    approval_type: ApprovalType
    context: ApprovalContext
    expires_in_hours: int = Field(default=24, ge=1, le=168, description="Expiry time (1-168 hours)")

    model_config = {"extra": "forbid"}


class ApprovalResponse(BaseModel):
    """Response after creating approval."""
    approval_id: str
    status: ApprovalStatus
    expires_at: float
    token: Optional[str] = Field(None, description="Single-use token (only returned once)")
    message: str

    model_config = {"extra": "forbid"}


class ApproveRequest(BaseModel):
    """Request to approve."""
    actor_id: str
    token: Optional[str] = Field(None, description="Single-use token (if required)")
    notes: Optional[str] = Field(None, description="Approval notes")

    model_config = {"extra": "forbid"}


class RejectRequest(BaseModel):
    """Request to reject (reason required)."""
    actor_id: str
    reason: str = Field(..., min_length=10, description="Rejection reason (min 10 chars)")
    notes: Optional[str] = Field(None, description="Additional notes")

    model_config = {"extra": "forbid"}


class ApprovalListFilter(BaseModel):
    """Filter for listing approvals."""
    status: Optional[ApprovalStatus] = None
    approval_type: Optional[ApprovalType] = None
    requested_by: Optional[str] = None
    risk_tier: Optional[RiskTier] = None
    include_expired: bool = Field(default=False, description="Include expired approvals")

    model_config = {"extra": "forbid"}


class ApprovalSummary(BaseModel):
    """Summary for approval list."""
    approval_id: str
    approval_type: ApprovalType
    status: ApprovalStatus
    risk_tier: RiskTier
    requested_by: str
    requested_at: float
    expires_at: float
    time_until_expiry: float
    action_description: str

    model_config = {"extra": "forbid"}


class ApprovalDetail(BaseModel):
    """Detailed approval information."""
    approval_id: str
    approval_type: ApprovalType
    status: ApprovalStatus
    context: ApprovalContext
    approved_by: Optional[str]
    approved_at: Optional[float]
    rejection_reason: Optional[str]
    expires_at: float
    time_until_expiry: float
    token_used: bool
    created_at: float
    updated_at: float

    model_config = {"extra": "forbid"}


class AuditExport(BaseModel):
    """Audit trail export."""
    approval_id: str
    entries: List[AuditEntry]
    exported_at: float = Field(default_factory=lambda: datetime.utcnow().timestamp())
    exported_by: str

    model_config = {"extra": "forbid"}


class GovernanceStats(BaseModel):
    """Governance system statistics."""
    total_approvals: int
    pending_approvals: int
    approved_count: int
    rejected_count: int
    expired_count: int
    by_type: Dict[str, int]
    by_risk_tier: Dict[str, int]
    average_approval_time: float  # seconds

    model_config = {"extra": "forbid"}
