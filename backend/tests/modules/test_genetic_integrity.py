import pytest

from app.modules.genetic_integrity.schemas import MutationAuditRequest, RegisterSnapshotRequest
from app.modules.genetic_integrity.service import GeneticIntegrityService


class FakeDB:
    def __init__(self):
        self.added = []
        self.commits = 0

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_genetic_integrity_register_and_verify_snapshot():
    service = GeneticIntegrityService()

    payload = {"metadata": {"blueprint_id": "bp-1"}, "tools": ["search"]}
    record = await service.register_snapshot(
        RegisterSnapshotRequest(
            agent_id="agent-1",
            snapshot_version=1,
            parent_snapshot=None,
            dna_payload=payload,
        )
    )

    verification = await service.verify_snapshot("agent-1", 1, payload)
    assert record.agent_id == "agent-1"
    assert verification.valid is True


@pytest.mark.asyncio
async def test_genetic_integrity_mutation_audit_and_metrics():
    service = GeneticIntegrityService()

    await service.register_snapshot(
        RegisterSnapshotRequest(
            agent_id="agent-2",
            snapshot_version=1,
            parent_snapshot=None,
            dna_payload={"metadata": {"blueprint_id": "bp-2"}},
        )
    )
    await service.register_snapshot(
        RegisterSnapshotRequest(
            agent_id="agent-2",
            snapshot_version=2,
            parent_snapshot=1,
            dna_payload={"metadata": {"blueprint_id": "bp-2"}, "temperature": 0.4},
        )
    )

    audit = await service.record_mutation(
        MutationAuditRequest(
            agent_id="agent-2",
            from_version=1,
            to_version=2,
            actor="genesis",
            reason="fitness_evolution",
            mutation={"temperature": 0.4},
            requires_governance_hook=True,
        )
    )

    metrics = await service.metrics()
    assert audit.requires_governance_hook is True
    assert metrics.total_snapshots == 2
    assert metrics.total_mutations == 1
    assert metrics.governance_hooks == 1


@pytest.mark.asyncio
async def test_genetic_integrity_persistence_hook_uses_db_session():
    service = GeneticIntegrityService()
    db = FakeDB()

    await service.register_snapshot(
        RegisterSnapshotRequest(
            agent_id="agent-db",
            snapshot_version=1,
            dna_payload={"metadata": {"blueprint_id": "bp-db"}},
        ),
        db=db,
    )
    await service.record_mutation(
        MutationAuditRequest(
            agent_id="agent-db",
            from_version=1,
            to_version=2,
            actor="genesis",
            reason="db_path",
            mutation={"x": 1},
        ),
        db=db,
    )

    assert db.commits >= 4  # snapshot + audit + mutation + audit
