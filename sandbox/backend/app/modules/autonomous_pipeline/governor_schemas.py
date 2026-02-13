"""
Execution Governor Schemas (Sprint 9-A)

Budget enforcement, policy decisions, and approval gates for autonomous pipeline.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class BudgetLimitType(str, Enum):
    """Types of budget limits."""
    HARD = "hard"  # Immediate failure
    SOFT = "soft"  # Degradation mode
    WARN = "warn"  # Log warning only


class GovernorDecisionType(str, Enum):
    """Governor decision types."""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    DEGRADE = "degrade"  # Skip non-critical nodes


class ApprovalStatus(str, Enum):
    """Approval request status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionBudget(BaseModel):
    """
    Budget constraints for pipeline execution.

    Prevents runaway costs and ensures bounded execution.
    """

    # Step limits
    max_steps: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Maximum number of nodes to execute"
    )

    # Time limits
    max_duration_seconds: float = Field(
        default=300.0,  # 5 minutes
        ge=1.0,
        le=3600.0,  # 1 hour max
        description="Maximum execution duration in seconds"
    )

    # External call limits
    max_external_calls: int = Field(
        default=10,
        ge=0,
        le=100,
        description="Maximum external API calls (DNS, Hetzner, etc.)"
    )

    # Cost limits (future)
    max_cost_usd: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum cost in USD (optional)"
    )

    # Limit types
    step_limit_type: BudgetLimitType = Field(
        default=BudgetLimitType.HARD,
        description="Enforcement type for step limit"
    )

    duration_limit_type: BudgetLimitType = Field(
        default=BudgetLimitType.HARD,
        description="Enforcement type for duration limit"
    )

    external_call_limit_type: BudgetLimitType = Field(
        default=BudgetLimitType.HARD,
        description="Enforcement type for external call limit"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "max_steps": 20,
                "max_duration_seconds": 180.0,
                "max_external_calls": 5,
                "max_cost_usd": 1.0,
                "step_limit_type": "hard",
                "duration_limit_type": "hard",
                "external_call_limit_type": "soft",
            }
        }


class ExecutionPolicy(BaseModel):
    """
    Policy rules for pipeline execution.

    Defines approval gates, critical nodes, and degradation rules.
    """

    policy_id: str = Field(..., description="Unique policy identifier")
    policy_name: str = Field(..., description="Human-readable name")

    # Budget
    budget: ExecutionBudget = Field(..., description="Budget constraints")

    # Approval gates
    require_approval_for_nodes: List[str] = Field(
        default_factory=list,
        description="Node IDs requiring manual approval"
    )

    require_approval_for_types: List[str] = Field(
        default_factory=list,
        description="Node types requiring approval (e.g., 'dns', 'odoo_module')"
    )

    # Critical nodes (cannot be skipped)
    critical_nodes: List[str] = Field(
        default_factory=list,
        description="Node IDs that must execute (no degradation)"
    )

    # Degradation rules
    allow_soft_degradation: bool = Field(
        default=True,
        description="Allow skipping non-critical nodes on budget breach"
    )

    skip_on_soft_limit: List[str] = Field(
        default_factory=lambda: ["webgenesis", "odoo_module"],
        description="Node types to skip on soft limit breach"
    )

    # Dry-run behavior
    dry_run_respects_limits: bool = Field(
        default=True,
        description="Apply budget limits even in dry-run mode"
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="system", description="Policy creator")

    class Config:
        json_schema_extra = {
            "example": {
                "policy_id": "policy_default",
                "policy_name": "Default Execution Policy",
                "budget": {
                    "max_steps": 20,
                    "max_duration_seconds": 180.0,
                    "max_external_calls": 5,
                },
                "require_approval_for_types": ["dns", "odoo_module"],
                "critical_nodes": ["webgen"],
                "allow_soft_degradation": True,
                "skip_on_soft_limit": ["odoo_module"],
            }
        }


class GovernorDecision(BaseModel):
    """
    Decision made by the execution governor.

    Determines whether a node can execute, needs approval, or must be skipped.
    """

    decision_type: GovernorDecisionType = Field(..., description="Decision type")
    node_id: str = Field(..., description="Node being evaluated")

    # Reasons
    allow_reason: Optional[str] = Field(None, description="Why execution was allowed")
    deny_reason: Optional[str] = Field(None, description="Why execution was denied")

    # Budget tracking
    budget_consumed: Dict[str, Any] = Field(
        default_factory=dict,
        description="Budget consumed so far"
    )

    budget_remaining: Dict[str, Any] = Field(
        default_factory=dict,
        description="Budget remaining"
    )

    # Approval (if required)
    requires_approval: bool = Field(default=False)
    approval_request_id: Optional[str] = Field(None)
    approval_status: Optional[ApprovalStatus] = Field(None)

    # Degradation
    degraded: bool = Field(
        default=False,
        description="Node was skipped due to degradation"
    )

    # Timestamp
    decided_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "decision_type": "allow",
                "node_id": "webgen",
                "allow_reason": "Within budget limits",
                "budget_consumed": {
                    "steps": 1,
                    "duration_seconds": 4.2,
                    "external_calls": 0,
                },
                "budget_remaining": {
                    "steps": 19,
                    "duration_seconds": 175.8,
                    "external_calls": 5,
                },
                "requires_approval": False,
                "degraded": False,
            }
        }


class ApprovalRequest(BaseModel):
    """
    Manual approval request for critical operations.
    """

    request_id: str = Field(..., description="Unique request ID")
    graph_id: str = Field(..., description="Execution graph ID")
    node_id: str = Field(..., description="Node requiring approval")
    node_type: str = Field(..., description="Node type")

    # Request details
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    requested_by: str = Field(default="system")

    # Node parameters (for review)
    node_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Node executor parameters"
    )

    # Status
    status: ApprovalStatus = Field(default=ApprovalStatus.PENDING)

    # Decision
    approved_by: Optional[str] = Field(None, description="Who approved/rejected")
    approved_at: Optional[datetime] = Field(None)
    rejection_reason: Optional[str] = Field(None)

    # Expiry
    expires_at: Optional[datetime] = Field(
        None,
        description="Approval request expiry (auto-reject after)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "approval_req_abc123",
                "graph_id": "graph_xyz",
                "node_id": "dns",
                "node_type": "dns",
                "requested_at": "2025-12-26T12:00:00Z",
                "node_params": {
                    "domain": "example.com",
                    "target_ip": "1.2.3.4",
                },
                "status": "pending",
                "expires_at": "2025-12-26T12:15:00Z",
            }
        }


class BudgetViolation(BaseModel):
    """
    Budget limit violation report.
    """

    violation_type: str = Field(..., description="Type of limit violated")
    limit_type: BudgetLimitType = Field(..., description="Hard/Soft/Warn")

    current_value: float = Field(..., description="Current consumed value")
    limit_value: float = Field(..., description="Maximum allowed value")

    exceeded_by: float = Field(..., description="Amount over limit")
    exceeded_by_percent: float = Field(..., description="Percentage over limit")

    # Action taken
    action_taken: str = Field(
        ...,
        description="Action: 'failed', 'degraded', 'warned'"
    )

    violated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "violation_type": "max_steps",
                "limit_type": "hard",
                "current_value": 21.0,
                "limit_value": 20.0,
                "exceeded_by": 1.0,
                "exceeded_by_percent": 5.0,
                "action_taken": "failed",
                "violated_at": "2025-12-26T12:00:10Z",
            }
        }
