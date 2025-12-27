"""
Policy Module - Data Models

Extended policy schemas for rule-based governance and permissions.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Legacy Schemas (kept for backward compatibility)
# ============================================================================


class PolicyHealth(BaseModel):
    """Policy system health status"""

    status: str
    timestamp: datetime


class PolicyInfo(BaseModel):
    """Policy system information"""

    name: str
    version: str
    config: dict[str, Any] | None = None


# ============================================================================
# Policy Engine Schemas (NEW in v0.3.0)
# ============================================================================


class PolicyEffect(str, Enum):
    """Policy effect when rule matches"""

    ALLOW = "allow"  # Explicitly allow action
    DENY = "deny"  # Explicitly deny action
    WARN = "warn"  # Allow but log warning
    AUDIT = "audit"  # Allow but require audit trail


class PolicyConditionOperator(str, Enum):
    """Operators for policy conditions"""

    EQUALS = "=="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    LESS_THAN = "<"
    CONTAINS = "contains"
    MATCHES = "matches"  # Regex
    IN = "in"  # List membership


class PolicyCondition(BaseModel):
    """
    Single condition in a policy rule.

    Example: {"field": "agent.role", "operator": "==", "value": "admin"}
    """

    field: str = Field(..., description="Field to evaluate (dot notation)")
    operator: PolicyConditionOperator = Field(..., description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")

    class Config:
        json_schema_extra = {
            "example": {
                "field": "agent.role",
                "operator": "==",
                "value": "admin",
            }
        }


class PolicyRule(BaseModel):
    """
    A single policy rule with conditions and effect.

    Rules are evaluated in priority order (highest first).
    """

    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field("", description="Rule description/purpose")
    effect: PolicyEffect = Field(..., description="Effect when rule matches")
    conditions: List[PolicyCondition] = Field(
        default_factory=list, description="Conditions that must ALL be true (AND logic)"
    )
    priority: int = Field(0, description="Rule priority (higher = evaluated first)")
    enabled: bool = Field(True, description="Whether rule is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "rule_id": "admin_full_access",
                "name": "Admin Full Access",
                "description": "Admins can do anything",
                "effect": "allow",
                "conditions": [{"field": "agent.role", "operator": "==", "value": "admin"}],
                "priority": 100,
                "enabled": True,
            }
        }


class Policy(BaseModel):
    """
    Complete policy with metadata and rules.

    Policies are collections of rules that govern agent behavior.
    """

    policy_id: str = Field(..., description="Unique policy identifier")
    name: str = Field(..., description="Policy name")
    version: str = Field("1.0.0", description="Policy version (semver)")
    description: str = Field("", description="Policy description")
    rules: List[PolicyRule] = Field(default_factory=list, description="Policy rules")
    default_effect: PolicyEffect = Field(
        PolicyEffect.DENY, description="Default effect when no rules match"
    )
    enabled: bool = Field(True, description="Whether policy is active")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Last update timestamp"
    )
    created_by: Optional[str] = Field(None, description="Creator user/agent ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extra metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "policy_id": "robot_safety_policy",
                "name": "Robot Safety Policy",
                "version": "1.0.0",
                "description": "Safety rules for robot operations",
                "default_effect": "deny",
                "enabled": True,
            }
        }


class PolicyEvaluationContext(BaseModel):
    """
    Context provided for policy evaluation.

    Contains information about the agent, action, environment, etc.
    Optionally enriched with ML risk scores.
    """

    agent_id: str = Field(..., description="ID of agent requesting action")
    agent_role: Optional[str] = Field(None, description="Agent role/type")
    action: str = Field(..., description="Action being requested")
    resource: Optional[str] = Field(None, description="Resource being accessed")
    environment: Dict[str, Any] = Field(
        default_factory=dict, description="Environmental context (time, location, etc.)"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )

    # ML Enrichment (optional)
    ml_risk_score: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="ML-computed risk score (0=safe, 1=critical)"
    )
    ml_confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="ML confidence in risk score"
    )
    ml_model_version: Optional[str] = Field(
        None, description="ML model version used"
    )
    ml_is_fallback: Optional[bool] = Field(
        None, description="Whether ML score is fallback value"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "robot_001",
                "agent_role": "fleet_member",
                "action": "robot.move",
                "resource": "warehouse_zone_a",
                "environment": {"time": "daytime", "battery_level": 80},
                "params": {"distance": 10, "speed": 2},
            }
        }


class PolicyEvaluationResult(BaseModel):
    """Result of policy evaluation"""

    allowed: bool = Field(..., description="Whether action is allowed")
    effect: PolicyEffect = Field(..., description="Applied effect")
    matched_rule: Optional[str] = Field(
        None, description="ID of matched rule (if any)"
    )
    matched_policy: Optional[str] = Field(
        None, description="ID of matched policy (if any)"
    )
    reason: str = Field(..., description="Human-readable reason for decision")
    warnings: List[str] = Field(
        default_factory=list, description="Warnings if effect is WARN"
    )
    requires_audit: bool = Field(
        False, description="Whether action requires audit trail"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "allowed": True,
                "effect": "allow",
                "matched_rule": "fleet_member_basic_movement",
                "matched_policy": "robot_safety_policy",
                "reason": "Fleet member allowed basic movement in assigned zone",
            }
        }


class Permission(BaseModel):
    """
    Permission model for agent capabilities.

    Permissions are simpler than policies - just resource + action.
    """

    permission_id: str = Field(..., description="Unique permission ID")
    agent_id: str = Field(..., description="Agent this permission applies to")
    resource: str = Field(..., description="Resource (e.g., 'robot.move', 'data.read')")
    action: str = Field(..., description="Action allowed on resource")
    granted_at: datetime = Field(
        default_factory=datetime.utcnow, description="When permission was granted"
    )
    expires_at: Optional[datetime] = Field(
        None, description="When permission expires (None = never)"
    )
    granted_by: Optional[str] = Field(None, description="Who granted permission")

    class Config:
        json_schema_extra = {
            "example": {
                "permission_id": "perm_001",
                "agent_id": "robot_001",
                "resource": "warehouse_zone_a",
                "action": "move",
                "granted_by": "admin_user",
            }
        }


class PolicyCreateRequest(BaseModel):
    """Request to create a new policy"""

    name: str
    version: str = "1.0.0"
    description: str = ""
    rules: List[PolicyRule] = []
    default_effect: PolicyEffect = PolicyEffect.DENY
    enabled: bool = True


class PolicyUpdateRequest(BaseModel):
    """Request to update an existing policy"""

    name: Optional[str] = None
    description: Optional[str] = None
    rules: Optional[List[PolicyRule]] = None
    default_effect: Optional[PolicyEffect] = None
    enabled: Optional[bool] = None


class PolicyListResponse(BaseModel):
    """Response for listing policies"""

    total: int
    policies: List[Policy]


class PolicyStats(BaseModel):
    """Policy system statistics"""

    total_policies: int
    active_policies: int
    total_rules: int
    total_evaluations: int
    total_allows: int
    total_denies: int
    total_warnings: int
