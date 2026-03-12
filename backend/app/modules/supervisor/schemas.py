from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Risk Assessment
# ============================================================================


class RiskLevel(str, Enum):
    """Risk severity levels for agent actions"""
    LOW = "low"           # Read-only operations, no side effects
    MEDIUM = "medium"     # Write operations, reversible
    HIGH = "high"         # Critical operations, personal data, production changes
    CRITICAL = "critical" # Irreversible, system-wide impact


# ============================================================================
# Supervision Requests & Responses
# ============================================================================


class SupervisionRequest(BaseModel):
    """Request for supervisor approval of agent action"""
    requesting_agent: str = Field(..., description="Agent ID requesting supervision")
    action: str = Field(..., description="Action to be performed (e.g., 'deploy_application')")
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context information for the action"
    )
    risk_level: RiskLevel = Field(..., description="Assessed risk level of the action")
    reason: Optional[str] = Field(
        None,
        description="Reason/justification for the action"
    )
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SupervisionResponse(BaseModel):
    """Response from supervisor after action evaluation"""
    approved: bool = Field(..., description="Whether the action is approved")
    reason: str = Field(..., description="Explanation for the decision")
    human_oversight_required: bool = Field(
        default=False,
        description="Whether human approval is needed"
    )
    human_oversight_token: Optional[str] = Field(
        None,
        description="Token for human approval workflow"
    )
    audit_id: str = Field(..., description="Audit trail ID for this decision")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    policy_violations: List[str] = Field(
        default_factory=list,
        description="List of policy violations detected"
    )


# ============================================================================
# Agent Status & Health
# ============================================================================


class AgentStatus(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    state: str
    last_heartbeat: Optional[datetime] = None
    missions_running: int = 0


class SupervisorHealth(BaseModel):
    status: str
    timestamp: datetime


class SupervisorStatus(BaseModel):
    status: str
    timestamp: datetime
    total_missions: int
    running_missions: int
    pending_missions: int
    completed_missions: int
    failed_missions: int
    cancelled_missions: int
    agents: List[AgentStatus] = []

    # New supervision metrics
    total_supervision_requests: int = Field(
        default=0,
        description="Total supervision requests processed"
    )
    approved_actions: int = Field(
        default=0,
        description="Number of approved actions"
    )
    denied_actions: int = Field(
        default=0,
        description="Number of denied actions"
    )
    human_approvals_pending: int = Field(
        default=0,
        description="Actions waiting for human approval"
    )


class DomainEscalationRequest(BaseModel):
    """Domain-to-supervisor escalation handoff payload."""

    domain_key: str = Field(..., min_length=1, max_length=100)
    requested_by: str = Field(..., min_length=1, max_length=120)
    requested_by_type: str = Field(..., min_length=1, max_length=32)
    tenant_id: Optional[str] = Field(default=None, max_length=64)
    reason: str = Field(..., min_length=1, max_length=1000)
    reasons: List[str] = Field(default_factory=list)
    recommended_next_actions: List[str] = Field(default_factory=list)
    risk_tier: str = Field(default="high", max_length=32)
    correlation_id: Optional[str] = Field(default=None, max_length=160)
    context: Dict[str, Any] = Field(default_factory=dict)


class DomainEscalationResponse(BaseModel):
    """Supervisor handoff record returned after escalation submission."""

    escalation_id: str
    status: str
    received_at: datetime
    domain_key: str
    requested_by: str
    risk_tier: str
    correlation_id: Optional[str] = None


class DomainEscalationStatus(str, Enum):
    QUEUED = "queued"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"


class DomainEscalationDecisionRequest(BaseModel):
    """Supervisor decision payload for an escalation.

    Note: ``reviewer_id`` is always overwritten server-side with the authenticated
    principal's ID (see router). Callers may omit it; any supplied value is ignored.
    """

    status: DomainEscalationStatus = Field(...)
    reviewer_id: Optional[str] = Field(default=None, max_length=120)
    decision_reason: str = Field(..., min_length=1, max_length=1000)
    notes: Dict[str, Any] = Field(default_factory=dict)


class DomainEscalationListResponse(BaseModel):
    """List response for escalation handoff records."""

    items: List[DomainEscalationResponse] = Field(default_factory=list)
    total: int = 0
