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
