"""
Foundation Module - Data Models

Pydantic schemas for Foundation layer operations.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Behavior Tree Models
# ============================================================================


class BehaviorTreeNode(BaseModel):
    """
    Behavior Tree node structure.

    Supports standard BT node types:
    - sequence: Execute children in order, fail if any fails
    - selector: Execute children until one succeeds
    - action: Execute a concrete action
    - condition: Check a condition, return success/failure
    """

    node_id: str = Field(..., description="Unique node identifier")
    node_type: Literal["sequence", "selector", "action", "condition"] = Field(
        ..., description="Type of behavior tree node"
    )
    children: List[BehaviorTreeNode] = Field(
        default_factory=list, description="Child nodes (for sequence/selector)"
    )
    action: Optional[str] = Field(
        None, description="Action to execute (for action/condition nodes)"
    )
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Parameters for the action"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "node_id": "move_forward",
                "node_type": "action",
                "action": "robot.move",
                "params": {"distance": 5.0, "speed": 1.0},
            }
        }


class BehaviorTreeExecutionResult(BaseModel):
    """Result of behavior tree execution"""

    status: Literal["success", "failure", "running"] = Field(
        ..., description="Execution status"
    )
    node_id: str = Field(..., description="Root node ID that was executed")
    message: str = Field(..., description="Execution message/details")
    executed_nodes: List[str] = Field(
        default_factory=list, description="List of executed node IDs"
    )
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# Foundation Configuration
# ============================================================================


class FoundationConfig(BaseModel):
    """
    Foundation layer configuration.

    Controls ethics enforcement, safety checks, and behavior tree execution.
    """

    ethics_enabled: bool = Field(
        True, description="Enable ethics enforcement for all actions"
    )
    safety_checks: bool = Field(
        True, description="Enable safety checks for dangerous operations"
    )
    strict_mode: bool = Field(
        False,
        description="Strict mode: Block all actions not explicitly whitelisted",
    )
    allowed_actions: List[str] = Field(
        default_factory=list,
        description="Whitelist of allowed actions (used in strict mode)",
    )
    blocked_actions: List[str] = Field(
        default_factory=lambda: [
            "delete_all",
            "format_disk",
            "sudo_rm_rf",
            "drop_database",
        ],
        description="Blacklist of always-blocked actions",
    )
    version: str = Field("0.1.0", description="Foundation config version")

    class Config:
        json_schema_extra = {
            "example": {
                "ethics_enabled": True,
                "safety_checks": True,
                "strict_mode": False,
                "blocked_actions": ["delete_all", "format_disk"],
            }
        }


# ============================================================================
# Foundation Status
# ============================================================================


class FoundationStatus(BaseModel):
    """Foundation system status and metrics"""

    active: bool = Field(..., description="Whether Foundation layer is active")
    ethics_enabled: bool = Field(..., description="Ethics enforcement status")
    safety_checks: bool = Field(..., description="Safety checks status")
    strict_mode: bool = Field(..., description="Strict mode status")
    ethics_violations: int = Field(
        0, description="Total number of ethics violations blocked"
    )
    safety_overrides: int = Field(
        0, description="Total number of safety overrides (dangerous actions blocked)"
    )
    total_validations: int = Field(
        0, description="Total number of action validations performed"
    )
    last_check: datetime = Field(
        default_factory=datetime.utcnow, description="Last validation timestamp"
    )
    uptime_seconds: float = Field(0.0, description="Foundation service uptime")

    class Config:
        json_schema_extra = {
            "example": {
                "active": True,
                "ethics_enabled": True,
                "safety_checks": True,
                "strict_mode": False,
                "ethics_violations": 5,
                "safety_overrides": 2,
                "total_validations": 1523,
                "uptime_seconds": 86400.0,
            }
        }


# ============================================================================
# Action Validation Models
# ============================================================================


class ActionValidationRequest(BaseModel):
    """Request to validate an action against ethics/safety rules"""

    action: str = Field(..., description="Action name to validate")
    params: Dict[str, Any] = Field(
        default_factory=dict, description="Action parameters"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context (agent_id, user_id, etc.)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "action": "robot.move",
                "params": {"distance": 10, "speed": 2},
                "context": {"agent_id": "robot_001"},
            }
        }


class ActionValidationResponse(BaseModel):
    """Response from action validation"""

    valid: bool = Field(..., description="Whether action is allowed")
    action: str = Field(..., description="Action that was validated")
    reason: Optional[str] = Field(None, description="Reason for blocking (if blocked)")
    severity: Literal["info", "warning", "critical"] = Field(
        "info", description="Severity level"
    )
    suggestions: List[str] = Field(
        default_factory=list, description="Alternative safe actions (if blocked)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "action": "robot.move",
                "severity": "info",
            }
        }


# ============================================================================
# Ethics Rule Models (for future expansion)
# ============================================================================


class EthicsRule(BaseModel):
    """
    Ethics rule definition.

    Placeholder for future ethics engine.
    """

    rule_id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Human-readable rule name")
    description: str = Field(..., description="Rule description")
    pattern: str = Field(..., description="Action pattern to match (regex)")
    action_type: Literal["allow", "block", "warn"] = Field(
        ..., description="Action to take when pattern matches"
    )
    priority: int = Field(0, description="Rule priority (higher = checked first)")
    enabled: bool = Field(True, description="Whether rule is enabled")

    class Config:
        json_schema_extra = {
            "example": {
                "rule_id": "no_destructive_ops",
                "name": "Block Destructive Operations",
                "description": "Prevents deletion of critical resources",
                "pattern": ".*delete.*|.*drop.*|.*destroy.*",
                "action_type": "block",
                "priority": 100,
            }
        }


# ============================================================================
# Foundation Info (System Information)
# ============================================================================


class FoundationInfo(BaseModel):
    """Foundation system information"""

    name: str = Field(..., description="Foundation system name")
    version: str = Field(..., description="Foundation version")
    capabilities: List[str] = Field(..., description="List of system capabilities")
    status: Literal["operational", "degraded", "offline"] = Field(
        ..., description="Current system status"
    )
    uptime: float = Field(..., description="System uptime in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "BRAiN Foundation Layer",
                "version": "1.0.0",
                "capabilities": [
                    "action_validation",
                    "ethics_rules",
                    "safety_patterns",
                    "behavior_trees",
                ],
                "status": "operational",
                "uptime": 86400.0,
            }
        }


# ============================================================================
# Authorization Models
# ============================================================================


class AuthorizationRequest(BaseModel):
    """Request to check action authorization"""

    agent_id: str = Field(..., description="Agent requesting authorization")
    action: str = Field(..., description="Action to authorize")
    resource: str = Field(..., description="Resource being accessed")
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Additional context"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "ops_agent",
                "action": "deploy_to_production",
                "resource": "brain-backend",
                "context": {"environment": "production"},
            }
        }


class AuthorizationResponse(BaseModel):
    """Response from authorization check"""

    authorized: bool = Field(..., description="Whether action is authorized")
    reason: str = Field(..., description="Reason for authorization result")
    required_permissions: List[str] = Field(
        default_factory=list, description="Required permissions for this action"
    )
    audit_id: str = Field(..., description="Audit trail identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "authorized": True,
                "reason": "Agent has required permissions",
                "required_permissions": [],
                "audit_id": "audit_20260115_170000",
            }
        }


# ============================================================================
# Audit Log Models
# ============================================================================


class AuditLogEntry(BaseModel):
    """Single audit log entry"""

    audit_id: str = Field(..., description="Unique audit identifier")
    timestamp: datetime = Field(..., description="Event timestamp")
    event_type: Literal["validation", "authorization"] = Field(
        ..., description="Type of event"
    )
    agent_id: Optional[str] = Field(None, description="Agent ID (if applicable)")
    action: str = Field(..., description="Action that was checked")
    outcome: Literal["allowed", "blocked", "authorized", "denied"] = Field(
        ..., description="Event outcome"
    )
    reason: str = Field(..., description="Reason for outcome")
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional event details"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "audit_id": "audit_20260115_170000",
                "timestamp": "2026-01-15T17:00:00Z",
                "event_type": "validation",
                "agent_id": "ops_agent",
                "action": "deploy_to_production",
                "outcome": "blocked",
                "reason": "Action is in blacklist",
                "details": {"environment": "production"},
            }
        }


class AuditLogRequest(BaseModel):
    """Request to query audit log"""

    agent_id: Optional[str] = Field(None, description="Filter by agent ID")
    action: Optional[str] = Field(None, description="Filter by action")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    outcome: Optional[str] = Field(None, description="Filter by outcome")
    limit: int = Field(100, ge=1, le=1000, description="Maximum entries to return")
    offset: int = Field(0, ge=0, description="Pagination offset")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "ops_agent",
                "outcome": "blocked",
                "limit": 50,
                "offset": 0,
            }
        }


class AuditLogResponse(BaseModel):
    """Response containing audit log entries"""

    entries: List[AuditLogEntry] = Field(..., description="List of audit entries")
    total: int = Field(..., description="Total matching entries")
    limit: int = Field(..., description="Query limit")
    offset: int = Field(..., description="Query offset")

    class Config:
        json_schema_extra = {
            "example": {
                "entries": [],
                "total": 42,
                "limit": 50,
                "offset": 0,
            }
        }
