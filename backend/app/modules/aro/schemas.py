"""
ARO Module - Data Models and Schemas

BRAiN Autonomous Repo Operator (ARO) - Phase 1
Provides strict governance and safety for repository operations.

Principles:
- Fail-closed: Deny by default
- Explicit authorization required for all actions
- Complete audit trail (append-only)
- Deterministic state machine
- No implicit state changes
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, validator


# ============================================================================
# Enumerations
# ============================================================================


class RepoOperationType(str, Enum):
    """
    Types of repository operations.

    All operations require explicit authorization.
    """

    # Read operations (lowest risk)
    READ_FILE = "read_file"
    LIST_FILES = "list_files"
    GET_STATUS = "get_status"
    GET_DIFF = "get_diff"
    GET_LOG = "get_log"

    # Write operations (medium risk)
    CREATE_FILE = "create_file"
    UPDATE_FILE = "update_file"
    DELETE_FILE = "delete_file"
    CREATE_BRANCH = "create_branch"

    # Git operations (high risk)
    COMMIT = "commit"
    PUSH = "push"
    MERGE = "merge"
    REBASE = "rebase"

    # Dangerous operations (requires elevated authorization)
    FORCE_PUSH = "force_push"
    DELETE_BRANCH = "delete_branch"
    RESET_HARD = "reset_hard"


class OperationState(str, Enum):
    """
    State machine states for repo operations.

    State transitions are strictly controlled.
    """

    # Initial states
    PROPOSED = "proposed"           # Operation proposed, not yet validated
    VALIDATING = "validating"       # Running validation checks

    # Authorization states
    PENDING_AUTH = "pending_auth"   # Waiting for authorization
    AUTHORIZED = "authorized"       # Explicitly authorized
    DENIED = "denied"              # Authorization denied

    # Execution states
    EXECUTING = "executing"        # Currently executing
    COMPLETED = "completed"        # Successfully completed
    FAILED = "failed"             # Execution failed

    # Terminal states
    ROLLED_BACK = "rolled_back"   # Changes rolled back
    CANCELLED = "cancelled"        # Cancelled before execution


class AuthorizationLevel(str, Enum):
    """
    Authorization levels for operations.

    Higher levels required for riskier operations.
    """

    NONE = "none"                  # No authorization
    READ_ONLY = "read_only"        # Can read files
    WRITE = "write"                # Can modify files
    COMMIT = "commit"              # Can commit changes
    PUSH = "push"                  # Can push to remote
    ADMIN = "admin"                # Full control (dangerous ops)


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ============================================================================
# Core Models
# ============================================================================


class RepoOperationContext(BaseModel):
    """
    Context for a repository operation.

    Contains all information needed to evaluate and execute an operation.
    """

    operation_id: str = Field(..., description="Unique operation identifier")
    operation_type: RepoOperationType = Field(..., description="Type of operation")

    # Agent information
    agent_id: str = Field(..., description="ID of agent requesting operation")
    agent_role: Optional[str] = Field(None, description="Role of requesting agent")

    # Repository information
    repo_path: str = Field(..., description="Path to repository")
    branch: str = Field("main", description="Target branch")

    # Operation parameters
    params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Operation-specific parameters"
    )

    # Authorization
    requested_auth_level: AuthorizationLevel = Field(
        AuthorizationLevel.NONE,
        description="Requested authorization level"
    )
    granted_auth_level: AuthorizationLevel = Field(
        AuthorizationLevel.NONE,
        description="Actually granted authorization level"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When operation was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time"
    )

    # Audit trail reference
    audit_trail_id: Optional[str] = Field(
        None,
        description="Reference to audit trail entry"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op_001",
                "operation_type": "commit",
                "agent_id": "aro_agent",
                "repo_path": "/home/user/BRAiN",
                "branch": "claude/aro-phase-1",
                "params": {"message": "feat: Add ARO module"},
                "requested_auth_level": "commit"
            }
        }


class ValidationResult(BaseModel):
    """
    Result of validation checks.

    All issues must be addressed before execution.
    """

    valid: bool = Field(..., description="Whether validation passed")
    severity: ValidationSeverity = Field(..., description="Highest severity found")

    issues: List[str] = Field(
        default_factory=list,
        description="List of validation issues"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-blocking warnings"
    )

    # Detailed validation results
    checks_passed: int = Field(0, description="Number of checks passed")
    checks_failed: int = Field(0, description="Number of checks failed")

    # Validation metadata
    validated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When validation was performed"
    )
    validator_id: str = Field(..., description="ID of validator that ran")

    class Config:
        json_schema_extra = {
            "example": {
                "valid": True,
                "severity": "info",
                "issues": [],
                "warnings": ["File is large (500 lines)"],
                "checks_passed": 5,
                "checks_failed": 0,
                "validator_id": "file_safety_validator"
            }
        }


class SafetyCheckResult(BaseModel):
    """
    Result of safety checkpoint verification.

    Safety checks are fail-closed: any failure blocks operation.
    """

    safe: bool = Field(..., description="Whether operation is safe")
    checkpoint_id: str = Field(..., description="ID of checkpoint")

    reason: str = Field(..., description="Reason for decision")
    blocked_reasons: List[str] = Field(
        default_factory=list,
        description="Reasons why operation was blocked (if unsafe)"
    )

    # Risk assessment
    risk_score: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Risk score (0.0 = safe, 1.0 = dangerous)"
    )
    risk_factors: List[str] = Field(
        default_factory=list,
        description="Identified risk factors"
    )

    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When check was performed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "safe": True,
                "checkpoint_id": "pre_commit_check",
                "reason": "All safety checks passed",
                "risk_score": 0.2,
                "risk_factors": ["Modifying existing file"]
            }
        }


class AuditLogEntry(BaseModel):
    """
    Single audit log entry.

    Audit log is append-only - entries are NEVER modified or deleted.
    """

    # Unique identifier
    entry_id: str = Field(..., description="Unique entry ID")

    # Operation reference
    operation_id: str = Field(..., description="Associated operation ID")
    operation_type: RepoOperationType = Field(..., description="Type of operation")

    # State machine
    previous_state: Optional[OperationState] = Field(
        None,
        description="Previous state (None for first entry)"
    )
    new_state: OperationState = Field(..., description="New state")

    # Agent information
    agent_id: str = Field(..., description="Agent that triggered this entry")

    # Event details
    event_type: str = Field(..., description="Type of event (state_change, error, etc.)")
    message: str = Field(..., description="Human-readable message")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional details"
    )

    # Timestamp (append-only guarantee)
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this entry was created (immutable)"
    )

    # Integrity
    previous_entry_id: Optional[str] = Field(
        None,
        description="Previous entry ID (for chain verification)"
    )

    class Config:
        # Make model immutable after creation
        frozen = True
        json_schema_extra = {
            "example": {
                "entry_id": "audit_001",
                "operation_id": "op_001",
                "operation_type": "commit",
                "previous_state": "authorized",
                "new_state": "executing",
                "agent_id": "aro_agent",
                "event_type": "state_change",
                "message": "Starting commit execution",
                "timestamp": "2025-12-21T10:00:00Z"
            }
        }


class RepoOperation(BaseModel):
    """
    Complete repository operation with full lifecycle.

    Represents the entire lifecycle of a repo operation from proposal to completion.
    """

    # Core fields
    operation_id: str = Field(..., description="Unique operation identifier")
    context: RepoOperationContext = Field(..., description="Operation context")

    # State machine
    current_state: OperationState = Field(
        OperationState.PROPOSED,
        description="Current state in lifecycle"
    )
    state_history: List[OperationState] = Field(
        default_factory=list,
        description="History of state transitions"
    )

    # Validation
    validation_results: List[ValidationResult] = Field(
        default_factory=list,
        description="Results from all validators"
    )

    # Safety checks
    safety_check_results: List[SafetyCheckResult] = Field(
        default_factory=list,
        description="Results from all safety checkpoints"
    )

    # Authorization
    authorization_granted: bool = Field(
        False,
        description="Whether operation is authorized"
    )
    authorized_by: Optional[str] = Field(
        None,
        description="Who authorized the operation"
    )
    authorized_at: Optional[datetime] = Field(
        None,
        description="When authorization was granted"
    )

    # Execution
    execution_started_at: Optional[datetime] = Field(
        None,
        description="When execution started"
    )
    execution_completed_at: Optional[datetime] = Field(
        None,
        description="When execution completed"
    )
    execution_result: Optional[Dict[str, Any]] = Field(
        None,
        description="Result of execution"
    )
    execution_error: Optional[str] = Field(
        None,
        description="Error message if execution failed"
    )

    # Audit trail
    audit_log_entries: List[str] = Field(
        default_factory=list,
        description="IDs of audit log entries for this operation"
    )

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When operation was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update time"
    )

    @validator('current_state')
    def validate_state_transition(cls, v, values):
        """
        Validate state transitions.

        Only specific transitions are allowed.
        """
        # This is a basic validator - full state machine logic in service layer
        return v

    def can_execute(self) -> bool:
        """
        Check if operation can be executed.

        Returns:
            True if all prerequisites are met
        """
        return (
            self.current_state == OperationState.AUTHORIZED
            and self.authorization_granted
            and all(v.valid for v in self.validation_results)
            and all(s.safe for s in self.safety_check_results)
        )

    def is_terminal_state(self) -> bool:
        """Check if operation is in a terminal state"""
        terminal_states = {
            OperationState.COMPLETED,
            OperationState.FAILED,
            OperationState.ROLLED_BACK,
            OperationState.CANCELLED,
            OperationState.DENIED
        }
        return self.current_state in terminal_states

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op_001",
                "current_state": "authorized",
                "authorization_granted": True,
                "authorized_by": "admin_agent"
            }
        }


# ============================================================================
# API Request/Response Models
# ============================================================================


class ProposeOperationRequest(BaseModel):
    """Request to propose a new repository operation"""

    operation_type: RepoOperationType
    agent_id: str
    repo_path: str
    branch: str = "main"
    params: Dict[str, Any] = Field(default_factory=dict)
    requested_auth_level: AuthorizationLevel = AuthorizationLevel.NONE

    class Config:
        json_schema_extra = {
            "example": {
                "operation_type": "commit",
                "agent_id": "aro_agent",
                "repo_path": "/home/user/BRAiN",
                "branch": "claude/aro-phase-1",
                "params": {"message": "feat: Add ARO module"},
                "requested_auth_level": "commit"
            }
        }


class AuthorizeOperationRequest(BaseModel):
    """Request to authorize a proposed operation"""

    operation_id: str
    authorized_by: str
    grant_level: AuthorizationLevel

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op_001",
                "authorized_by": "admin_agent",
                "grant_level": "commit"
            }
        }


class ExecuteOperationRequest(BaseModel):
    """Request to execute an authorized operation"""

    operation_id: str

    class Config:
        json_schema_extra = {
            "example": {
                "operation_id": "op_001"
            }
        }


class OperationStatusResponse(BaseModel):
    """Response with operation status"""

    operation: RepoOperation
    can_execute: bool
    blocking_issues: List[str] = Field(default_factory=list)

    class Config:
        json_schema_extra = {
            "example": {
                "operation": {},
                "can_execute": True,
                "blocking_issues": []
            }
        }


class AROStats(BaseModel):
    """ARO system statistics"""

    total_operations: int
    operations_by_state: Dict[str, int]
    operations_by_type: Dict[str, int]
    total_audit_entries: int
    authorization_grant_rate: float
    validation_pass_rate: float
    safety_check_pass_rate: float

    class Config:
        json_schema_extra = {
            "example": {
                "total_operations": 100,
                "operations_by_state": {"completed": 80, "failed": 10, "denied": 10},
                "operations_by_type": {"commit": 60, "push": 20, "read_file": 20},
                "total_audit_entries": 500,
                "authorization_grant_rate": 0.9,
                "validation_pass_rate": 0.95,
                "safety_check_pass_rate": 0.98
            }
        }


class AROHealth(BaseModel):
    """ARO system health status"""

    status: str
    operational: bool
    audit_log_integrity: bool
    policy_engine_available: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "operational": True,
                "audit_log_integrity": True,
                "policy_engine_available": True
            }
        }


class AROInfo(BaseModel):
    """ARO system information"""

    name: str = "BRAiN Autonomous Repo Operator (ARO)"
    version: str = "1.0.0"
    phase: str = "Phase 1"
    description: str = "Strict governance and safety for repository operations"
    features: List[str] = Field(
        default_factory=lambda: [
            "State machine controlled operations",
            "Append-only audit logging",
            "Multi-level validation",
            "Safety checkpoints",
            "Policy engine integration",
            "Fail-closed design"
        ]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "BRAiN Autonomous Repo Operator (ARO)",
                "version": "1.0.0",
                "phase": "Phase 1"
            }
        }
