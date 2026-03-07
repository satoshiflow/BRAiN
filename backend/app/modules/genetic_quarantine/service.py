"""Service for Genetic Quarantine Manager."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_bridge import write_unified_audit
from app.core.event_contract import EventSeverity, build_event_instance, build_runtime_event_payload
from app.modules.genetic_quarantine.models import GeneticQuarantineAuditModel, GeneticQuarantineRecordModel
from app.modules.genetic_quarantine.schemas import (
    QuarantineAuditEntry,
    QuarantineRecord,
    QuarantineRequest,
    QuarantineSeverity,
    QuarantineState,
    QuarantineTransitionRequest,
)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _naive_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _to_record(model: GeneticQuarantineRecordModel) -> QuarantineRecord:
    prev_state = QuarantineState(model.previous_state) if model.previous_state else None
    return QuarantineRecord(
        quarantine_id=model.quarantine_id,
        agent_id=model.agent_id,
        snapshot_version=model.snapshot_version,
        state=QuarantineState(model.state),
        previous_state=prev_state,
        reason=model.reason,
        severity=QuarantineSeverity(model.severity),
        source=model.source,
        actor=model.actor,
        correlation_id=model.correlation_id,
        context=model.context or {},
        created_at=model.created_at.replace(tzinfo=timezone.utc),
    )


def _to_audit(model: GeneticQuarantineAuditModel) -> QuarantineAuditEntry:
    return QuarantineAuditEntry(
        audit_id=model.audit_id,
        quarantine_id=model.quarantine_id,
        event_type=model.event_type,
        action=model.action,
        actor=model.actor,
        details=model.details or {},
        correlation_id=model.correlation_id,
        timestamp=model.timestamp.replace(tzinfo=timezone.utc),
    )


class GeneticQuarantineService:
    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self.event_stream = event_stream
        self._records: List[QuarantineRecord] = []
        self._audits: List[QuarantineAuditEntry] = []

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

    async def quarantine(self, request: QuarantineRequest, db: Optional[AsyncSession] = None) -> QuarantineRecord:
        quarantine_id = f"gq_{uuid.uuid4().hex[:12]}"
        record = QuarantineRecord(
            quarantine_id=quarantine_id,
            agent_id=request.agent_id,
            snapshot_version=request.snapshot_version,
            state=request.requested_state,
            previous_state=None,
            reason=request.reason,
            severity=request.severity,
            source=request.source,
            actor=request.actor,
            correlation_id=request.correlation_id,
            context=request.context,
            created_at=request.timestamp,
        )

        persisted = False
        async with self._best_effort_db(db) as session:
            if session is not None:
                session.add(
                    GeneticQuarantineRecordModel(
                        quarantine_id=record.quarantine_id,
                        agent_id=record.agent_id,
                        snapshot_version=record.snapshot_version,
                        state=record.state.value,
                        previous_state=None,
                        reason=record.reason,
                        severity=record.severity.value,
                        source=record.source,
                        actor=record.actor,
                        correlation_id=record.correlation_id,
                        context=record.context,
                        created_at=_naive_utc(record.created_at),
                    )
                )
                await session.commit()
                persisted = True

        if not persisted:
            self._records.append(record)

        await self._append_audit(
            quarantine_id=record.quarantine_id,
            event_type="genetic_quarantine.state_changed",
            action="quarantine",
            actor=record.actor,
            details={
                "agent_id": record.agent_id,
                "snapshot_version": record.snapshot_version,
                "state": record.state.value,
                "severity": record.severity.value,
                "reason": record.reason,
                "context": record.context,
            },
            correlation_id=record.correlation_id,
            db=db,
        )
        await self._publish_event(record, action="quarantine")
        return record

    async def transition(self, request: QuarantineTransitionRequest, db: Optional[AsyncSession] = None) -> QuarantineRecord:
        record = await self.get_record(request.quarantine_id, db=db)
        if record is None:
            raise ValueError(f"Unknown quarantine_id: {request.quarantine_id}")

        prev_state = record.state
        record = QuarantineRecord(
            quarantine_id=record.quarantine_id,
            agent_id=record.agent_id,
            snapshot_version=record.snapshot_version,
            state=request.target_state,
            previous_state=prev_state,
            reason=request.reason,
            severity=record.severity,
            source=record.source,
            actor=request.actor,
            correlation_id=request.correlation_id or record.correlation_id,
            context={**record.context, **request.context},
            created_at=_now_utc(),
        )

        persisted = False
        async with self._best_effort_db(db) as session:
            if session is not None:
                existing = await session.get(GeneticQuarantineRecordModel, request.quarantine_id)
                if existing is None:
                    raise ValueError(f"Unknown quarantine_id: {request.quarantine_id}")
                existing.previous_state = prev_state.value
                existing.state = request.target_state.value
                existing.reason = request.reason
                existing.actor = request.actor
                existing.correlation_id = request.correlation_id or existing.correlation_id
                existing.context = {**(existing.context or {}), **request.context}
                existing.created_at = _naive_utc(record.created_at)
                await session.commit()
                persisted = True

        if not persisted:
            self._records = [r for r in self._records if r.quarantine_id != record.quarantine_id]
            self._records.append(record)

        await self._append_audit(
            quarantine_id=record.quarantine_id,
            event_type="genetic_quarantine.state_changed",
            action="transition",
            actor=request.actor,
            details={
                "from_state": prev_state.value,
                "to_state": request.target_state.value,
                "reason": request.reason,
                "context": request.context,
            },
            correlation_id=record.correlation_id,
            db=db,
        )
        await self._publish_event(record, action="transition")
        return record

    async def list_records(self, db: Optional[AsyncSession] = None) -> List[QuarantineRecord]:
        async with self._best_effort_db(db) as session:
            if session is not None:
                result = await session.execute(
                    select(GeneticQuarantineRecordModel).order_by(GeneticQuarantineRecordModel.created_at.desc())
                )
                return [_to_record(item) for item in result.scalars().all()]
        return sorted(self._records, key=lambda r: r.created_at, reverse=True)

    async def list_audit_entries(self, db: Optional[AsyncSession] = None) -> List[QuarantineAuditEntry]:
        async with self._best_effort_db(db) as session:
            if session is not None:
                result = await session.execute(
                    select(GeneticQuarantineAuditModel).order_by(GeneticQuarantineAuditModel.timestamp.desc())
                )
                return [_to_audit(item) for item in result.scalars().all()]
        return sorted(self._audits, key=lambda e: e.timestamp, reverse=True)

    async def get_record(self, quarantine_id: str, db: Optional[AsyncSession] = None) -> Optional[QuarantineRecord]:
        async with self._best_effort_db(db) as session:
            if session is not None:
                item = await session.get(GeneticQuarantineRecordModel, quarantine_id)
                return _to_record(item) if item else None
        for item in self._records:
            if item.quarantine_id == quarantine_id:
                return item
        return None

    async def _append_audit(
        self,
        *,
        quarantine_id: str,
        event_type: str,
        action: str,
        actor: str,
        details: dict,
        correlation_id: Optional[str],
        db: Optional[AsyncSession],
    ) -> None:
        audit = QuarantineAuditEntry(
            audit_id=f"gqa_{uuid.uuid4().hex[:12]}",
            quarantine_id=quarantine_id,
            event_type=event_type,
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
                    GeneticQuarantineAuditModel(
                        audit_id=audit.audit_id,
                        quarantine_id=audit.quarantine_id,
                        event_type=audit.event_type,
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
            self._audits.append(audit)

        await write_unified_audit(
            event_type=event_type,
            action=f"genetic_quarantine.{action}",
            actor=actor,
            actor_type="system",
            resource_type="genetic_quarantine",
            resource_id=quarantine_id,
            severity="warning",
            message=f"Quarantine {action} for {quarantine_id}",
            correlation_id=correlation_id,
            details=details,
            db=db,
        )

    async def _publish_event(self, record: QuarantineRecord, *, action: str) -> None:
        if self.event_stream is None:
            return
        try:
            from mission_control_core.core import Event

            payload = build_runtime_event_payload(
                event_type="genetic_quarantine.state_changed",
                severity=EventSeverity.WARNING if record.state in {QuarantineState.QUARANTINED, QuarantineState.REJECTED} else EventSeverity.INFO,
                source="genetic_quarantine",
                entity=record.agent_id,
                correlation_id=record.correlation_id,
                data={
                    "quarantine_id": record.quarantine_id,
                    "state": record.state.value,
                    "previous_state": record.previous_state.value if record.previous_state else None,
                    "snapshot_version": record.snapshot_version,
                    "action": action,
                },
            )
            event = build_event_instance(
                Event,
                event_type="genetic_quarantine.state_changed",
                source="genetic_quarantine",
                payload=payload,
                correlation_id=record.correlation_id,
            )
            await self.event_stream.publish(event)
        except Exception:
            return


_service: Optional[GeneticQuarantineService] = None


def get_genetic_quarantine_service(event_stream: Optional["EventStream"] = None) -> GeneticQuarantineService:
    global _service
    if _service is None:
        _service = GeneticQuarantineService(event_stream=event_stream)
        return _service
    if event_stream is not None and _service.event_stream is None:
        _service.event_stream = event_stream
    return _service
