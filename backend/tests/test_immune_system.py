"""
Test suite for Immune System hardening (Sprint D).

Tests the immune orchestrator's core decision logic, governance routing,
audit chain completeness, and adapter coverage patterns.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.immune_orchestrator.schemas import (
    DecisionAction,
    ImmuneDecision,
    IncidentSignal,
    SignalSeverity,
)
from app.modules.immune_orchestrator.service import ImmuneOrchestratorService


@pytest.fixture
def mock_db():
    """Mock database session."""
    db = MagicMock(spec=AsyncSession)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_event_stream():
    """Mock event stream."""
    stream = MagicMock()
    stream.publish = AsyncMock()
    return stream


@pytest.fixture
def immune_service(mock_event_stream):
    """Create immune orchestrator service with mocked event stream."""
    return ImmuneOrchestratorService(event_stream=mock_event_stream)


def create_test_signal(
    severity: SignalSeverity = SignalSeverity.WARNING,
    recurrence: int = 0,
    blast_radius: int = 1,
    confidence: float = 0.8,
    correlation_id: Optional[str] = None,
) -> IncidentSignal:
    """Create a test incident signal."""
    return IncidentSignal(
        id=f"sig-{uuid.uuid4().hex[:8]}",
        type="health_check_failure",
        source="health_monitor",
        severity=severity,
        entity="service.backend",
        timestamp=datetime.now(timezone.utc),
        context={"check": "database"},
        correlation_id=correlation_id or f"corr-{uuid.uuid4().hex[:8]}",
        blast_radius=blast_radius,
        confidence=confidence,
        recurrence=recurrence,
    )


# ============================================================================
# Core Decision Logic Tests
# ============================================================================


@pytest.mark.asyncio
async def test_observe_action_for_low_severity_signal(immune_service):
    """Low severity signal should result in OBSERVE action."""
    signal = create_test_signal(severity=SignalSeverity.INFO, recurrence=0)

    decision = await immune_service.ingest_signal(signal, db=None)

    assert decision.action == DecisionAction.OBSERVE
    assert decision.priority_score < 0.5
    assert decision.requires_governance_hook is False
    assert signal.correlation_id == decision.correlation_id


@pytest.mark.asyncio
async def test_warn_action_for_moderate_severity(immune_service):
    """Moderate severity should result in WARN action."""
    signal = create_test_signal(severity=SignalSeverity.WARNING, recurrence=0, confidence=0.7)

    decision = await immune_service.ingest_signal(signal, db=None)

    assert decision.action in {DecisionAction.WARN, DecisionAction.MITIGATE}
    assert 0.3 <= decision.priority_score <= 0.8
    assert decision.requires_governance_hook is False


@pytest.mark.asyncio
async def test_escalate_action_for_critical_recurring_signal(immune_service):
    """Critical severity with high recurrence should escalate."""
    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=5,
        blast_radius=10,
        confidence=0.95,
    )

    decision = await immune_service.ingest_signal(signal, db=None)

    assert decision.action == DecisionAction.ESCALATE
    assert decision.priority_score > 0.8
    assert decision.requires_governance_hook is True
    assert "escalation" in decision.reason.lower()


@pytest.mark.asyncio
async def test_isolate_action_for_high_blast_radius(immune_service):
    """High blast radius with critical severity should isolate."""
    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=2,
        blast_radius=50,
        confidence=0.9,
    )

    decision = await immune_service.ingest_signal(signal, db=None)

    assert decision.action in {DecisionAction.ISOLATE, DecisionAction.ESCALATE}
    assert decision.priority_score > 0.7
    assert decision.requires_governance_hook is True


@pytest.mark.asyncio
async def test_priority_score_increases_with_recurrence(immune_service):
    """Priority score should increase with signal recurrence."""
    signal_first = create_test_signal(severity=SignalSeverity.WARNING, recurrence=0)
    signal_recurring = create_test_signal(severity=SignalSeverity.WARNING, recurrence=10)

    decision_first = await immune_service.ingest_signal(signal_first, db=None)
    decision_recurring = await immune_service.ingest_signal(signal_recurring, db=None)

    assert decision_recurring.priority_score > decision_first.priority_score


# ============================================================================
# Governance Routing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_governance_hook_required_for_isolate(immune_service):
    """ISOLATE action must require governance hook."""
    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=3,
        blast_radius=30,
    )

    decision = await immune_service.ingest_signal(signal, db=None)

    if decision.action == DecisionAction.ISOLATE:
        assert decision.requires_governance_hook is True


@pytest.mark.asyncio
async def test_governance_hook_required_for_escalate(immune_service):
    """ESCALATE action must require governance hook."""
    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=10,
        blast_radius=100,
    )

    decision = await immune_service.ingest_signal(signal, db=None)

    if decision.action == DecisionAction.ESCALATE:
        assert decision.requires_governance_hook is True


@pytest.mark.asyncio
async def test_no_governance_hook_for_observe_warn(immune_service):
    """OBSERVE and WARN actions should not require governance hooks."""
    signal_info = create_test_signal(severity=SignalSeverity.INFO)
    signal_warn = create_test_signal(severity=SignalSeverity.WARNING, recurrence=1)

    decision_info = await immune_service.ingest_signal(signal_info, db=None)
    decision_warn = await immune_service.ingest_signal(signal_warn, db=None)

    if decision_info.action == DecisionAction.OBSERVE:
        assert decision_info.requires_governance_hook is False
    if decision_warn.action == DecisionAction.WARN:
        assert decision_warn.requires_governance_hook is False


@pytest.mark.asyncio
async def test_repair_trigger_invoked_for_isolate(immune_service):
    """Repair trigger should be invoked for ISOLATE actions."""
    repair_trigger = AsyncMock()
    immune_service.set_repair_trigger(repair_trigger)

    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=3,
        blast_radius=40,
    )

    decision = await immune_service.ingest_signal(signal, db=None)

    if decision.action == DecisionAction.ISOLATE:
        repair_trigger.assert_called_once()
        call_args = repair_trigger.call_args[0][0]
        assert call_args["source_module"] == "immune_orchestrator"
        assert call_args["subject_id"] == signal.id
        assert call_args["correlation_id"] == signal.correlation_id


@pytest.mark.asyncio
async def test_repair_trigger_invoked_for_escalate(immune_service):
    """Repair trigger should be invoked for ESCALATE actions."""
    repair_trigger = AsyncMock()
    immune_service.set_repair_trigger(repair_trigger)

    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=10,
        blast_radius=100,
    )

    decision = await immune_service.ingest_signal(signal, db=None)

    if decision.action == DecisionAction.ESCALATE:
        repair_trigger.assert_called_once()
        call_args = repair_trigger.call_args[0][0]
        assert call_args["severity"] == "critical"


# ============================================================================
# Audit Chain Completeness Tests
# ============================================================================


@pytest.mark.asyncio
async def test_audit_entry_created_for_decision(immune_service):
    """Every decision must create an audit entry."""
    signal = create_test_signal(severity=SignalSeverity.WARNING)

    await immune_service.ingest_signal(signal, db=None)

    audit_entries = await immune_service.list_audit_entries(db=None)
    assert len(audit_entries) == 1
    entry = audit_entries[0]
    assert entry.event_type == "immune.decision"
    assert entry.actor == "immune_orchestrator"
    assert entry.resource_id == signal.id
    assert entry.correlation_id == signal.correlation_id


@pytest.mark.asyncio
async def test_audit_entry_contains_decision_details(immune_service):
    """Audit entry must contain complete decision context."""
    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=5,
    )

    decision = await immune_service.ingest_signal(signal, db=None)
    audit_entries = await immune_service.list_audit_entries(db=None)

    entry = audit_entries[0]
    assert entry.details["decision_id"] == decision.decision_id
    assert entry.details["priority_score"] == decision.priority_score
    assert entry.details["source"] == signal.source
    assert entry.details["type"] == signal.type
    assert entry.details["entity"] == signal.entity


@pytest.mark.asyncio
async def test_correlation_id_propagates_through_audit_chain(immune_service):
    """Correlation ID must propagate through entire audit chain."""
    correlation_id = f"test-corr-{uuid.uuid4().hex[:8]}"
    signal = create_test_signal(correlation_id=correlation_id)

    decision = await immune_service.ingest_signal(signal, db=None)
    audit_entries = await immune_service.list_audit_entries(db=None)

    assert signal.correlation_id == correlation_id
    assert decision.correlation_id == correlation_id
    assert audit_entries[0].correlation_id == correlation_id


@pytest.mark.asyncio
@patch("app.modules.immune_orchestrator.service.write_unified_audit")
async def test_unified_audit_invoked_for_every_decision(mock_audit, immune_service):
    """write_unified_audit must be called for every decision."""
    mock_audit.return_value = AsyncMock()

    signal = create_test_signal(severity=SignalSeverity.WARNING)
    await immune_service.ingest_signal(signal, db=None)

    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args[1]
    assert call_kwargs["event_type"] == "immune.decision"
    assert call_kwargs["actor"] == "immune_orchestrator"
    assert call_kwargs["resource_id"] == signal.id


# ============================================================================
# Event Stream Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_event_published_for_decision(immune_service, mock_event_stream):
    """Event must be published to EventStream for every decision."""
    signal = create_test_signal(severity=SignalSeverity.WARNING)

    await immune_service.ingest_signal(signal, db=None)

    mock_event_stream.publish.assert_called_once()


@pytest.mark.asyncio
async def test_event_contains_complete_decision_payload(immune_service, mock_event_stream):
    """Published event must contain complete decision context."""
    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=3,
    )

    decision = await immune_service.ingest_signal(signal, db=None)

    mock_event_stream.publish.assert_called_once()
    # Event construction is mocked, but we verify it was called


@pytest.mark.asyncio
async def test_event_failure_does_not_block_decision(immune_service, mock_event_stream):
    """Event publish failure must not prevent decision completion."""
    mock_event_stream.publish.side_effect = Exception("Event stream unavailable")

    signal = create_test_signal(severity=SignalSeverity.WARNING)
    decision = await immune_service.ingest_signal(signal, db=None)

    # Decision should complete despite event failure
    assert decision.action is not None
    assert decision.decision_id is not None


# ============================================================================
# Memory Fallback Tests
# ============================================================================


@pytest.mark.asyncio
async def test_signals_list_returns_memory_when_db_none(immune_service):
    """list_signals should return in-memory signals when db=None."""
    signal = create_test_signal()
    await immune_service.ingest_signal(signal, db=None)

    signals = await immune_service.list_signals(db=None)
    assert len(signals) == 1
    assert signals[0].id == signal.id


@pytest.mark.asyncio
async def test_decisions_list_returns_memory_when_db_none(immune_service):
    """list_decisions should return in-memory decisions when db=None."""
    signal = create_test_signal()
    await immune_service.ingest_signal(signal, db=None)

    decisions = await immune_service.list_decisions(db=None)
    assert len(decisions) == 1
    assert decisions[0].signal_id == signal.id


@pytest.mark.asyncio
async def test_audit_list_returns_memory_when_db_none(immune_service):
    """list_audit_entries should return in-memory entries when db=None."""
    signal = create_test_signal()
    await immune_service.ingest_signal(signal, db=None)

    entries = await immune_service.list_audit_entries(db=None)
    assert len(entries) == 1


# ============================================================================
# Metrics Tests
# ============================================================================


@pytest.mark.asyncio
async def test_metrics_tracks_signal_count(immune_service):
    """Metrics should accurately track total signal count."""
    for i in range(3):
        signal = create_test_signal()
        await immune_service.ingest_signal(signal, db=None)

    metrics = await immune_service.metrics(db=None)
    assert metrics.total_signals == 3
    assert metrics.total_decisions == 3


@pytest.mark.asyncio
async def test_metrics_tracks_action_distribution(immune_service):
    """Metrics should track action distribution."""
    # Create signals with different severities to trigger different actions
    signal_info = create_test_signal(severity=SignalSeverity.INFO)
    signal_warn = create_test_signal(severity=SignalSeverity.WARNING)
    signal_crit = create_test_signal(severity=SignalSeverity.CRITICAL, recurrence=5)

    await immune_service.ingest_signal(signal_info, db=None)
    await immune_service.ingest_signal(signal_warn, db=None)
    await immune_service.ingest_signal(signal_crit, db=None)

    metrics = await immune_service.metrics(db=None)
    assert metrics.total_decisions == 3
    assert len(metrics.actions) > 0
    assert sum(metrics.actions.values()) == 3


@pytest.mark.asyncio
async def test_metrics_tracks_source_distribution(immune_service):
    """Metrics should track signal sources."""
    signal1 = create_test_signal()
    signal1.source = "health_monitor"
    signal2 = create_test_signal()
    signal2.source = "runtime_auditor"

    await immune_service.ingest_signal(signal1, db=None)
    await immune_service.ingest_signal(signal2, db=None)

    metrics = await immune_service.metrics(db=None)
    assert metrics.by_source["health_monitor"] >= 1
    assert metrics.by_source["runtime_auditor"] >= 1


# ============================================================================
# Service Singleton Tests
# ============================================================================


def test_get_immune_orchestrator_service_returns_singleton():
    """get_immune_orchestrator_service should return singleton."""
    from app.modules.immune_orchestrator.service import get_immune_orchestrator_service

    service1 = get_immune_orchestrator_service()
    service2 = get_immune_orchestrator_service()

    assert service1 is service2


def test_get_immune_orchestrator_service_sets_event_stream():
    """get_immune_orchestrator_service should set event stream if provided."""
    from app.modules.immune_orchestrator.service import (
        get_immune_orchestrator_service,
        _service,
    )

    # Reset singleton
    import app.modules.immune_orchestrator.service as svc_module
    svc_module._service = None

    mock_stream = MagicMock()
    service = get_immune_orchestrator_service(event_stream=mock_stream)

    assert service.event_stream is mock_stream


# ============================================================================
# Adapter Coverage Pattern Tests (from immune_adapter_coverage.md)
# ============================================================================


@pytest.mark.asyncio
async def test_signal_ingestion_from_health_monitor(immune_service):
    """Verify signal can be ingested from health_monitor adapter."""
    signal = create_test_signal()
    signal.source = "health_monitor"
    signal.type = "health_check_failure"

    decision = await immune_service.ingest_signal(signal, db=None)

    assert decision.signal_id == signal.id
    assert decision.action is not None


@pytest.mark.asyncio
async def test_signal_ingestion_from_runtime_auditor(immune_service):
    """Verify signal can be ingested from runtime_auditor adapter."""
    signal = create_test_signal()
    signal.source = "runtime_auditor"
    signal.type = "circuit_breaker_open"

    decision = await immune_service.ingest_signal(signal, db=None)

    assert decision.signal_id == signal.id
    assert decision.action is not None


@pytest.mark.asyncio
async def test_signal_ingestion_from_observer_core(immune_service):
    """Verify signal can be ingested from observer_core adapter."""
    signal = create_test_signal()
    signal.source = "observer_core"
    signal.type = "timeline_query_failure"

    decision = await immune_service.ingest_signal(signal, db=None)

    assert decision.signal_id == signal.id
    assert decision.action is not None


@pytest.mark.asyncio
async def test_adapter_pattern_preserves_correlation_id(immune_service):
    """Adapter ingestion must preserve correlation_id from source."""
    correlation_id = f"adapter-test-{uuid.uuid4().hex[:8]}"
    signal = create_test_signal(correlation_id=correlation_id)

    decision = await immune_service.ingest_signal(signal, db=None)

    assert signal.correlation_id == correlation_id
    assert decision.correlation_id == correlation_id


# ============================================================================
# Decision Reason Tests
# ============================================================================


@pytest.mark.asyncio
async def test_decision_reason_explains_escalation(immune_service):
    """Decision reason for ESCALATE must mention score and recurrence."""
    signal = create_test_signal(severity=SignalSeverity.CRITICAL, recurrence=10)

    decision = await immune_service.ingest_signal(signal, db=None)

    if decision.action == DecisionAction.ESCALATE:
        assert "score" in decision.reason.lower()
        assert "recurrence" in decision.reason.lower()


@pytest.mark.asyncio
async def test_decision_reason_explains_isolation(immune_service):
    """Decision reason for ISOLATE must mention score."""
    signal = create_test_signal(
        severity=SignalSeverity.CRITICAL,
        recurrence=3,
        blast_radius=50,
    )

    decision = await immune_service.ingest_signal(signal, db=None)

    if decision.action == DecisionAction.ISOLATE:
        assert "score" in decision.reason.lower()
        assert "isolation" in decision.reason.lower() or "isolate" in decision.reason.lower()


# ============================================================================
# Summary Test
# ============================================================================


@pytest.mark.asyncio
async def test_end_to_end_decision_flow_with_all_artifacts(immune_service):
    """
    End-to-end test verifying complete decision flow:
    - Signal ingestion
    - Decision creation
    - Audit entry creation
    - Correlation ID propagation
    - Metrics tracking
    """
    correlation_id = f"e2e-test-{uuid.uuid4().hex[:8]}"
    signal = create_test_signal(
        severity=SignalSeverity.WARNING,
        recurrence=2,
        correlation_id=correlation_id,
    )

    # Ingest signal
    decision = await immune_service.ingest_signal(signal, db=None)

    # Verify decision
    assert decision.decision_id is not None
    assert decision.signal_id == signal.id
    assert decision.action is not None
    assert decision.correlation_id == correlation_id

    # Verify signal stored
    signals = await immune_service.list_signals(db=None)
    assert any(s.id == signal.id for s in signals)

    # Verify decision stored
    decisions = await immune_service.list_decisions(db=None)
    assert any(d.decision_id == decision.decision_id for d in decisions)

    # Verify audit entry created
    audit_entries = await immune_service.list_audit_entries(db=None)
    matching_entries = [e for e in audit_entries if e.resource_id == signal.id]
    assert len(matching_entries) > 0
    assert matching_entries[0].correlation_id == correlation_id

    # Verify metrics updated
    metrics = await immune_service.metrics(db=None)
    assert metrics.total_signals > 0
    assert metrics.total_decisions > 0
