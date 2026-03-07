"""Service layer for Genetic Integrity."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from loguru import logger
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_bridge import write_unified_audit
from app.core.event_contract import EventSeverity, build_event_instance, build_runtime_event_payload
from app.modules.genetic_integrity.models import GeneticAuditModel, GeneticMutationAuditModel, GeneticSnapshotRecordModel
from app.modules.genetic_integrity.hashing import snapshot_hash
from app.modules.genetic_integrity.schemas import (
    GeneticAuditEntry,
    GeneticIntegrityRecord,
    GeneticMetrics,
    MutationAuditRecord,
    MutationAuditRequest,
    RegisterSnapshotRequest,
    VerificationResult,
)
from app.modules.genetic_integrity.verification import verify_snapshot_record

try:
    from mission_control_core.core import EventStream, Event
except ImportError:  # pragma: no cover
    EventStream = None
    Event = None


class GeneticIntegrityService:
    """Canonical hashing and mutation audit trail for DNA snapshots."""

    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self.event_stream = event_stream
        self._records: Dict[Tuple[str, int], GeneticIntegrityRecord] = {}
        self._mutation_audit: List[MutationAuditRecord] = []
        self._audit_entries: List[GeneticAuditEntry] = []

    @staticmethod
    def _naive_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    async def register_snapshot(self, request: RegisterSnapshotRequest, db: AsyncSession | None = None) -> GeneticIntegrityRecord:
        parent_hash = None
        if request.parent_snapshot is not None:
            parent = self._records.get((request.agent_id, request.parent_snapshot))
            if parent is not None:
                parent_hash = parent.payload_hash

        digest = snapshot_hash(
            agent_id=request.agent_id,
            snapshot_version=request.snapshot_version,
            parent_snapshot=request.parent_snapshot,
            dna_payload=request.dna_payload,
        )

        record = GeneticIntegrityRecord(
            record_id=f"genrec-{uuid.uuid4().hex[:12]}",
            agent_id=request.agent_id,
            snapshot_version=request.snapshot_version,
            parent_snapshot=request.parent_snapshot,
            payload_hash=digest,
            parent_hash=parent_hash,
            correlation_id=request.correlation_id,
        )

        self._records[(request.agent_id, request.snapshot_version)] = record
        await self._persist_snapshot_record(record, db=db)
        await self._append_audit(
            event_type="genetic_integrity.snapshot_registered",
            action="register_snapshot",
            resource_type="dna_snapshot",
            resource_id=f"{request.agent_id}:{request.snapshot_version}",
            details={
                "record_id": record.record_id,
                "parent_snapshot": request.parent_snapshot,
                "parent_hash": parent_hash,
                "correlation_id": request.correlation_id,
            },
            db=db,
        )
        await self._emit_snapshot_event(record)

        await write_unified_audit(
            event_type="genetic_integrity.snapshot_registered",
            action="register_snapshot",
            actor="genetic_integrity_service",
            actor_type="system",
            resource_type="dna_snapshot",
            resource_id=f"{request.agent_id}:{request.snapshot_version}",
            severity="info",
            message="DNA snapshot integrity registered",
            correlation_id=request.correlation_id,
            details={
                "record_id": record.record_id,
                "payload_hash": record.payload_hash,
                "parent_snapshot": request.parent_snapshot,
            },
            db=db,
        )

        return record

    async def get_snapshot_record(
        self,
        agent_id: str,
        snapshot_version: int,
        db: AsyncSession | None = None,
    ) -> Optional[GeneticIntegrityRecord]:
        db_record = await self._fetch_snapshot_record(agent_id, snapshot_version, db=db)
        if db_record is not None:
            return db_record
        return self._records.get((agent_id, snapshot_version))

    async def list_snapshot_records(
        self,
        agent_id: Optional[str] = None,
        db: AsyncSession | None = None,
    ) -> List[GeneticIntegrityRecord]:
        if db is None:
            values = list(self._records.values())
            if agent_id is None:
                return values
            return [item for item in values if item.agent_id == agent_id]
        rows = await self._fetch_snapshot_records(agent_id=agent_id, db=db)
        if rows:
            return rows
        values = list(self._records.values())
        if agent_id is None:
            return values
        return [item for item in values if item.agent_id == agent_id]

    async def verify_snapshot(
        self,
        agent_id: str,
        snapshot_version: int,
        dna_payload: dict,
        db: AsyncSession | None = None,
    ) -> VerificationResult:
        record = await self.get_snapshot_record(agent_id, snapshot_version, db=db)
        if record is None:
            return VerificationResult(
                agent_id=agent_id,
                snapshot_version=snapshot_version,
                valid=False,
                expected_hash=None,
                computed_hash=None,
            )
        return verify_snapshot_record(record, dna_payload)

    async def record_mutation(self, request: MutationAuditRequest, db: AsyncSession | None = None) -> MutationAuditRecord:
        mutation_record = MutationAuditRecord(
            audit_id=f"genmut-{uuid.uuid4().hex[:12]}",
            agent_id=request.agent_id,
            from_version=request.from_version,
            to_version=request.to_version,
            actor=request.actor,
            reason=request.reason,
            mutation=request.mutation,
            requires_governance_hook=request.requires_governance_hook,
            correlation_id=request.correlation_id,
        )
        self._mutation_audit.append(mutation_record)
        await self._persist_mutation_record(mutation_record, db=db)

        await self._append_audit(
            event_type="genetic_integrity.mutation_recorded",
            action="record_mutation",
            resource_type="dna_mutation",
            resource_id=f"{request.agent_id}:{request.from_version}->{request.to_version}",
            details={
                "actor": request.actor,
                "reason": request.reason,
                "requires_governance_hook": request.requires_governance_hook,
                "correlation_id": request.correlation_id,
            },
            db=db,
        )
        await self._emit_mutation_event(mutation_record)

        await write_unified_audit(
            event_type="genetic_integrity.mutation_recorded",
            action="record_mutation",
            actor="genetic_integrity_service",
            actor_type="system",
            resource_type="dna_mutation",
            resource_id=f"{request.agent_id}:{request.from_version}->{request.to_version}",
            severity=("warning" if request.requires_governance_hook else "info"),
            message=request.reason,
            correlation_id=request.correlation_id,
            details={
                "mutation_id": mutation_record.audit_id,
                "requires_governance_hook": request.requires_governance_hook,
            },
            db=db,
        )

        return mutation_record

    async def list_mutation_audit(self, db: AsyncSession | None = None) -> List[MutationAuditRecord]:
        if db is None:
            return list(self._mutation_audit)
        rows = await self._fetch_mutations(db=db)
        if rows:
            return rows
        return list(self._mutation_audit)

    async def list_audit_entries(self, db: AsyncSession | None = None) -> List[GeneticAuditEntry]:
        if db is None:
            return list(self._audit_entries)
        rows = await self._fetch_audit_entries(db=db)
        if rows:
            return rows
        return list(self._audit_entries)

    async def metrics(self, db: AsyncSession | None = None) -> GeneticMetrics:
        snapshots = await self.list_snapshot_records(db=db)
        mutations = await self.list_mutation_audit(db=db)
        governance_hooks = sum(1 for record in mutations if record.requires_governance_hook)
        return GeneticMetrics(
            total_snapshots=len(snapshots),
            total_mutations=len(mutations),
            governance_hooks=governance_hooks,
        )

    async def register_from_dna_snapshot(
        self,
        *,
        agent_id: str,
        snapshot_version: int,
        parent_snapshot: Optional[int],
        dna_payload: dict,
        correlation_id: Optional[str] = None,
        db: AsyncSession | None = None,
    ) -> GeneticIntegrityRecord:
        """Integration helper for DNA/Genesis modules."""
        return await self.register_snapshot(
            RegisterSnapshotRequest(
                agent_id=agent_id,
                snapshot_version=snapshot_version,
                parent_snapshot=parent_snapshot,
                dna_payload=dna_payload,
                correlation_id=correlation_id,
                source="dna",
            ),
            db=db,
        )

    async def _append_audit(
        self,
        *,
        event_type: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: dict,
        db: AsyncSession | None,
    ) -> None:
        entry = GeneticAuditEntry(
            audit_id=f"genaud-{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
        )
        self._audit_entries.append(entry)
        await self._persist_audit_entry(entry, db=db)

    async def _emit_snapshot_event(self, record: GeneticIntegrityRecord) -> None:
        if self.event_stream is None or Event is None:
            return
        try:
            payload = build_runtime_event_payload(
                event_type="genetic_integrity.snapshot_registered",
                severity=EventSeverity.INFO,
                source="genetic_integrity_service",
                entity=record.agent_id,
                correlation_id=record.correlation_id,
                data={
                    "record_id": record.record_id,
                    "snapshot_version": record.snapshot_version,
                    "parent_snapshot": record.parent_snapshot,
                    "payload_hash": record.payload_hash,
                },
            )
            await self.event_stream.publish(
                build_event_instance(
                    Event,
                    event_type="genetic_integrity.snapshot_registered",
                    source="genetic_integrity_service",
                    payload=payload,
                    correlation_id=record.correlation_id,
                )
            )
        except Exception as exc:  # pragma: no cover
            logger.error("[GeneticIntegrity] snapshot event publish failed: %s", exc)

    async def _emit_mutation_event(self, record: MutationAuditRecord) -> None:
        if self.event_stream is None or Event is None:
            return
        try:
            payload = build_runtime_event_payload(
                event_type="genetic_integrity.mutation_recorded",
                severity=(EventSeverity.WARNING if record.requires_governance_hook else EventSeverity.INFO),
                source="genetic_integrity_service",
                entity=record.agent_id,
                correlation_id=record.correlation_id,
                data={
                    "mutation_id": record.audit_id,
                    "from_version": record.from_version,
                    "to_version": record.to_version,
                    "actor": record.actor,
                    "reason": record.reason,
                    "requires_governance_hook": record.requires_governance_hook,
                },
            )
            await self.event_stream.publish(
                build_event_instance(
                    Event,
                    event_type="genetic_integrity.mutation_recorded",
                    source="genetic_integrity_service",
                    payload=payload,
                    correlation_id=record.correlation_id,
                )
            )
        except Exception as exc:  # pragma: no cover
            logger.error("[GeneticIntegrity] mutation event publish failed: %s", exc)

    async def _persist_snapshot_record(self, record: GeneticIntegrityRecord, db: AsyncSession | None) -> None:
        async with self._session(db) as session:
            if session is None:
                return
            try:
                session.add(
                    GeneticSnapshotRecordModel(
                        record_id=record.record_id,
                        agent_id=record.agent_id,
                        snapshot_version=record.snapshot_version,
                        parent_snapshot=record.parent_snapshot,
                        payload_hash=record.payload_hash,
                        parent_hash=record.parent_hash,
                        correlation_id=record.correlation_id,
                        created_at=self._naive_utc(record.created_at),
                    )
                )
                await session.commit()
            except Exception as exc:
                logger.warning("[GeneticIntegrity] snapshot persistence fallback to memory: %s", exc)

    async def _persist_mutation_record(self, record: MutationAuditRecord, db: AsyncSession | None) -> None:
        async with self._session(db) as session:
            if session is None:
                return
            try:
                session.add(
                    GeneticMutationAuditModel(
                        audit_id=record.audit_id,
                        agent_id=record.agent_id,
                        from_version=record.from_version,
                        to_version=record.to_version,
                        actor=record.actor,
                        reason=record.reason,
                        mutation=record.mutation,
                        requires_governance_hook="true" if record.requires_governance_hook else "false",
                        correlation_id=record.correlation_id,
                        created_at=self._naive_utc(record.created_at),
                    )
                )
                await session.commit()
            except Exception as exc:
                logger.warning("[GeneticIntegrity] mutation persistence fallback to memory: %s", exc)

    async def _persist_audit_entry(self, entry: GeneticAuditEntry, db: AsyncSession | None) -> None:
        async with self._session(db) as session:
            if session is None:
                return
            try:
                session.add(
                    GeneticAuditModel(
                        audit_id=entry.audit_id,
                        event_type=entry.event_type,
                        action=entry.action,
                        resource_type=entry.resource_type,
                        resource_id=entry.resource_id,
                        details=entry.details,
                        timestamp=self._naive_utc(entry.timestamp),
                    )
                )
                await session.commit()
            except Exception as exc:
                logger.warning("[GeneticIntegrity] audit persistence fallback to memory: %s", exc)

    async def _fetch_snapshot_record(
        self,
        agent_id: str,
        snapshot_version: int,
        db: AsyncSession | None,
    ) -> Optional[GeneticIntegrityRecord]:
        async with self._session(db) as session:
            if session is None:
                return None
            try:
                result = await session.execute(
                    select(GeneticSnapshotRecordModel).where(
                        GeneticSnapshotRecordModel.agent_id == agent_id,
                        GeneticSnapshotRecordModel.snapshot_version == snapshot_version,
                    )
                )
                row = result.scalar_one_or_none()
                if row is None:
                    return None
                return GeneticIntegrityRecord(
                    record_id=row.record_id,
                    agent_id=row.agent_id,
                    snapshot_version=row.snapshot_version,
                    parent_snapshot=row.parent_snapshot,
                    payload_hash=row.payload_hash,
                    parent_hash=row.parent_hash,
                    correlation_id=row.correlation_id,
                    created_at=row.created_at,
                )
            except Exception:
                return None

    async def _fetch_snapshot_records(
        self,
        *,
        agent_id: Optional[str],
        db: AsyncSession | None,
    ) -> List[GeneticIntegrityRecord]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                query = select(GeneticSnapshotRecordModel).order_by(desc(GeneticSnapshotRecordModel.created_at))
                if agent_id is not None:
                    query = query.where(GeneticSnapshotRecordModel.agent_id == agent_id)
                result = await session.execute(query)
                rows = result.scalars().all()
                return [
                    GeneticIntegrityRecord(
                        record_id=row.record_id,
                        agent_id=row.agent_id,
                        snapshot_version=row.snapshot_version,
                        parent_snapshot=row.parent_snapshot,
                        payload_hash=row.payload_hash,
                        parent_hash=row.parent_hash,
                        correlation_id=row.correlation_id,
                        created_at=row.created_at,
                    )
                    for row in rows
                ]
            except Exception:
                return []

    async def _fetch_mutations(self, db: AsyncSession | None) -> List[MutationAuditRecord]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                result = await session.execute(select(GeneticMutationAuditModel).order_by(desc(GeneticMutationAuditModel.created_at)))
                rows = result.scalars().all()
                return [
                    MutationAuditRecord(
                        audit_id=row.audit_id,
                        agent_id=row.agent_id,
                        from_version=row.from_version,
                        to_version=row.to_version,
                        actor=row.actor,
                        reason=row.reason,
                        mutation=row.mutation or {},
                        requires_governance_hook=(row.requires_governance_hook == "true"),
                        correlation_id=row.correlation_id,
                        created_at=row.created_at,
                    )
                    for row in rows
                ]
            except Exception:
                return []

    async def _fetch_audit_entries(self, db: AsyncSession | None) -> List[GeneticAuditEntry]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                result = await session.execute(select(GeneticAuditModel).order_by(desc(GeneticAuditModel.timestamp)))
                rows = result.scalars().all()
                return [
                    GeneticAuditEntry(
                        audit_id=row.audit_id,
                        event_type=row.event_type,
                        action=row.action,
                        resource_type=row.resource_type,
                        resource_id=row.resource_id,
                        details=row.details or {},
                        timestamp=row.timestamp,
                    )
                    for row in rows
                ]
            except Exception:
                return []

    @asynccontextmanager
    async def _session(self, db: AsyncSession | None):
        if db is not None:
            yield db
            return
        yield None


_service: Optional[GeneticIntegrityService] = None


def get_genetic_integrity_service(event_stream: Optional["EventStream"] = None) -> GeneticIntegrityService:
    global _service
    if _service is None:
        _service = GeneticIntegrityService(event_stream=event_stream)
    elif event_stream is not None and _service.event_stream is None:
        _service.event_stream = event_stream
    return _service
