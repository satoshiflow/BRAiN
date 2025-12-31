"""
NeuroRail Error Code Registry.

Centralized error codes for mechanical failures in the NeuroRail execution system.
Inspired by SGLang Model Gateway's error taxonomy.

Error Code Format: NR-E{number:03d}

Categories:
- NR-E001-NR-E099: Execution Errors (mechanical)
- NR-E100-NR-E109: Budget/Enforcement Errors (Phase 2)
- NR-E110-NR-E119: Manifest/Governance Errors (Phase 2)
- NR-E120-NR-E129: Decision/Resolution Errors (Phase 2)
- NR-E130-NR-E139: Shadowing/Activation Errors (Phase 2)
- NR-E140-NR-E149: Reflex System Errors (Phase 2)
- NR-E200-NR-E299: Governance Errors (reserved for Policy Engine)
- NR-E300-NR-E399: System Errors
"""

from enum import Enum
from typing import Optional, Dict, Any


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    MECHANICAL = "mechanical"  # Retriable errors (timeouts, network, resources)
    ETHICAL = "ethical"        # Non-retriable errors (policy violations, safety)
    SYSTEM = "system"          # Infrastructure errors


class NeuroRailErrorCode(str, Enum):
    """
    Centralized error codes for NeuroRail system.

    These codes are machine-readable and used for:
    - Error classification (mechanical vs ethical)
    - Retry decision logic
    - Audit trail consistency
    - Observability and alerting
    """

    # Execution Errors (NR-E001-NR-E099) - Mechanical
    EXEC_TIMEOUT = "NR-E001"
    """Execution exceeded timeout budget."""

    EXEC_OVERBUDGET = "NR-E002"
    """Execution exceeded resource budget (tokens/memory/cpu)."""

    RETRY_EXHAUSTED = "NR-E003"
    """All retry attempts exhausted for mechanical failure."""

    UPSTREAM_UNAVAILABLE = "NR-E004"
    """Upstream service (LLM, tool, API) unavailable."""

    BAD_RESPONSE_FORMAT = "NR-E005"
    """Upstream returned malformed or unexpected response."""

    POLICY_REFLEX_COOLDOWN = "NR-E006"
    """Job blocked by reflex system cooldown."""

    ORPHAN_KILLED = "NR-E007"
    """Job killed due to missing parent context (orphan protection)."""

    # Budget/Enforcement Errors (NR-E100-NR-E109) - Phase 2
    BUDGET_TIMEOUT_EXCEEDED = "NR-E100"
    """Execution exceeded timeout budget (hard limit)."""

    BUDGET_RETRY_EXHAUSTED = "NR-E101"
    """Retry budget exhausted (max retries reached)."""

    BUDGET_PARALLELISM_EXCEEDED = "NR-E102"
    """Parallelism budget exceeded (too many concurrent executions)."""

    BUDGET_COST_EXCEEDED = "NR-E103"
    """Cost budget exceeded (tokens/credits limit reached)."""

    BUDGET_TOKEN_EXCEEDED = "NR-E104"
    """LLM token budget exceeded."""

    # Manifest/Governance Errors (NR-E110-NR-E119) - Phase 2
    MANIFEST_NOT_FOUND = "NR-E110"
    """Requested manifest version not found."""

    MANIFEST_INVALID_SCHEMA = "NR-E111"
    """Manifest schema validation failed."""

    MANIFEST_HASH_MISMATCH = "NR-E112"
    """Manifest hash chain validation failed."""

    MANIFEST_DUPLICATE_VERSION = "NR-E113"
    """Manifest version already exists."""

    MANIFEST_RULE_CONFLICT = "NR-E114"
    """Manifest rule priority conflict (duplicate priorities)."""

    # Decision/Resolution Errors (NR-E120-NR-E129) - Phase 2
    DECISION_NO_RULE_MATCH = "NR-E120"
    """No manifest rule matched the job context."""

    DECISION_BUDGET_RESOLUTION_FAILED = "NR-E121"
    """Failed to resolve budget from manifest rules."""

    DECISION_INVALID_CONTEXT = "NR-E122"
    """Invalid job context provided for decision."""

    DECISION_PERSISTENCE_FAILED = "NR-E123"
    """Failed to persist decision to database."""

    # Shadowing/Activation Errors (NR-E130-NR-E139) - Phase 2
    SHADOW_EVALUATION_FAILED = "NR-E130"
    """Shadow manifest evaluation failed."""

    SHADOW_REPORT_INCOMPLETE = "NR-E131"
    """Shadow report has insufficient evaluation data."""

    ACTIVATION_GATE_BLOCKED = "NR-E132"
    """Manifest activation blocked by gate (explosion rate too high)."""

    ACTIVATION_ALREADY_ACTIVE = "NR-E133"
    """Cannot activate manifest that is already active."""

    SHADOW_MODE_REQUIRED = "NR-E134"
    """Operation requires manifest to be in shadow mode."""

    # Reflex System Errors (NR-E140-NR-E149) - Phase 2
    REFLEX_CIRCUIT_OPEN = "NR-E140"
    """Circuit breaker is open (failure threshold exceeded)."""

    REFLEX_TRIGGER_ACTIVATED = "NR-E141"
    """Reflex trigger activated (error rate/budget violation threshold)."""

    REFLEX_ACTION_FAILED = "NR-E142"
    """Reflex action execution failed."""

    REFLEX_LIFECYCLE_INVALID = "NR-E143"
    """Invalid lifecycle state transition requested."""

    # Governance Errors (NR-E200-NR-E299) - Ethical (handled by core, not NeuroRail)
    # Note: Ethical/policy violations are handled by Policy Engine, not NeuroRail
    # These codes are reserved for future governance-specific errors

    # System Errors (NR-E300-NR-E399) - System
    CIRCUIT_BREAKER_OPEN = "NR-E300"
    """Circuit breaker open for upstream service."""

    INVALID_STATE_TRANSITION = "NR-E301"
    """Attempted illegal state machine transition."""

    AUDIT_LOG_FAILURE = "NR-E302"
    """Failed to write to audit log (critical)."""

    TELEMETRY_FAILURE = "NR-E303"
    """Failed to record telemetry (non-critical)."""

    MISSING_TRACE_CONTEXT = "NR-E304"
    """Required trace context (mission_id, plan_id, etc.) missing."""


