import pytest

from app.modules.genetic_integrity.schemas import MutationAuditRequest, RegisterSnapshotRequest
from app.modules.genetic_integrity.service import GeneticIntegrityService
from app.modules.immune_orchestrator.schemas import IncidentSignal, SignalSeverity
from app.modules.immune_orchestrator.service import ImmuneOrchestratorService
from app.modules.recovery_policy_engine.schemas import RecoveryRequest, RecoverySeverity
from app.modules.recovery_policy_engine.service import RecoveryPolicyService


class DummyEvent:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class DummyEventStream:
    def __init__(self):
        self.events = []

    async def publish(self, event):
        self.events.append(event)


def _assert_envelope(payload: dict):
    required = {"event_type", "severity", "source", "entity", "correlation_id", "occurred_at", "data"}
    assert required.issubset(set(payload.keys()))


@pytest.mark.asyncio
async def test_immune_event_envelope_contract(monkeypatch):
    stream = DummyEventStream()
    service = ImmuneOrchestratorService(event_stream=stream)

    import app.modules.immune_orchestrator.service as immune_service_module
    monkeypatch.setattr(immune_service_module, "Event", DummyEvent)

    signal = IncidentSignal(
        id="sig-contract-1",
        type="agent.failure",
        source="agent_management",
        severity=SignalSeverity.WARNING,
        entity="agent-1",
        correlation_id="corr-1",
    )
    await service.ingest_signal(signal)

    assert len(stream.events) == 1
    event = stream.events[0]
    assert event.type == "immune.decision"
    _assert_envelope(event.payload)


@pytest.mark.asyncio
async def test_recovery_event_envelope_contract(monkeypatch):
    stream = DummyEventStream()
    service = RecoveryPolicyService(event_stream=stream)

    import app.modules.recovery_policy_engine.service as recovery_service_module
    monkeypatch.setattr(recovery_service_module, "Event", DummyEvent)

    request = RecoveryRequest(
        id="rec-contract-1",
        source="task_queue",
        entity_id="task-1",
        failure_type="timeout",
        severity=RecoverySeverity.HIGH,
        correlation_id="corr-2",
    )
    await service.decide(request)

    assert len(stream.events) == 1
    event = stream.events[0]
    assert event.type == "recovery.action"
    _assert_envelope(event.payload)


@pytest.mark.asyncio
async def test_genetic_event_envelope_contract(monkeypatch):
    stream = DummyEventStream()
    service = GeneticIntegrityService(event_stream=stream)

    import app.modules.genetic_integrity.service as genetic_service_module
    monkeypatch.setattr(genetic_service_module, "Event", DummyEvent)

    await service.register_snapshot(
        RegisterSnapshotRequest(
            agent_id="agent-contract",
            snapshot_version=1,
            dna_payload={"metadata": {"blueprint_id": "bp-contract"}},
            correlation_id="corr-3",
        )
    )
    await service.record_mutation(
        MutationAuditRequest(
            agent_id="agent-contract",
            from_version=1,
            to_version=2,
            actor="genesis",
            reason="contract_test",
            mutation={"temperature": 0.5},
            correlation_id="corr-3",
        )
    )

    assert len(stream.events) == 2
    assert stream.events[0].type == "genetic_integrity.snapshot_registered"
    assert stream.events[1].type == "genetic_integrity.mutation_recorded"
    _assert_envelope(stream.events[0].payload)
    _assert_envelope(stream.events[1].payload)
