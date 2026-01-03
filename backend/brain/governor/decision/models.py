"""
Governor v1 Decision Models (Phase 2a)

Models for deterministic agent creation governance decisions.

This module defines the request/response structures for Governor v1,
which makes formal decisions on agent creation with:
- approve / reject / approve_with_constraints
- Constraints enforcement
- Risk tier classification
- Quarantine decisions
- Complete audit trail

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================

class DecisionType(str, Enum):
    """
    Governor decision types.

    - APPROVE: Unconditional approval (default constraints only)
    - REJECT: Denied (with reason code)
    - APPROVE_WITH_CONSTRAINTS: Approved with additional constraints
    """
    APPROVE = "approve"
    REJECT = "reject"
    APPROVE_WITH_CONSTRAINTS = "approve_with_constraints"


class ReasonCode(str, Enum):
    """
    Reason codes for decisions.

    Success codes (2xx):
    - APPROVED_DEFAULT: Approved with default constraints
    - APPROVED_WITH_CONSTRAINTS: Approved with additional constraints

    Rejection codes (4xx):
    - UNAUTHORIZED_ROLE: Actor role not authorized
    - TEMPLATE_NOT_IN_ALLOWLIST: Template not in allowlist
    - TEMPLATE_HASH_MISSING: Template hash not provided
    - CAPABILITY_ESCALATION_DENIED: Customization attempts capability escalation
    - BUDGET_INSUFFICIENT: Insufficient budget available
    - POPULATION_LIMIT_EXCEEDED: AgentType population limit exceeded
    - KILLSWITCH_ACTIVE: Kill switch is active

    System codes (5xx):
    - EVALUATION_ERROR: Internal evaluation error
    """
    # Success codes (2xx)
    APPROVED_DEFAULT = "APPROVED_DEFAULT"
    APPROVED_WITH_CONSTRAINTS = "APPROVED_WITH_CONSTRAINTS"

    # Rejection codes (4xx)
    UNAUTHORIZED_ROLE = "UNAUTHORIZED_ROLE"
    TEMPLATE_NOT_IN_ALLOWLIST = "TEMPLATE_NOT_IN_ALLOWLIST"
    TEMPLATE_HASH_MISSING = "TEMPLATE_HASH_MISSING"
    CAPABILITY_ESCALATION_DENIED = "CAPABILITY_ESCALATION_DENIED"
    BUDGET_INSUFFICIENT = "BUDGET_INSUFFICIENT"
    POPULATION_LIMIT_EXCEEDED = "POPULATION_LIMIT_EXCEEDED"
    KILLSWITCH_ACTIVE = "KILLSWITCH_ACTIVE"

    # System codes (5xx)
    EVALUATION_ERROR = "EVALUATION_ERROR"


class RiskTier(str, Enum):
    """
    Risk tier classification for agents.

    Risk tiers determine oversight level and constraints:
    - LOW: Standard agents with minimal oversight
    - MEDIUM: Agents with moderate capabilities, standard review
    - HIGH: Agents with elevated capabilities or data access
    - CRITICAL: System agents (Genesis, Governor, Supervisor, Ligase, KARMA)
    """
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# ============================================================================
# Decision Request
# ============================================================================

class ActorContext(BaseModel):
    """
    Context about the actor requesting agent creation.

    Attributes:
        user_id: User identifier
        role: User role (must be SYSTEM_ADMIN for agent creation)
        source: Source system/service
    """
    user_id: str = Field(..., description="User identifier")
    role: str = Field(..., description="User role (SYSTEM_ADMIN required)")
    source: str = Field(..., description="Source system/service")


class RequestContext(BaseModel):
    """
    Additional context for decision evaluation.

    Attributes:
        ip_address: Client IP address (for audit)
        tenant_id: Tenant identifier (if multi-tenant)
        project_id: Project identifier
        has_customizations: Whether request includes customizations
        customization_fields: List of customized field paths
    """
    ip_address: Optional[str] = None
    tenant_id: Optional[str] = None
    project_id: Optional[str] = None
    has_customizations: bool = False
    customization_fields: List[str] = Field(default_factory=list)


class DecisionRequest(BaseModel):
    """
    Request for Governor decision on agent creation.

    Contains all information needed for deterministic policy evaluation:
    - Actor context (who, role, source)
    - DNA to be evaluated
    - Template tracking (name, hash)
    - Request context (customizations, etc.)

    Example:
        >>> request = DecisionRequest(
        ...     request_id="req-abc123",
        ...     operation="agent_creation",
        ...     actor=ActorContext(
        ...         user_id="admin-001",
        ...         role="SYSTEM_ADMIN",
        ...         source="genesis_api"
        ...     ),
        ...     agent_dna=dna,
        ...     template_name="worker_base",
        ...     template_hash="sha256:abc123...",
        ...     context=RequestContext(has_customizations=True)
        ... )
    """

    # Request identification
    request_id: str = Field(
        ...,
        description="Unique request identifier (from Genesis)"
    )

    decision_id: str = Field(
        default_factory=lambda: f"dec_{uuid.uuid4().hex[:16]}",
        description="Unique decision identifier"
    )

    operation: str = Field(
        default="agent_creation",
        description="Operation type (always 'agent_creation' for Phase 2a)"
    )

    timestamp: float = Field(
        default_factory=time.time,
        description="Request timestamp (Unix epoch)"
    )

    # Actor context
    actor: ActorContext = Field(
        ...,
        description="Actor requesting the creation"
    )

    # Agent DNA
    agent_dna: Dict[str, Any] = Field(
        ...,
        description="Agent DNA to evaluate (Pydantic model as dict)"
    )

    dna_hash: str = Field(
        ...,
        description="SHA256 hash of DNA (for audit trail)"
    )

    # Template tracking
    template_name: str = Field(
        ...,
        description="Template name (e.g., 'worker_base')"
    )

    template_hash: str = Field(
        ...,
        description="SHA256 hash of template (MANDATORY)"
    )

    # Request context
    context: RequestContext = Field(
        default_factory=RequestContext,
        description="Additional request context"
    )


# ============================================================================
# Decision Result
# ============================================================================

class DecisionResult(BaseModel):
    """
    Governor decision result for agent creation.

    Immutable record of:
    - Whether creation is approved/rejected
    - Decision type and reason code
    - Risk tier classification
    - Constraints to apply (if approved)
    - Quarantine status
    - Policy versioning
    - Audit metadata

    Example:
        >>> result = DecisionResult(
        ...     approved=True,
        ...     decision_type=DecisionType.APPROVE_WITH_CONSTRAINTS,
        ...     reason_code=ReasonCode.APPROVED_WITH_CONSTRAINTS,
        ...     reason_detail="Customizations detected, constraints applied",
        ...     risk_tier=RiskTier.MEDIUM,
        ...     constraints={"max_credits_per_mission": 50},
        ...     quarantine=False,
        ...     policy_version="1.0.0",
        ...     ruleset_version="2a"
        ... )
    """

    # Decision identification (from request)
    decision_id: str = Field(
        ...,
        description="Unique decision identifier"
    )

    request_id: str = Field(
        ...,
        description="Original request identifier"
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Decision timestamp (UTC)"
    )

    # Decision output
    approved: bool = Field(
        ...,
        description="Whether creation is approved"
    )

    decision_type: DecisionType = Field(
        ...,
        description="Decision type (approve/reject/approve_with_constraints)"
    )

    reason_code: ReasonCode = Field(
        ...,
        description="Machine-readable reason code"
    )

    reason_detail: str = Field(
        ...,
        max_length=500,
        description="Human-readable reason (max 500 chars)"
    )

    # Risk classification
    risk_tier: RiskTier = Field(
        ...,
        description="Risk tier (LOW/MEDIUM/HIGH/CRITICAL)"
    )

    # Constraints (optional, only for approved decisions)
    constraints: Optional[Dict[str, Any]] = Field(
        None,
        description="EffectiveConstraints to apply (if approved)"
    )

    # Quarantine
    quarantine: bool = Field(
        ...,
        description="Whether agent should be quarantined (Phase 3)"
    )

    # Policy versioning
    policy_version: str = Field(
        ...,
        description="Policy version used for decision"
    )

    ruleset_version: str = Field(
        ...,
        description="Ruleset version (e.g., '2a', '2b')"
    )

    # Audit metadata
    evaluated_rules: List[str] = Field(
        default_factory=list,
        description="Rule IDs that were evaluated"
    )

    triggered_rules: List[str] = Field(
        default_factory=list,
        description="Rule IDs that triggered (caused decision)"
    )

    evaluation_duration_ms: float = Field(
        default=0.0,
        description="Decision evaluation duration in milliseconds"
    )

    # Actor context (for audit)
    actor_user_id: str = Field(
        ...,
        description="User ID of actor"
    )

    actor_role: str = Field(
        ...,
        description="Role of actor"
    )

    # Template tracking
    template_name: str = Field(
        ...,
        description="Template name"
    )

    template_hash: str = Field(
        ...,
        description="Template hash"
    )

    dna_hash: str = Field(
        ...,
        description="DNA hash"
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "decision_id": "dec_abc123def456",
                "request_id": "req-xyz789",
                "timestamp": "2026-01-02T12:00:00.000000Z",
                "approved": True,
                "decision_type": "approve_with_constraints",
                "reason_code": "APPROVED_WITH_CONSTRAINTS",
                "reason_detail": "Customizations detected, constraints applied",
                "risk_tier": "MEDIUM",
                "constraints": {
                    "budget": {
                        "max_credits_per_mission": 50,
                        "max_daily_credits": 500
                    }
                },
                "quarantine": False,
                "policy_version": "1.0.0",
                "ruleset_version": "2a",
                "evaluated_rules": ["A1", "B1", "C1"],
                "triggered_rules": ["C2"],
                "evaluation_duration_ms": 12.5,
                "actor_user_id": "admin-001",
                "actor_role": "SYSTEM_ADMIN",
                "template_name": "worker_base",
                "template_hash": "sha256:abc123...",
                "dna_hash": "def456..."
            }
        }
