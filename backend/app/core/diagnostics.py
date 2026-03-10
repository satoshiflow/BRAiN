"""Runtime Diagnostics & Error Framework

Standardized failure taxonomy, correlation, and provenance for BRAiN runtime.

Sprint C deliverable from BRAIN_HARDENING_ROADMAP.md
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Failure Taxonomy
# ============================================================================


class FailureClass(str, Enum):
    """Standardized failure classification for runtime diagnostics."""

    REQUEST_FAILURE = "request_failure"
    EXECUTION_FAILURE = "execution_failure"
    INTEGRATION_FAILURE = "integration_failure"
    GOVERNANCE_FAILURE = "governance_failure"
    OBSERVABILITY_FAILURE = "observability_failure"
    LEARNING_PIPELINE_FAILURE = "learning_pipeline_failure"


class Severity(str, Enum):
    """Failure severity levels aligned with observability standards."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Retryability(str, Enum):
    """Retryability classification for recovery policy routing."""

    SAFE_RETRY = "safe_retry"  # Can retry without side effects
    IDEMPOTENT_RETRY = "idempotent_retry"  # Safe if idempotency key provided
    UNSAFE_RETRY = "unsafe_retry"  # May cause side effects, require manual approval
    NO_RETRY = "no_retry"  # Not retryable (validation, auth, etc.)


class OperatorAction(str, Enum):
    """Recommended operator action for incident triage."""

    NONE = "none"  # Auto-recoverable or informational
    MONITOR = "monitor"  # Watch for recurrence patterns
    INVESTIGATE = "investigate"  # Manual diagnostics required
    ESCALATE = "escalate"  # Immediate attention required
    REMEDIATE = "remediate"  # Manual fix required


# ============================================================================
# Failure Codes by Class
# ============================================================================


class RequestFailureCode(str, Enum):
    """Request-level failure codes."""

    VALIDATION_ERROR = "validation_error"
    AUTH_MISSING = "auth_missing"
    AUTH_INVALID = "auth_invalid"
    AUTH_EXPIRED = "auth_expired"
    FORBIDDEN = "forbidden"
    RATE_LIMITED = "rate_limited"
    MALFORMED_INPUT = "malformed_input"
    RESOURCE_NOT_FOUND = "resource_not_found"
    CONFLICT = "conflict"
    PRECONDITION_FAILED = "precondition_failed"


class ExecutionFailureCode(str, Enum):
    """Execution-level failure codes."""

    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    SKILL_EXECUTION_ERROR = "skill_execution_error"
    WORKER_CRASH = "worker_crash"
    QUEUE_OVERFLOW = "queue_overflow"
    CIRCUIT_OPEN = "circuit_open"
    UNHANDLED_EXCEPTION = "unhandled_exception"


class IntegrationFailureCode(str, Enum):
    """Integration/external dependency failure codes."""

    DATABASE_ERROR = "database_error"
    REDIS_ERROR = "redis_error"
    EVENTSTREAM_ERROR = "eventstream_error"
    EXTERNAL_API_ERROR = "external_api_error"
    PROVIDER_ERROR = "provider_error"
    NETWORK_ERROR = "network_error"
    SERIALIZATION_ERROR = "serialization_error"


class GovernanceFailureCode(str, Enum):
    """Governance/policy violation codes."""

    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_DENIED = "approval_denied"
    POLICY_VIOLATION = "policy_violation"
    QUOTA_EXCEEDED = "quota_exceeded"
    TENANT_ISOLATION_VIOLATION = "tenant_isolation_violation"
    CAPABILITY_MISSING = "capability_missing"
    LIFECYCLE_VIOLATION = "lifecycle_violation"


class ObservabilityFailureCode(str, Enum):
    """Observability/audit pipeline failure codes."""

    AUDIT_WRITE_FAILED = "audit_write_failed"
    EVENT_PUBLISH_FAILED = "event_publish_failed"
    SIGNAL_INGESTION_FAILED = "signal_ingestion_failed"
    CORRELATION_MISSING = "correlation_missing"
    PROVENANCE_LINK_BROKEN = "provenance_link_broken"
    TELEMETRY_DROPPED = "telemetry_dropped"


class LearningPipelineFailureCode(str, Enum):
    """Learning layer pipeline failure codes."""

    EXPERIENCE_CAPTURE_FAILED = "experience_capture_failed"
    INSIGHT_EXTRACTION_FAILED = "insight_extraction_failed"
    PATTERN_CANDIDATE_FAILED = "pattern_candidate_failed"
    CONSOLIDATION_FAILED = "consolidation_failed"
    EVOLUTION_SELECTION_FAILED = "evolution_selection_failed"
    DELIBERATION_FAILED = "deliberation_failed"
    DISCOVERY_FAILED = "discovery_failed"
    ECONOMY_SIGNAL_FAILED = "economy_signal_failed"