# Error Code Metadata
ERROR_METADATA: Dict[NeuroRailErrorCode, Dict[str, Any]] = {
    # Execution Errors
    NeuroRailErrorCode.EXEC_TIMEOUT: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,  # Already exhausted time budget
        "severity": "warning",
        "message": "Execution exceeded timeout budget",
    },
    NeuroRailErrorCode.EXEC_OVERBUDGET: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,  # Already exhausted resource budget
        "severity": "warning",
        "message": "Execution exceeded resource budget",
    },
    NeuroRailErrorCode.RETRY_EXHAUSTED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,  # Already exhausted retries
        "severity": "error",
        "message": "All retry attempts exhausted",
    },
    NeuroRailErrorCode.UPSTREAM_UNAVAILABLE: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": True,
        "severity": "warning",
        "message": "Upstream service unavailable",
    },
    NeuroRailErrorCode.BAD_RESPONSE_FORMAT: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": True,  # May be transient
        "severity": "warning",
        "message": "Upstream returned malformed response",
    },
    NeuroRailErrorCode.POLICY_REFLEX_COOLDOWN: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": True,  # Can retry after cooldown
        "severity": "info",
        "message": "Job blocked by reflex cooldown",
    },
    NeuroRailErrorCode.ORPHAN_KILLED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,
        "severity": "error",
        "message": "Job killed due to missing parent context",
    },

    # Budget/Enforcement Errors (Phase 2)
    NeuroRailErrorCode.BUDGET_TIMEOUT_EXCEEDED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,  # Already exceeded timeout budget
        "severity": "error",
        "message": "Execution exceeded timeout budget",
        "immune_alert": True,  # Alert immune system
    },
    NeuroRailErrorCode.BUDGET_RETRY_EXHAUSTED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,  # Already exhausted retries
        "severity": "error",
        "message": "Retry budget exhausted",
        "immune_alert": True,
    },
    NeuroRailErrorCode.BUDGET_PARALLELISM_EXCEEDED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": True,  # Can retry after capacity frees up
        "severity": "warning",
        "message": "Parallelism budget exceeded",
        "immune_alert": False,
    },
    NeuroRailErrorCode.BUDGET_COST_EXCEEDED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,  # Cost limit reached
        "severity": "error",
        "message": "Cost budget exceeded",
        "immune_alert": True,
    },
    NeuroRailErrorCode.BUDGET_TOKEN_EXCEEDED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,  # Token limit reached
        "severity": "warning",
        "message": "LLM token budget exceeded",
        "immune_alert": False,
    },

    # Manifest/Governance Errors (Phase 2)
    NeuroRailErrorCode.MANIFEST_NOT_FOUND: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "error",
        "message": "Manifest version not found",
        "immune_alert": True,  # Missing manifest is critical
    },
    NeuroRailErrorCode.MANIFEST_INVALID_SCHEMA: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "error",
        "message": "Manifest schema validation failed",
        "immune_alert": True,
    },
    NeuroRailErrorCode.MANIFEST_HASH_MISMATCH: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "critical",
        "message": "Manifest hash chain validation failed",
        "immune_alert": True,  # Hash mismatch is security issue
    },
    NeuroRailErrorCode.MANIFEST_DUPLICATE_VERSION: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "warning",
        "message": "Manifest version already exists",
        "immune_alert": False,
    },
    NeuroRailErrorCode.MANIFEST_RULE_CONFLICT: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "error",
        "message": "Manifest rule priority conflict",
        "immune_alert": False,
    },

    # Decision/Resolution Errors (Phase 2)
    NeuroRailErrorCode.DECISION_NO_RULE_MATCH: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,
        "severity": "warning",
        "message": "No manifest rule matched job context",
        "immune_alert": False,  # Fallback to default is acceptable
    },
    NeuroRailErrorCode.DECISION_BUDGET_RESOLUTION_FAILED: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "error",
        "message": "Failed to resolve budget from manifest",
        "immune_alert": True,
    },
    NeuroRailErrorCode.DECISION_INVALID_CONTEXT: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,
        "severity": "warning",
        "message": "Invalid job context for decision",
        "immune_alert": False,
    },
    NeuroRailErrorCode.DECISION_PERSISTENCE_FAILED: {
        "category": ErrorCategory.SYSTEM,
        "retriable": True,  # Database might recover
        "severity": "error",
        "message": "Failed to persist decision to database",
        "immune_alert": True,
    },

    # Shadowing/Activation Errors (Phase 2)
    NeuroRailErrorCode.SHADOW_EVALUATION_FAILED: {
        "category": ErrorCategory.SYSTEM,
        "retriable": True,
        "severity": "warning",
        "message": "Shadow manifest evaluation failed",
        "immune_alert": False,
    },
    NeuroRailErrorCode.SHADOW_REPORT_INCOMPLETE: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "warning",
        "message": "Shadow report has insufficient data",
        "immune_alert": False,
    },
    NeuroRailErrorCode.ACTIVATION_GATE_BLOCKED: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "warning",
        "message": "Manifest activation blocked by gate",
        "immune_alert": True,  # Gate block is important
    },
    NeuroRailErrorCode.ACTIVATION_ALREADY_ACTIVE: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "info",
        "message": "Manifest already active",
        "immune_alert": False,
    },
    NeuroRailErrorCode.SHADOW_MODE_REQUIRED: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "warning",
        "message": "Operation requires shadow mode",
        "immune_alert": False,
    },

    # Reflex System Errors (Phase 2)
    NeuroRailErrorCode.REFLEX_CIRCUIT_OPEN: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": True,  # Can retry after recovery timeout
        "severity": "warning",
        "message": "Circuit breaker is open",
        "immune_alert": True,  # Important for cascading failure prevention
    },
    NeuroRailErrorCode.REFLEX_TRIGGER_ACTIVATED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": False,  # Trigger indicates threshold exceeded
        "severity": "warning",
        "message": "Reflex trigger activated",
        "immune_alert": True,
    },
    NeuroRailErrorCode.REFLEX_ACTION_FAILED: {
        "category": ErrorCategory.SYSTEM,
        "retriable": True,
        "severity": "error",
        "message": "Reflex action execution failed",
        "immune_alert": True,
    },
    NeuroRailErrorCode.REFLEX_LIFECYCLE_INVALID: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "error",
        "message": "Invalid lifecycle state transition",
        "immune_alert": False,
    },

    # System Errors
    NeuroRailErrorCode.CIRCUIT_BREAKER_OPEN: {
        "category": ErrorCategory.SYSTEM,
        "retriable": True,  # Can retry after recovery timeout
        "severity": "warning",
        "message": "Circuit breaker open",
    },
    NeuroRailErrorCode.INVALID_STATE_TRANSITION: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "error",
        "message": "Invalid state machine transition",
    },
    NeuroRailErrorCode.AUDIT_LOG_FAILURE: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "critical",
        "message": "Failed to write audit log",
    },
    NeuroRailErrorCode.TELEMETRY_FAILURE: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "warning",
        "message": "Failed to record telemetry",
    },
    NeuroRailErrorCode.MISSING_TRACE_CONTEXT: {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "error",
        "message": "Missing required trace context",
    },
}


