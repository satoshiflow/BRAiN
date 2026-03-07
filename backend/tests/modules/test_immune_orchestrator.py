import pytest

from app.modules.immune_orchestrator.schemas import IncidentSignal, SignalSeverity
from app.modules.immune_orchestrator.service import ImmuneOrchestratorService


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_immune_orchestrator_creates_decision_and_audit_entry():
    service = ImmuneOrchestratorService()

    signal = IncidentSignal(
        id="sig-1",
        type="agent.failure",
        source="agent_management",
        severity=SignalSeverity.CRITICAL,
        entity="agent-42",
        blast_radius=5,
        confidence=0.9,
        recurrence=3,
    )

    decision = await service.ingest_signal(signal)

    assert decision.signal_id == signal.id
    assert decision.priority_score >= 0.0
    assert decision.action.value in {"mitigate", "isolate", "escalate"}
    assert len(await service.list_audit_entries()) == 1


@pytest.mark.asyncio
async def test_immune_orchestrator_metrics_increment():
    service = ImmuneOrchestratorService()

    for idx in range(2):
        signal = IncidentSignal(
            id=f"sig-{idx}",
            type="health.degraded",
            source="system_health",
            severity=SignalSeverity.WARNING,
            entity=f"service-{idx}",
        )
        await service.ingest_signal(signal)

    metrics = await service.metrics()
    assert metrics.total_signals == 2
    assert metrics.total_decisions == 2
    assert metrics.by_source.get("system_health") == 2


@pytest.mark.asyncio
async def test_immune_orchestrator_persistence_hook_uses_db_session():
    service = ImmuneOrchestratorService()
    db = FakeDB()

    signal = IncidentSignal(
        id="sig-db-1",
        type="health.critical",
        source="runtime_auditor",
        severity=SignalSeverity.CRITICAL,
        entity="runtime",
    )
    await service.ingest_signal(signal, db=db)

    assert db.commits >= 2  # signal/decision + audit