# ============================================================================
# Standard Failure Envelope
# ============================================================================


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class FailureRecord(BaseModel):
    """Standard failure envelope for BRAiN runtime diagnostics.

    All runtime failure paths should emit FailureRecord instances.
    This provides correlation, provenance, classification, and operator triage signals.
    """

    # Identity & Context
    failure_id: str = Field(default_factory=lambda: f"fail_{uuid.uuid4().hex[:16]}")
    tenant_id: str = Field(..., description="Tenant context for isolation")
    correlation_id: Optional[str] = Field(None, description="Request/execution correlation ID")

    # Execution Context
    skill_run_id: Optional[str] = Field(None, description="Associated SkillRun ID if applicable")
    mission_id: Optional[str] = Field(None, description="Associated Mission ID if applicable")
    entity: str = Field(..., description="Failing entity (module, service, worker, etc.)")

    # Classification
    failure_class: FailureClass = Field(..., description="High-level failure taxonomy")
    failure_code: str = Field(..., description="Specific failure code from taxonomy")
    severity: Severity = Field(..., description="Severity level")
    retryability: Retryability = Field(..., description="Retry safety classification")
    operator_action: OperatorAction = Field(..., description="Recommended operator action")

    # Diagnostics
    message: str = Field(..., description="Human-readable failure summary")
    technical_details: dict[str, Any] = Field(default_factory=dict, description="Technical context (redacted)")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available (redacted)")

    # Linkage
    audit_ref: Optional[str] = Field(None, description="Reference to audit record")
    event_ref: Optional[str] = Field(None, description="Reference to published event")
    provenance_refs: list[str] = Field(default_factory=list, description="Links to source records (ExperienceRecord, etc.)")

    # Metadata
    occurred_at: str = Field(default_factory=_utcnow_iso)
    captured_at: str = Field(default_factory=_utcnow_iso)

    def to_sanitized_dict(self) -> dict[str, Any]:
        """Return sanitized failure record safe for client responses.

        Strips stack_trace and redacts technical_details.
        """
        data = self.model_dump()
        data.pop("stack_trace", None)
        data["technical_details"] = {"redacted": True}
        return data

    def get_redaction_hash(self) -> str:
        """Generate hash for deduplication and privacy-preserving aggregation."""
        canonical = json.dumps(
            {
                "tenant_id": self.tenant_id,
                "entity": self.entity,
                "failure_class": self.failure_class,
                "failure_code": self.failure_code,
                "message": self.message,
            },
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ============================================================================
# Correlation ID Propagation Helpers
# ============================================================================


def extract_correlation_id(headers: dict[str, str] | None) -> Optional[str]:
    """Extract correlation ID from HTTP headers or generate new one.

    Supports standard X-Correlation-ID and X-Request-ID headers.
    """
    if not headers:
        return generate_correlation_id()

    for key in ("x-correlation-id", "x-request-id"):
        value = headers.get(key) or headers.get(key.upper())
        if value:
            return str(value).strip()

    return generate_correlation_id()


def generate_correlation_id() -> str:
    """Generate new correlation ID."""
    return f"corr_{uuid.uuid4().hex[:20]}"


def propagate_correlation_id(
    *,
    request_correlation_id: Optional[str],
    skill_run_id: Optional[str] = None,
    mission_id: Optional[str] = None,
) -> str:
    """Ensure correlation ID exists and is properly propagated through execution layers.

    Priority:
    1. request_correlation_id if provided
    2. Derive from skill_run_id if provided
    3. Derive from mission_id if provided
    4. Generate new correlation_id
    """
    if request_correlation_id:
        return request_correlation_id
    if skill_run_id:
        return f"corr_skill_{skill_run_id}"
    if mission_id:
        return f"corr_mission_{mission_id}"
    return generate_correlation_id()


# ============================================================================
# Provenance Linking Utilities
# ============================================================================


class ProvenanceRef(BaseModel):
    """Structured provenance reference for failure → source record linkage."""

    ref_type: str = Field(..., description="Type: experience_record, insight_candidate, pattern_candidate, etc.")
    ref_id: str = Field(..., description="ID of source record")
    correlation_id: Optional[str] = Field(None, description="Correlation ID if available")

    def to_string(self) -> str:
        """Serialize to compact string format: type:id[:correlation_id]"""
        if self.correlation_id:
            return f"{self.ref_type}:{self.ref_id}:{self.correlation_id}"
        return f"{self.ref_type}:{self.ref_id}"

    @classmethod
    def from_string(cls, s: str) -> Optional[ProvenanceRef]:
        """Parse compact string format back to ProvenanceRef."""
        parts = s.split(":")
        if len(parts) < 2:
            return None
        ref_type, ref_id = parts[0], parts[1]
        correlation_id = parts[2] if len(parts) > 2 else None
        return cls(ref_type=ref_type, ref_id=ref_id, correlation_id=correlation_id)


def build_provenance_ref(*, ref_type: str, ref_id: str, correlation_id: Optional[str] = None) -> str:
    """Build provenance reference string."""
    return ProvenanceRef(ref_type=ref_type, ref_id=ref_id, correlation_id=correlation_id).to_string()


def parse_provenance_refs(refs: list[str]) -> list[ProvenanceRef]:
    """Parse list of provenance reference strings into structured objects."""
    parsed = []
    for ref_str in refs:
        ref = ProvenanceRef.from_string(ref_str)
        if ref:
            parsed.append(ref)
    return parsed


# ============================================================================
# Redaction Utilities
# ============================================================================

# Patterns that should be redacted from technical_details and stack traces
REDACTION_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE), "Bearer [REDACTED]"),
    (re.compile(r"api[_-]?key['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE), "api_key=[REDACTED]"),
    (re.compile(r"password['\"]?\s*[:=]\s*['\"]?[^\s'\"]+", re.IGNORECASE), "password=[REDACTED]"),
    (re.compile(r"token['\"]?\s*[:=]\s*['\"]?[\w\-\.]+", re.IGNORECASE), "token=[REDACTED]"),
    (re.compile(r"secret['\"]?\s*[:=]\s*['\"]?[\w\-]+", re.IGNORECASE), "secret=[REDACTED]"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL_REDACTED]"),
]


def redact_sensitive_data(text: str) -> str:
    """Apply redaction patterns to text (stack traces, logs, etc.)."""
    if not text:
        return text
    for pattern, replacement in REDACTION_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact_dict(data: dict[str, Any], keys_to_redact: set[str] | None = None) -> dict[str, Any]:
    """Recursively redact sensitive keys from dictionary.

    Args:
        data: Dictionary to redact
        keys_to_redact: Set of key names to redact (default: common sensitive keys)

    Returns:
        Redacted dictionary copy
    """
    if keys_to_redact is None:
        keys_to_redact = {"password", "token", "api_key", "secret", "authorization", "auth"}

    redacted = {}
    for key, value in data.items():
        if key.lower() in keys_to_redact:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_dict(value, keys_to_redact)
        elif isinstance(value, list):
            redacted[key] = [redact_dict(v, keys_to_redact) if isinstance(v, dict) else v for v in value]
        elif isinstance(value, str):
            redacted[key] = redact_sensitive_data(value)
        else:
            redacted[key] = value
    return redacted


# ============================================================================
# Failure Record Builder
# ============================================================================


def build_failure_record(
    *,
    tenant_id: str,
    entity: str,
    failure_class: FailureClass,
    failure_code: str,
    severity: Severity,
    message: str,
    correlation_id: Optional[str] = None,
    skill_run_id: Optional[str] = None,
    mission_id: Optional[str] = None,
    retryability: Retryability = Retryability.UNSAFE_RETRY,
    operator_action: OperatorAction = OperatorAction.INVESTIGATE,
    technical_details: dict[str, Any] | None = None,
    stack_trace: Optional[str] = None,
    audit_ref: Optional[str] = None,
    event_ref: Optional[str] = None,
    provenance_refs: list[str] | None = None,
) -> FailureRecord:
    """Build a standardized FailureRecord with proper redaction and defaults.

    This is the canonical factory for creating failure records across the backend.
    """
    # Ensure correlation ID
    final_correlation_id = propagate_correlation_id(
        request_correlation_id=correlation_id,
        skill_run_id=skill_run_id,
        mission_id=mission_id,
    )

    # Redact technical details
    redacted_details = redact_dict(technical_details) if technical_details else {}

    # Redact stack trace
    redacted_stack = redact_sensitive_data(stack_trace) if stack_trace else None

    return FailureRecord(
        tenant_id=tenant_id,
        correlation_id=final_correlation_id,
        skill_run_id=skill_run_id,
        mission_id=mission_id,
        entity=entity,
        failure_class=failure_class,
        failure_code=failure_code,
        severity=severity,
        retryability=retryability,
        operator_action=operator_action,
        message=message,
        technical_details=redacted_details,
        stack_trace=redacted_stack,
        audit_ref=audit_ref,
        event_ref=event_ref,
        provenance_refs=provenance_refs or [],
    )