class NeuroRailError(Exception):
    """Base exception for all NeuroRail errors."""

    def __init__(
        self,
        code: NeuroRailErrorCode,
        message: Optional[str] = None,
        *,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        self.code = code
        self.metadata = ERROR_METADATA.get(code, {})
        self.category = self.metadata.get("category", ErrorCategory.SYSTEM)
        self.retriable = self.metadata.get("retriable", False)
        self.severity = self.metadata.get("severity", "error")

        # Use custom message or default from metadata
        self.message = message or self.metadata.get("message", str(code))

        super().__init__(self.message)
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        return {
            "code": self.code,
            "category": self.category,
            "retriable": self.retriable,
            "severity": self.severity,
            "message": self.message,
            "details": self.details,
        }


class ExecutionTimeoutError(NeuroRailError):
    """Raised when execution exceeds timeout budget."""

    def __init__(
        self,
        timeout_ms: float,
        elapsed_ms: float,
        **kwargs
    ) -> None:
        details = {
            "timeout_ms": timeout_ms,
            "elapsed_ms": elapsed_ms,
            **kwargs.get("details", {}),
        }
        super().__init__(
            NeuroRailErrorCode.EXEC_TIMEOUT,
            message=f"Execution timeout: {elapsed_ms}ms > {timeout_ms}ms",
            details=details,
            cause=kwargs.get("cause"),
        )


class BudgetExceededError(NeuroRailError):
    """Raised when execution exceeds resource budget."""

    def __init__(
        self,
        resource_type: str,
        limit: float,
        consumed: float,
        **kwargs
    ) -> None:
        details = {
            "resource_type": resource_type,
            "limit": limit,
            "consumed": consumed,
            **kwargs.get("details", {}),
        }
        super().__init__(
            NeuroRailErrorCode.EXEC_OVERBUDGET,
            message=f"Budget exceeded for {resource_type}: {consumed} > {limit}",
            details=details,
            cause=kwargs.get("cause"),
        )


class RetryExhaustedError(NeuroRailError):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self,
        attempts: int,
        last_error: Optional[Exception] = None,
        **kwargs
    ) -> None:
        details = {
            "attempts": attempts,
            "last_error": str(last_error) if last_error else None,
            **kwargs.get("details", {}),
        }
        super().__init__(
            NeuroRailErrorCode.RETRY_EXHAUSTED,
            message=f"All {attempts} retry attempts exhausted",
            details=details,
            cause=last_error or kwargs.get("cause"),
        )


