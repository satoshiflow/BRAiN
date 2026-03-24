"""
Test Suite for Runtime Diagnostics & Error Framework

Tests for:
- Failure taxonomy and classification
- FailureRecord creation and validation
- Correlation ID propagation
- Provenance linking
- Redaction (security)
- Incident timeline API

Sprint C deliverable from BRAIN_HARDENING_ROADMAP.md
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.core.diagnostics import (
    ExecutionFailureCode,
    FailureClass,
    FailureRecord,
    GovernanceFailureCode,
    IntegrationFailureCode,
    LearningPipelineFailureCode,
    ObservabilityFailureCode,
    OperatorAction,
    ProvenanceRef,
    RequestFailureCode,
    Retryability,
    Severity,
    build_failure_record,
    build_provenance_ref,
    extract_correlation_id,
    generate_correlation_id,
    parse_provenance_refs,
    propagate_correlation_id,
    redact_dict,
    redact_sensitive_data,
)


# ============================================================================
# Failure Taxonomy Tests
# ============================================================================


class TestFailureTaxonomy:
    """Test failure taxonomy enumerations."""

    def test_failure_classes_complete(self):
        """All six failure classes are defined."""
        assert FailureClass.REQUEST_FAILURE == "request_failure"
        assert FailureClass.EXECUTION_FAILURE == "execution_failure"
        assert FailureClass.INTEGRATION_FAILURE == "integration_failure"
        assert FailureClass.GOVERNANCE_FAILURE == "governance_failure"
        assert FailureClass.OBSERVABILITY_FAILURE == "observability_failure"
        assert FailureClass.LEARNING_PIPELINE_FAILURE == "learning_pipeline_failure"

    def test_severity_levels(self):
        """Severity levels are defined."""
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.ERROR == "error"
        assert Severity.CRITICAL == "critical"

    def test_retryability_classifications(self):
        """Retryability classifications are defined."""
        assert Retryability.SAFE_RETRY == "safe_retry"
        assert Retryability.IDEMPOTENT_RETRY == "idempotent_retry"
        assert Retryability.UNSAFE_RETRY == "unsafe_retry"
        assert Retryability.NO_RETRY == "no_retry"

    def test_operator_actions(self):
        """Operator actions are defined."""
        assert OperatorAction.NONE == "none"
        assert OperatorAction.MONITOR == "monitor"
        assert OperatorAction.INVESTIGATE == "investigate"
        assert OperatorAction.ESCALATE == "escalate"
        assert OperatorAction.REMEDIATE == "remediate"

    def test_request_failure_codes(self):
        """Request failure codes are defined."""
        assert RequestFailureCode.VALIDATION_ERROR == "validation_error"
        assert RequestFailureCode.AUTH_MISSING == "auth_missing"
        assert RequestFailureCode.AUTH_INVALID == "auth_invalid"
        assert RequestFailureCode.FORBIDDEN == "forbidden"
        assert RequestFailureCode.RATE_LIMITED == "rate_limited"

    def test_execution_failure_codes(self):
        """Execution failure codes are defined."""
        assert ExecutionFailureCode.TIMEOUT == "timeout"
        assert ExecutionFailureCode.RESOURCE_EXHAUSTED == "resource_exhausted"
        assert ExecutionFailureCode.SKILL_EXECUTION_ERROR == "skill_execution_error"
        assert ExecutionFailureCode.UNHANDLED_EXCEPTION == "unhandled_exception"

    def test_integration_failure_codes(self):
        """Integration failure codes are defined."""
        assert IntegrationFailureCode.DATABASE_ERROR == "database_error"
        assert IntegrationFailureCode.REDIS_ERROR == "redis_error"
        assert IntegrationFailureCode.EVENTSTREAM_ERROR == "eventstream_error"
        assert IntegrationFailureCode.EXTERNAL_API_ERROR == "external_api_error"

    def test_governance_failure_codes(self):
        """Governance failure codes are defined."""
        assert GovernanceFailureCode.APPROVAL_REQUIRED == "approval_required"
        assert GovernanceFailureCode.APPROVAL_DENIED == "approval_denied"
        assert GovernanceFailureCode.POLICY_VIOLATION == "policy_violation"
        assert GovernanceFailureCode.QUOTA_EXCEEDED == "quota_exceeded"

    def test_observability_failure_codes(self):
        """Observability failure codes are defined."""
        assert ObservabilityFailureCode.AUDIT_WRITE_FAILED == "audit_write_failed"
        assert ObservabilityFailureCode.EVENT_PUBLISH_FAILED == "event_publish_failed"
        assert ObservabilityFailureCode.CORRELATION_MISSING == "correlation_missing"
        assert ObservabilityFailureCode.PROVENANCE_LINK_BROKEN == "provenance_link_broken"

    def test_learning_pipeline_failure_codes(self):
        """Learning pipeline failure codes are defined."""
        assert LearningPipelineFailureCode.EXPERIENCE_CAPTURE_FAILED == "experience_capture_failed"
        assert LearningPipelineFailureCode.INSIGHT_EXTRACTION_FAILED == "insight_extraction_failed"
        assert LearningPipelineFailureCode.PATTERN_CANDIDATE_FAILED == "pattern_candidate_failed"
        assert LearningPipelineFailureCode.CONSOLIDATION_FAILED == "consolidation_failed"


# ============================================================================
# FailureRecord Tests
# ============================================================================


class TestFailureRecord:
    """Test FailureRecord creation, validation, and serialization."""

    def test_create_minimal_failure_record(self):
        """Create failure record with minimal required fields."""
        record = FailureRecord(
            tenant_id="tenant_xyz",
            entity="test_module",
            failure_class=FailureClass.REQUEST_FAILURE,
            failure_code=RequestFailureCode.VALIDATION_ERROR,
            severity=Severity.WARNING,
            message="Test validation error",
            retryability=Retryability.NO_RETRY,
            operator_action=OperatorAction.NONE,
        )

        assert record.tenant_id == "tenant_xyz"
        assert record.entity == "test_module"
        assert record.failure_class == FailureClass.REQUEST_FAILURE
        assert record.failure_code == RequestFailureCode.VALIDATION_ERROR
        assert record.severity == Severity.WARNING
        assert record.message == "Test validation error"
        assert record.retryability == Retryability.NO_RETRY
        assert record.operator_action == OperatorAction.NONE
        assert record.failure_id.startswith("fail_")
        assert record.occurred_at is not None

    def test_create_full_failure_record(self):
        """Create failure record with all optional fields."""
        record = FailureRecord(
            tenant_id="tenant_xyz",
            correlation_id="corr_abc123",
            skill_run_id="run_def456",
            mission_id="mission_ghi789",
            entity="skill_engine",
            failure_class=FailureClass.EXECUTION_FAILURE,
            failure_code=ExecutionFailureCode.TIMEOUT,
            severity=Severity.ERROR,
            message="Skill execution timed out",
            retryability=Retryability.SAFE_RETRY,
            operator_action=OperatorAction.MONITOR,
            technical_details={"timeout_seconds": 300},
            stack_trace="Traceback (most recent call last):\n  ...",
            audit_ref="audit_123",
            event_ref="event_456",
            provenance_refs=["experience_record:exp_789"],
        )

        assert record.correlation_id == "corr_abc123"
        assert record.skill_run_id == "run_def456"
        assert record.mission_id == "mission_ghi789"
        assert record.technical_details == {"timeout_seconds": 300}
        assert record.stack_trace == "Traceback (most recent call last):\n  ..."
        assert record.audit_ref == "audit_123"
        assert record.event_ref == "event_456"
        assert record.provenance_refs == ["experience_record:exp_789"]

    def test_failure_record_to_sanitized_dict(self):
        """to_sanitized_dict removes sensitive fields."""
        record = FailureRecord(
            tenant_id="tenant_xyz",
            entity="test_module",
            failure_class=FailureClass.EXECUTION_FAILURE,
            failure_code=ExecutionFailureCode.UNHANDLED_EXCEPTION,
            severity=Severity.CRITICAL,
            message="Unhandled exception occurred",
            retryability=Retryability.UNSAFE_RETRY,
            operator_action=OperatorAction.ESCALATE,
            technical_details={"error": "details"},
            stack_trace="sensitive stack trace",
        )

        sanitized = record.to_sanitized_dict()
        assert "stack_trace" not in sanitized
        assert sanitized["technical_details"] == {"redacted": True}
        assert sanitized["message"] == "Unhandled exception occurred"
        assert sanitized["severity"] == "critical"

    def test_failure_record_get_redaction_hash(self):
        """get_redaction_hash produces consistent hash for deduplication."""
        record1 = FailureRecord(
            tenant_id="tenant_xyz",
            entity="test_module",
            failure_class=FailureClass.REQUEST_FAILURE,
            failure_code=RequestFailureCode.VALIDATION_ERROR,
            severity=Severity.WARNING,
            message="Validation failed",
            retryability=Retryability.NO_RETRY,
            operator_action=OperatorAction.NONE,
        )

        record2 = FailureRecord(
            tenant_id="tenant_xyz",
            entity="test_module",
            failure_class=FailureClass.REQUEST_FAILURE,
            failure_code=RequestFailureCode.VALIDATION_ERROR,
            severity=Severity.WARNING,
            message="Validation failed",
            retryability=Retryability.NO_RETRY,
            operator_action=OperatorAction.NONE,
            correlation_id="different_correlation_id",
        )

        # Same hash despite different correlation_id
        assert record1.get_redaction_hash() == record2.get_redaction_hash()

    def test_build_failure_record_factory(self):
        """build_failure_record factory produces valid FailureRecord."""
        record = build_failure_record(
            tenant_id="tenant_xyz",
            entity="skill_engine",
            failure_class=FailureClass.EXECUTION_FAILURE,
            failure_code=ExecutionFailureCode.TIMEOUT,
            severity=Severity.ERROR,
            message="Timeout occurred",
            correlation_id="corr_abc",
            retryability=Retryability.SAFE_RETRY,
            operator_action=OperatorAction.MONITOR,
        )

        assert isinstance(record, FailureRecord)
        assert record.tenant_id == "tenant_xyz"
        assert record.correlation_id == "corr_abc"


# ============================================================================
# Correlation ID Tests
# ============================================================================


class TestCorrelationID:
    """Test correlation ID generation and propagation."""

    def test_generate_correlation_id(self):
        """generate_correlation_id produces valid ID."""
        corr_id = generate_correlation_id()
        assert corr_id.startswith("corr_")
        assert len(corr_id) > 10

    def test_extract_correlation_id_from_headers(self):
        """extract_correlation_id extracts from standard headers."""
        headers = {"x-correlation-id": "corr_from_header"}
        corr_id = extract_correlation_id(headers)
        assert corr_id == "corr_from_header"

    def test_extract_correlation_id_from_request_id(self):
        """extract_correlation_id extracts from X-Request-ID."""
        headers = {"x-request-id": "req_123"}
        corr_id = extract_correlation_id(headers)
        assert corr_id == "req_123"

    def test_extract_correlation_id_generates_when_missing(self):
        """extract_correlation_id generates new ID when missing."""
        headers = {}
        corr_id = extract_correlation_id(headers)
        assert corr_id.startswith("corr_")

    def test_propagate_correlation_id_uses_request_id(self):
        """propagate_correlation_id prefers request_correlation_id."""
        corr_id = propagate_correlation_id(
            request_correlation_id="corr_request",
            skill_run_id="run_123",
            mission_id="mission_456",
        )
        assert corr_id == "corr_request"

    def test_propagate_correlation_id_derives_from_skill_run(self):
        """propagate_correlation_id derives from skill_run_id."""
        corr_id = propagate_correlation_id(
            request_correlation_id=None,
            skill_run_id="run_123",
            mission_id="mission_456",
        )
        assert corr_id == "corr_skill_run_123"

    def test_propagate_correlation_id_derives_from_mission(self):
        """propagate_correlation_id derives from mission_id."""
        corr_id = propagate_correlation_id(
            request_correlation_id=None,
            skill_run_id=None,
            mission_id="mission_456",
        )
        assert corr_id == "corr_mission_mission_456"

    def test_propagate_correlation_id_generates_when_none(self):
        """propagate_correlation_id generates new ID when all inputs None."""
        corr_id = propagate_correlation_id(
            request_correlation_id=None,
            skill_run_id=None,
            mission_id=None,
        )
        assert corr_id.startswith("corr_")


# ============================================================================
# Provenance Tests
# ============================================================================


class TestProvenanceRef:
    """Test provenance reference creation and parsing."""

    def test_create_provenance_ref(self):
        """ProvenanceRef creation and serialization."""
        ref = ProvenanceRef(ref_type="experience_record", ref_id="exp_123", correlation_id="corr_abc")
        assert ref.ref_type == "experience_record"
        assert ref.ref_id == "exp_123"
        assert ref.correlation_id == "corr_abc"

    def test_provenance_ref_to_string(self):
        """to_string produces compact format."""
        ref = ProvenanceRef(ref_type="experience_record", ref_id="exp_123", correlation_id="corr_abc")
        assert ref.to_string() == "experience_record:exp_123:corr_abc"

    def test_provenance_ref_to_string_without_correlation(self):
        """to_string works without correlation_id."""
        ref = ProvenanceRef(ref_type="insight_candidate", ref_id="ins_456")
        assert ref.to_string() == "insight_candidate:ins_456"

    def test_provenance_ref_from_string(self):
        """from_string parses compact format."""
        ref = ProvenanceRef.from_string("experience_record:exp_123:corr_abc")
        assert ref is not None
        assert ref.ref_type == "experience_record"
        assert ref.ref_id == "exp_123"
        assert ref.correlation_id == "corr_abc"

    def test_provenance_ref_from_string_without_correlation(self):
        """from_string parses format without correlation_id."""
        ref = ProvenanceRef.from_string("pattern_candidate:pat_789")
        assert ref is not None
        assert ref.ref_type == "pattern_candidate"
        assert ref.ref_id == "pat_789"
        assert ref.correlation_id is None

    def test_provenance_ref_from_string_invalid(self):
        """from_string returns None for invalid format."""
        ref = ProvenanceRef.from_string("invalid")
        assert ref is None

    def test_build_provenance_ref(self):
        """build_provenance_ref helper produces string."""
        ref_str = build_provenance_ref(ref_type="experience_record", ref_id="exp_123", correlation_id="corr_abc")
        assert ref_str == "experience_record:exp_123:corr_abc"

    def test_parse_provenance_refs(self):
        """parse_provenance_refs parses list of strings."""
        refs = parse_provenance_refs(
            [
                "experience_record:exp_123:corr_abc",
                "insight_candidate:ins_456",
                "invalid",
            ]
        )
        assert len(refs) == 2
        assert refs[0].ref_type == "experience_record"
        assert refs[1].ref_type == "insight_candidate"


# ============================================================================
# Redaction Tests (Security)
# ============================================================================


class TestRedaction:
    """Test redaction of sensitive data."""

    def test_redact_sensitive_data_bearer_token(self):
        """redact_sensitive_data redacts Bearer tokens."""
        text = "Authorization: Bearer abc123token456"
        redacted = redact_sensitive_data(text)
        assert "Bearer [REDACTED]" in redacted
        assert "abc123token456" not in redacted

    def test_redact_sensitive_data_api_key(self):
        """redact_sensitive_data redacts API keys."""
        text = "api_key=secret123"
        redacted = redact_sensitive_data(text)
        assert "api_key=[REDACTED]" in redacted
        assert "secret123" not in redacted

    def test_redact_sensitive_data_password(self):
        """redact_sensitive_data redacts passwords."""
        text = "password: mysecretpass"
        redacted = redact_sensitive_data(text)
        assert "password=[REDACTED]" in redacted
        assert "mysecretpass" not in redacted

    def test_redact_sensitive_data_email(self):
        """redact_sensitive_data redacts email addresses."""
        text = "Contact: user@example.com for support"
        redacted = redact_sensitive_data(text)
        assert "[EMAIL_REDACTED]" in redacted
        assert "user@example.com" not in redacted

    def test_redact_dict_simple(self):
        """redact_dict redacts sensitive keys."""
        data = {
            "username": "john",
            "password": "secret123",
            "api_key": "key456",
            "public_field": "visible",
        }
        redacted = redact_dict(data)
        assert redacted["username"] == "john"
        assert redacted["password"] == "[REDACTED]"
        assert redacted["api_key"] == "[REDACTED]"
        assert redacted["public_field"] == "visible"

    def test_redact_dict_nested(self):
        """redact_dict redacts nested dictionaries."""
        data = {
            "user": {
                "name": "john",
                "password": "secret123",
            },
            "config": {
                "token": "token789",
            },
        }
        redacted = redact_dict(data)
        assert redacted["user"]["name"] == "john"
        assert redacted["user"]["password"] == "[REDACTED]"
        assert redacted["config"]["token"] == "[REDACTED]"

    def test_redact_dict_list_of_dicts(self):
        """redact_dict handles lists of dictionaries."""
        data = {
            "users": [
                {"name": "alice", "password": "pass1"},
                {"name": "bob", "password": "pass2"},
            ]
        }
        redacted = redact_dict(data)
        assert redacted["users"][0]["name"] == "alice"
        assert redacted["users"][0]["password"] == "[REDACTED]"
        assert redacted["users"][1]["password"] == "[REDACTED]"

    def test_redact_dict_string_values(self):
        """redact_dict applies pattern redaction to string values."""
        data = {
            "message": "Bearer token123 in message",
            "log": "api_key=secret456",
        }
        redacted = redact_dict(data)
        assert "Bearer [REDACTED]" in redacted["message"]
        assert "token123" not in redacted["message"]
        assert "api_key=[REDACTED]" in redacted["log"]

    def test_build_failure_record_auto_redacts(self):
        """build_failure_record automatically redacts technical_details."""
        record = build_failure_record(
            tenant_id="tenant_xyz",
            entity="test_module",
            failure_class=FailureClass.INTEGRATION_FAILURE,
            failure_code=IntegrationFailureCode.EXTERNAL_API_ERROR,
            severity=Severity.ERROR,
            message="API call failed",
            technical_details={
                "url": "https://api.example.com",
                "api_key": "secret123",
                "response": "error",
            },
        )

        assert record.technical_details["url"] == "https://api.example.com"
        assert record.technical_details["api_key"] == "[REDACTED]"
        assert record.technical_details["response"] == "error"

    def test_build_failure_record_redacts_stack_trace(self):
        """build_failure_record redacts stack traces."""
        stack = "Error: Bearer token123\nFile: api.py\nLine: 42"
        record = build_failure_record(
            tenant_id="tenant_xyz",
            entity="test_module",
            failure_class=FailureClass.EXECUTION_FAILURE,
            failure_code=ExecutionFailureCode.UNHANDLED_EXCEPTION,
            severity=Severity.CRITICAL,
            message="Unhandled exception",
            stack_trace=stack,
        )

        assert "Bearer [REDACTED]" in record.stack_trace
        assert "token123" not in record.stack_trace


# ============================================================================
# Integration Tests
# ============================================================================


class TestDiagnosticsIntegration:
    """Integration tests for diagnostics workflows."""

    def test_request_failure_workflow(self):
        """End-to-end request failure workflow."""
        # Simulate HTTP request with correlation ID
        headers = {"x-correlation-id": "corr_req_123"}
        correlation_id = extract_correlation_id(headers)

        # Create failure record
        failure = build_failure_record(
            tenant_id="tenant_xyz",
            entity="skill_router",
            failure_class=FailureClass.REQUEST_FAILURE,
            failure_code=RequestFailureCode.VALIDATION_ERROR,
            severity=Severity.WARNING,
            message="Invalid skill_id format",
            correlation_id=correlation_id,
            retryability=Retryability.NO_RETRY,
            operator_action=OperatorAction.NONE,
            technical_details={"skill_id": "invalid_id"},
        )

        # Verify sanitized response for client
        sanitized = failure.to_sanitized_dict()
        assert sanitized["failure_class"] == "request_failure"
        assert sanitized["correlation_id"] == "corr_req_123"
        assert "stack_trace" not in sanitized

    def test_execution_failure_with_provenance_workflow(self):
        """End-to-end execution failure with provenance linking."""
        skill_run_id = "run_abc123"
        experience_id = "exp_def456"
        correlation_id = propagate_correlation_id(request_correlation_id=None, skill_run_id=skill_run_id)

        # Create failure with provenance
        failure = build_failure_record(
            tenant_id="tenant_xyz",
            entity="insight_layer",
            failure_class=FailureClass.LEARNING_PIPELINE_FAILURE,
            failure_code=LearningPipelineFailureCode.INSIGHT_EXTRACTION_FAILED,
            severity=Severity.ERROR,
            message="Failed to extract insight",
            correlation_id=correlation_id,
            skill_run_id=skill_run_id,
            retryability=Retryability.SAFE_RETRY,
            operator_action=OperatorAction.INVESTIGATE,
            provenance_refs=[
                build_provenance_ref(ref_type="experience_record", ref_id=experience_id, correlation_id=correlation_id)
            ],
        )

        # Verify provenance linkage
        assert len(failure.provenance_refs) == 1
        parsed_refs = parse_provenance_refs(failure.provenance_refs)
        assert parsed_refs[0].ref_type == "experience_record"
        assert parsed_refs[0].ref_id == experience_id
        assert parsed_refs[0].correlation_id == correlation_id

    def test_governance_failure_workflow(self):
        """End-to-end governance failure workflow."""
        failure = build_failure_record(
            tenant_id="tenant_xyz",
            entity="immune_orchestrator",
            failure_class=FailureClass.GOVERNANCE_FAILURE,
            failure_code=GovernanceFailureCode.APPROVAL_REQUIRED,
            severity=Severity.WARNING,
            message="High-risk recovery action requires approval",
            correlation_id="corr_immune_789",
            retryability=Retryability.NO_RETRY,
            operator_action=OperatorAction.NONE,
            technical_details={"action": "isolate_module", "risk_level": "high"},
        )

        assert failure.retryability == Retryability.NO_RETRY
        assert failure.operator_action == OperatorAction.NONE
        assert failure.technical_details["action"] == "isolate_module"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
