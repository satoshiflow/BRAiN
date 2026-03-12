import pytest

from app.modules.opencode_repair.schemas import (
    OpenCodeJobConstraints,
    OpenCodeJobContext,
    OpenCodeJobContractCreateRequest,
    OpenCodeJobMode,
    OpenCodeJobScope,
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


@pytest.mark.asyncio
async def test_dispatch_job_contract_queues_job() -> None:
    service = OpenCodeRepairService(event_stream=None)

    job = await service.dispatch_job_contract(
        OpenCodeJobContractCreateRequest(
            correlation_id="corr-job-1",
            mode=OpenCodeJobMode.BUILD,
            scope=OpenCodeJobScope(
                module="course_factory",
                entity_id="course-123",
                tenant_id="tenant-1",
            ),
            constraints=OpenCodeJobConstraints(
                timeout_seconds=900,
                max_iterations=1,
                risk_level="low",
                approval_required=False,
                blast_radius_limit=1,
            ),
            context=OpenCodeJobContext(
                trigger_event="course.deploy.staging.requested",
                original_request={"staging_domain": "example.staging"},
            ),
            created_by="course_factory_service",
        ),
        db=None,
    )

    assert job.job_id.startswith("job_")
    assert job.mode == OpenCodeJobMode.BUILD
    assert job.scope.module == "course_factory"
    assert job.status.value == "queued"
