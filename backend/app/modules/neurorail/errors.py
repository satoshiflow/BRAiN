"""
NeuroRail Error Code Registry.

Centralized error codes for mechanical failures in the NeuroRail execution system.
Inspired by SGLang Model Gateway's error taxonomy.

Error Code Format: NR-E{number:03d}

Categories:
- NR-E001-NR-E099: Execution Errors (mechanical)
- NR-E100-NR-E199: Resource Errors
- NR-E200-NR-E299: Governance Errors
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

    # Resource Errors (NR-E100-NR-E199) - Mechanical
    RESOURCE_EXHAUSTED = "NR-E100"
    """System resource exhausted (memory, connections, queue)."""

    RATE_LIMIT_EXCEEDED = "NR-E101"
    """Rate limit exceeded for external service."""

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

    # Resource Errors
    NeuroRailErrorCode.RESOURCE_EXHAUSTED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": True,
        "severity": "warning",
        "message": "System resource exhausted",
    },
    NeuroRailErrorCode.RATE_LIMIT_EXCEEDED: {
        "category": ErrorCategory.MECHANICAL,
        "retriable": True,
        "severity": "info",
        "message": "Rate limit exceeded",
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
