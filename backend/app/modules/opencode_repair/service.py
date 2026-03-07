"""Service for OpenCode repair loop."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_bridge import write_unified_audit
from app.core.event_contract import EventSeverity, build_event_instance, build_runtime_event_payload
from app.modules.opencode_repair.models import OpenCodeRepairAuditModel, OpenCodeRepairTicketModel
from app.modules.opencode_repair.schemas import (
    RepairAuditEntry,
    RepairAutotriggerRequest,
    RepairTicket,
    RepairTicketCreateRequest,
    RepairTicketSeverity,
    RepairTicketStatus,
    RepairTicketUpdateRequest,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _to_ticket(model: OpenCodeRepairTicketModel) -> RepairTicket:
    return RepairTicket(
        ticket_id=model.ticket_id,
        source_module=model.source_module,
        source_event_type=model.source_event_type,
        title=model.title,
        description=model.description,
        severity=RepairTicketSeverity(model.severity),
        status=RepairTicketStatus(model.status),
        correlation_id=model.correlation_id,
        actor=model.actor,
        governance_required=model.governance_required,
        evidence=model.evidence or {},
        created_at=model.created_at.replace(tzinfo=timezone.utc),
        updated_at=model.updated_at.replace(tzinfo=timezone.utc),
    )


def _to_audit(model: OpenCodeRepairAuditModel) -> RepairAuditEntry:
    return RepairAuditEntry(
        audit_id=model.audit_id,
        ticket_id=model.ticket_id,
        action=model.action,
        actor=model.actor,
        details=model.details or {},
        correlation_id=model.correlation_id,
        timestamp=model.timestamp.replace(tzinfo=timezone.utc),
    )


class OpenCodeRepairService:
    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self.event_stream = event_stream
        self._tickets: List[RepairTicket] = []
        self._audit_entries: List[RepairAuditEntry] = []

    @asynccontextmanager
    async def _best_effort_db(self, db: Optional[AsyncSession]):
        if db is None:
            yield None
            return
        try:
            yield db
        except Exception:
            await db.rollback()
            yield None

    async def create_ticket(self, request: RepairTicketCreateRequest, db: Optional[AsyncSession] = None) -> RepairTicket:
        now = _now_utc()
        ticket = RepairTicket(
            ticket_id=f"rt_{uuid.uuid4().hex[:12]}",
            source_module=request.source_module,
            source_event_type=request.source_event_type,
            title=request.title,
            description=request.description,
            severity=request.severity,
            status=RepairTicketStatus.OPEN,
            correlation_id=request.correlation_id,
            actor=request.actor,
            governance_required=request.governance_required,
            evidence=request.evidence,
            created_at=now,
            updated_at=now,
        )

        persisted = False
        async with self._best_effort_db(db) as session:
            if session is not None:
                session.add(
                    OpenCodeRepairTicketModel(
                        ticket_id=ticket.ticket_id,
                        source_module=ticket.source_module,
                        source_event_type=ticket.source_event_type,
                        title=ticket.title,
                        description=ticket.description,
                        severity=ticket.severity.value,
                        status=ticket.status.value,
                        correlation_id=ticket.correlation_id,
                        actor=ticket.actor,
                        governance_required=ticket.governance_required,
                        evidence=ticket.evidence,
                        created_at=_naive_utc(ticket.created_at),
                        updated_at=_naive_utc(ticket.updated_at),
                    )
                )
                await session.commit()
                persisted = True

        if not persisted:
            self._tickets.append(ticket)

        await self._append_audit(
            ticket_id=ticket.ticket_id,
            action="ticket_created",
            actor=ticket.actor,
            details={
                "source_module": ticket.source_module,
                "source_event_type": ticket.source_event_type,
                "severity": ticket.severity.value,
                "status": ticket.status.value,
            },
            correlation_id=ticket.correlation_id,
            db=db,
        )
        await self._publish_event(ticket, "ticket_created")
        return ticket

    async def create_ticket_from_signal(self, request: RepairAutotriggerRequest, db: Optional[AsyncSession] = None) -> RepairTicket:
        governance_required = request.severity in {RepairTicketSeverity.HIGH, RepairTicketSeverity.CRITICAL}
        return await self.create_ticket(
            RepairTicketCreateRequest(
                source_module=request.source_module,
                source_event_type=request.source_event_type,
                title=f"Repair request for {request.subject_id}",
                description=request.summary,
                severity=request.severity,
                correlation_id=request.correlation_id,
                actor=request.actor,
                evidence={"subject_id": request.subject_id, "context": request.context, "timestamp": request.timestamp.isoformat()},
                governance_required=governance_required,
            ),
            db=db,
        )

    async def update_ticket(self, request: RepairTicketUpdateRequest, db: Optional[AsyncSession] = None) -> RepairTicket:
        ticket = await self.get_ticket(request.ticket_id, db=db)
        if ticket is None:
            raise ValueError(f"Unknown ticket_id: {request.ticket_id}")

        updated = RepairTicket(
            ticket_id=ticket.ticket_id,
            source_module=ticket.source_module,
            source_event_type=ticket.source_event_type,
            title=ticket.title,
            description=ticket.description,
            severity=ticket.severity,
            status=request.status,
            correlation_id=ticket.correlation_id,
            actor=request.actor,
            governance_required=ticket.governance_required,
            evidence={**ticket.evidence, **request.evidence, "last_note": request.note},
            created_at=ticket.created_at,
            updated_at=_now_utc(),
        )

        persisted = False
        async with self._best_effort_db(db) as session:
            if session is not None:
                row = await session.get(OpenCodeRepairTicketModel, updated.ticket_id)
                if row is None:
                    raise ValueError(f"Unknown ticket_id: {request.ticket_id}")
                row.status = updated.status.value
                row.actor = updated.actor
                row.evidence = updated.evidence
                row.updated_at = _naive_utc(updated.updated_at)
                await session.commit()
                persisted = True

        if not persisted:
            self._tickets = [t for t in self._tickets if t.ticket_id != updated.ticket_id]
            self._tickets.append(updated)

        await self._append_audit(
            ticket_id=updated.ticket_id,
            action="ticket_updated",
            actor=updated.actor,
            details={"status": updated.status.value, "note": request.note},
            correlation_id=updated.correlation_id,
            db=db,
        )
        await self._publish_event(updated, "ticket_updated")
        return updated

    async def list_tickets(self, db: Optional[AsyncSession] = None) -> List[RepairTicket]:
        async with self._best_effort_db(db) as session:
            if session is not None:
                result = await session.execute(select(OpenCodeRepairTicketModel).order_by(OpenCodeRepairTicketModel.updated_at.desc()))
                return [_to_ticket(r) for r in result.scalars().all()]
        return sorted(self._tickets, key=lambda t: t.updated_at, reverse=True)

    async def list_audit_entries(self, db: Optional[AsyncSession] = None) -> List[RepairAuditEntry]:
        async with self._best_effort_db(db) as session:
            if session is not None:
                result = await session.execute(select(OpenCodeRepairAuditModel).order_by(OpenCodeRepairAuditModel.timestamp.desc()))
                return [_to_audit(r) for r in result.scalars().all()]
        return sorted(self._audit_entries, key=lambda a: a.timestamp, reverse=True)

    async def get_ticket(self, ticket_id: str, db: Optional[AsyncSession] = None) -> Optional[RepairTicket]:
        async with self._best_effort_db(db) as session:
            if session is not None:
                row = await session.get(OpenCodeRepairTicketModel, ticket_id)
                return _to_ticket(row) if row else None
        for ticket in self._tickets:
            if ticket.ticket_id == ticket_id:
                return ticket
        return None

    async def _append_audit(
        self,
        *,
        ticket_id: str,
        action: str,
        actor: str,
        details: dict,
        correlation_id: Optional[str],
        db: Optional[AsyncSession],
    ) -> None:
        audit = RepairAuditEntry(
            audit_id=f"rta_{uuid.uuid4().hex[:12]}",
            ticket_id=ticket_id,
            action=action,
            actor=actor,
            details=details,
            correlation_id=correlation_id,
            timestamp=_now_utc(),
        )

        persisted = False
        async with self._best_effort_db(db) as session:
            if session is not None:
                session.add(
                    OpenCodeRepairAuditModel(
                        audit_id=audit.audit_id,
                        ticket_id=audit.ticket_id,
                        action=audit.action,
                        actor=audit.actor,
                        details=audit.details,
                        correlation_id=audit.correlation_id,
                        timestamp=_naive_utc(audit.timestamp),
                    )
                )
                await session.commit()
                persisted = True

        if not persisted:
            self._audit_entries.append(audit)

        await write_unified_audit(
            event_type=f"opencode_repair.{action}",
            action=f"opencode_repair.{action}",
            actor=actor,
            actor_type="system",
            resource_type="repair_ticket",
            resource_id=ticket_id,
            severity="warning",
            message=f"Repair ticket {action}",
            correlation_id=correlation_id,
            details=details,
            db=db,
        )

    async def _publish_event(self, ticket: RepairTicket, action: str) -> None:
        if self.event_stream is None:
            return
        try:
            from mission_control_core.core import Event

            severity = EventSeverity.INFO
            if ticket.severity in {RepairTicketSeverity.HIGH, RepairTicketSeverity.CRITICAL}:
                severity = EventSeverity.WARNING
            payload = build_runtime_event_payload(
                event_type="opencode_repair.ticket",
                severity=severity,
                source="opencode_repair",
                entity=ticket.ticket_id,
                correlation_id=ticket.correlation_id,
                data={
                    "action": action,
                    "status": ticket.status.value,
                    "severity": ticket.severity.value,
                    "source_module": ticket.source_module,
                },
            )
            event = build_event_instance(
                Event,
                event_type="opencode_repair.ticket",
                source="opencode_repair",
                payload=payload,
                correlation_id=ticket.correlation_id,
            )
            await self.event_stream.publish(event)
        except Exception:
            return


_service: Optional[OpenCodeRepairService] = None


def get_opencode_repair_service(event_stream: Optional["EventStream"] = None) -> OpenCodeRepairService:
    global _service
    if _service is None:
        _service = OpenCodeRepairService(event_stream=event_stream)
        return _service
    if event_stream is not None and _service.event_stream is None:
        _service.event_stream = event_stream
    return _service
