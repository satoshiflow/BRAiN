import pytest

from app.modules.opencode_repair.schemas import (
    RepairAutotriggerRequest,
    RepairTicketSeverity,
    RepairTicketStatus,
    RepairTicketUpdateRequest,
)
from app.modules.opencode_repair.service import OpenCodeRepairService


@pytest.mark.asyncio
async def test_repair_ticket_autotrigger_and_update() -> None:
    service = OpenCodeRepairService(event_stream=None)

    ticket = await service.create_ticket_from_signal(
        RepairAutotriggerRequest(
            source_module="immune_orchestrator",
            source_event_type="immune.decision",
            subject_id="sig-123",
            summary="Escalated risk requires patch",
            severity=RepairTicketSeverity.CRITICAL,
            correlation_id="corr-rt-1",
            context={"action": "escalate"},
            actor="immune_orchestrator",
        ),
        db=None,
    )

    assert ticket.status == RepairTicketStatus.OPEN
    assert ticket.governance_required is True

    updated = await service.update_ticket(
        RepairTicketUpdateRequest(
            ticket_id=ticket.ticket_id,
            status=RepairTicketStatus.PATCH_PROPOSED,
            note="Patch attached",
            actor="opencode",
            evidence={"patch_ref": "pr-xyz"},
        ),
        db=None,
    )

    assert updated.status == RepairTicketStatus.PATCH_PROPOSED
    assert updated.evidence.get("patch_ref") == "pr-xyz"

    audits = await service.list_audit_entries(db=None)
    assert len(audits) >= 2
