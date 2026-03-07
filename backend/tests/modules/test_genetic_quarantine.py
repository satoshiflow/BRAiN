from datetime import datetime, timezone

import pytest

from app.modules.genetic_quarantine.schemas import (
    QuarantineRequest,
    QuarantineSeverity,
    QuarantineState,
    QuarantineTransitionRequest,
)
from app.modules.genetic_quarantine.service import GeneticQuarantineService


@pytest.mark.asyncio
async def test_quarantine_and_transition_in_memory() -> None:
    service = GeneticQuarantineService(event_stream=None)

    record = await service.quarantine(
        QuarantineRequest(
            agent_id="agent-1",
            snapshot_version=5,
            reason="Mutation risk spike",
            requested_state=QuarantineState.QUARANTINED,
            severity=QuarantineSeverity.HIGH,
            source="immune_orchestrator",
            actor="immune_orchestrator",
            correlation_id="corr-gq-1",
            context={"decision": "isolate"},
            timestamp=datetime.now(timezone.utc),
        ),
        db=None,
    )

    assert record.state == QuarantineState.QUARANTINED
    assert record.severity == QuarantineSeverity.HIGH

    transitioned = await service.transition(
        QuarantineTransitionRequest(
            quarantine_id=record.quarantine_id,
            target_state=QuarantineState.PROBATION,
            reason="Controlled probation",
            actor="governance",
            correlation_id="corr-gq-1",
            context={"approved": True},
        ),
        db=None,
    )

    assert transitioned.previous_state == QuarantineState.QUARANTINED
    assert transitioned.state == QuarantineState.PROBATION

    audits = await service.list_audit_entries(db=None)
    assert len(audits) >= 2