class OrphanKilledError(NeuroRailError):
    """Raised when job is killed due to missing parent context."""

    def __init__(
        self,
        job_id: str,
        missing_context: str,
        **kwargs
    ) -> None:
        details = {
            "job_id": job_id,
            "missing_context": missing_context,
            **kwargs.get("details", {}),
        }
        super().__init__(
            NeuroRailErrorCode.ORPHAN_KILLED,
            message=f"Job {job_id} killed: missing {missing_context}",
            details=details,
            cause=kwargs.get("cause"),
        )


# ============================================================================
# Phase 2 Exception Classes
# ============================================================================

class ManifestNotFoundError(NeuroRailError):
    """Raised when requested manifest version is not found."""

    def __init__(self, version: str, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.MANIFEST_NOT_FOUND,
            message=f"Manifest version '{version}' not found",
            details={"version": version, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class ManifestInvalidSchemaError(NeuroRailError):
    """Raised when manifest schema validation fails."""

    def __init__(self, validation_errors: list, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.MANIFEST_INVALID_SCHEMA,
            message=f"Manifest schema validation failed: {len(validation_errors)} errors",
            details={"validation_errors": validation_errors, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class ManifestHashMismatchError(NeuroRailError):
    """Raised when manifest hash chain validation fails."""

    def __init__(self, expected_hash: str, actual_hash: str, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.MANIFEST_HASH_MISMATCH,
            message=f"Manifest hash mismatch: expected {expected_hash}, got {actual_hash}",
            details={"expected_hash": expected_hash, "actual_hash": actual_hash, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class DecisionBudgetResolutionError(NeuroRailError):
    """Raised when budget resolution from manifest fails."""

    def __init__(self, job_type: str, reason: str, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.DECISION_BUDGET_RESOLUTION_FAILED,
            message=f"Failed to resolve budget for {job_type}: {reason}",
            details={"job_type": job_type, "reason": reason, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class ActivationGateBlockedError(NeuroRailError):
    """Raised when manifest activation is blocked by gate."""

    def __init__(self, version: str, reason: str, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.ACTIVATION_GATE_BLOCKED,
            message=f"Activation of manifest '{version}' blocked: {reason}",
            details={"version": version, "reason": reason, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class BudgetTimeoutExceededError(NeuroRailError):
    """Raised when execution exceeds timeout budget (Phase 2 enforcement)."""

    def __init__(self, timeout_ms: float, elapsed_ms: float, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.BUDGET_TIMEOUT_EXCEEDED,
            message=f"Timeout budget exceeded: {elapsed_ms}ms > {timeout_ms}ms",
            details={"timeout_ms": timeout_ms, "elapsed_ms": elapsed_ms, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class BudgetRetryExhaustedError(NeuroRailError):
    """Raised when retry budget is exhausted (Phase 2 enforcement)."""

    def __init__(self, max_retries: int, last_error: Optional[Exception] = None, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.BUDGET_RETRY_EXHAUSTED,
            message=f"Retry budget exhausted: {max_retries} attempts",
            details={"max_retries": max_retries, "last_error": str(last_error) if last_error else None, **kwargs.get("details", {})},
            cause=last_error or kwargs.get("cause"),
        )


class BudgetParallelismExceededError(NeuroRailError):
    """Raised when parallelism budget is exceeded."""

    def __init__(self, limit: int, current: int, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.BUDGET_PARALLELISM_EXCEEDED,
            message=f"Parallelism budget exceeded: {current} > {limit}",
            details={"limit": limit, "current": current, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class BudgetCostExceededError(NeuroRailError):
    """Raised when cost budget is exceeded."""

    def __init__(self, limit: float, consumed: float, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.BUDGET_COST_EXCEEDED,
            message=f"Cost budget exceeded: {consumed} > {limit} credits",
            details={"limit": limit, "consumed": consumed, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class ReflexCircuitOpenError(NeuroRailError):
    """Raised when circuit breaker is open."""

    def __init__(self, circuit_id: str, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.REFLEX_CIRCUIT_OPEN,
            message=f"Circuit {circuit_id} is OPEN (failure threshold exceeded)",
            details={"circuit_id": circuit_id, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class ReflexTriggerActivatedError(NeuroRailError):
    """Raised when reflex trigger is activated."""

    def __init__(self, trigger_type: str, reason: str, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.REFLEX_TRIGGER_ACTIVATED,
            message=f"Reflex trigger activated: {trigger_type} - {reason}",
            details={"trigger_type": trigger_type, "reason": reason, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class ReflexActionFailedError(NeuroRailError):
    """Raised when reflex action execution fails."""

    def __init__(self, action_type: str, reason: str, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.REFLEX_ACTION_FAILED,
            message=f"Reflex action {action_type} failed: {reason}",
            details={"action_type": action_type, "reason": reason, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


class ReflexLifecycleInvalidError(NeuroRailError):
    """Raised when invalid lifecycle state transition is requested."""

    def __init__(self, from_state: str, to_state: str, **kwargs) -> None:
        super().__init__(
            NeuroRailErrorCode.REFLEX_LIFECYCLE_INVALID,
            message=f"Invalid lifecycle transition: {from_state} → {to_state}",
            details={"from_state": from_state, "to_state": to_state, **kwargs.get("details", {})},
            cause=kwargs.get("cause"),
        )


def get_error_info(code: NeuroRailErrorCode) -> Dict[str, Any]:
    """Get metadata for an error code."""
    return ERROR_METADATA.get(code, {
        "category": ErrorCategory.SYSTEM,
        "retriable": False,
        "severity": "error",
        "message": str(code),
    })


def is_retriable(code: NeuroRailErrorCode) -> bool:
    """Check if error code represents a retriable error."""
    return ERROR_METADATA.get(code, {}).get("retriable", False)


def get_category(code: NeuroRailErrorCode) -> ErrorCategory:
    """Get category for error code."""
    return ERROR_METADATA.get(code, {}).get("category", ErrorCategory.SYSTEM)


def should_alert_immune(code: NeuroRailErrorCode) -> bool:
    """
    Check if error code should trigger immune system alert.

    Returns:
        True if immune system should be alerted (critical errors)
    """
    return ERROR_METADATA.get(code, {}).get("immune_alert", False)
