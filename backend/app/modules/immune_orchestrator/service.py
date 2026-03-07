"""Service layer for the Immune Orchestrator module."""

from __future__ import annotations

import uuid
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List, Optional

from loguru import logger
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_bridge import write_unified_audit
from app.core.event_contract import EventSeverity, build_event_instance, build_runtime_event_payload
from app.modules.immune_orchestrator.models import ImmuneAuditModel, ImmuneDecisionModel, ImmuneSignalModel
from app.modules.immune_orchestrator.playbook_registry import PlaybookRegistry
from app.modules.immune_orchestrator.priority_engine import PriorityEngine
from app.modules.immune_orchestrator.schemas import (
    DecisionAction,
    ImmuneAuditEntry,
    ImmuneDecision,
    ImmuneMetrics,
    IncidentSignal,
    SignalSeverity,
)

try:
    from mission_control_core.core import EventStream, Event
except ImportError:  # pragma: no cover
    EventStream = None
    Event = None


class ImmuneOrchestratorService:
    """Central decision layer for runtime incidents."""

    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self.event_stream = event_stream
        self.priority_engine = PriorityEngine()
        self.playbooks = PlaybookRegistry()
        self._signals: List[IncidentSignal] = []
        self._decisions: List[ImmuneDecision] = []
        self._audit_entries: List[ImmuneAuditEntry] = []
        self._repair_trigger: Optional[Callable[[dict], Awaitable[None]]] = None

    def set_repair_trigger(self, trigger: Callable[[dict], Awaitable[None]]) -> None:
        self._repair_trigger = trigger

    @staticmethod
    def _naive_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    async def ingest_signal(self, signal: IncidentSignal, db: AsyncSession | None = None) -> ImmuneDecision:
        priority_score = self.priority_engine.score(signal)
        action = self.playbooks.choose_action(priority_score, signal.severity, signal.recurrence)

        decision = ImmuneDecision(
            decision_id=f"imdec-{uuid.uuid4().hex[:12]}",
            signal_id=signal.id,
            action=action,
            priority_score=priority_score,
            reason=self._reason_for(action, signal, priority_score),
            requires_governance_hook=action in {DecisionAction.ISOLATE, DecisionAction.ESCALATE},
            correlation_id=signal.correlation_id,
        )

        self._signals.append(signal)
        self._decisions.append(decision)

        await self._persist_signal_and_decision(signal=signal, decision=decision, db=db)
        await self._emit_decision_event(signal, decision)
        await self._append_audit(signal, decision, db=db)
        await self._trigger_repair_if_needed(signal, decision)

        logger.info(
            "[ImmuneOrchestrator] decision=%s signal=%s source=%s score=%.3f",
            decision.action.value,
            signal.id,
            signal.source,
            decision.priority_score,
        )
        return decision

    async def list_signals(self, db: AsyncSession | None = None) -> List[IncidentSignal]:
        if db is None:
            return list(self._signals)
        rows = await self._fetch_all_signals(db=db)
        if rows:
            return rows
        return list(self._signals)

    async def list_decisions(self, db: AsyncSession | None = None) -> List[ImmuneDecision]:
        if db is None:
            return list(self._decisions)
        rows = await self._fetch_all_decisions(db=db)
        if rows:
            return rows
        return list(self._decisions)

    async def list_audit_entries(self, db: AsyncSession | None = None) -> List[ImmuneAuditEntry]:
        if db is None:
            return list(self._audit_entries)
        rows = await self._fetch_all_audit_entries(db=db)
        if rows:
            return rows
        return list(self._audit_entries)

    async def metrics(self, db: AsyncSession | None = None) -> ImmuneMetrics:
        signals = await self.list_signals(db=db)
        decisions = await self.list_decisions(db=db)
        action_counter = Counter([decision.action.value for decision in decisions])
        source_counter = Counter([signal.source for signal in signals])
        return ImmuneMetrics(
            total_signals=len(signals),
            total_decisions=len(decisions),
            actions=dict(action_counter),
            by_source=dict(source_counter),
        )

    async def _append_audit(self, signal: IncidentSignal, decision: ImmuneDecision, db: AsyncSession | None) -> None:
        entry = ImmuneAuditEntry(
            audit_id=f"imaud-{uuid.uuid4().hex[:12]}",
            event_type="immune.decision",
            actor="immune_orchestrator",
            action=decision.action.value,
            severity=signal.severity,
            resource_type="incident_signal",
            resource_id=signal.id,
            correlation_id=signal.correlation_id,
            details={
                "source": signal.source,
                "type": signal.type,
                "entity": signal.entity,
                "priority_score": decision.priority_score,
                "decision_id": decision.decision_id,
                "requires_governance_hook": decision.requires_governance_hook,
            },
        )
        self._audit_entries.append(entry)

        await self._persist_audit_entry(entry, db=db)

        await write_unified_audit(
            event_type="immune.decision",
            action=decision.action.value,
            actor="immune_orchestrator",
            actor_type="system",
            resource_type="incident_signal",
            resource_id=signal.id,
            severity=signal.severity.value,
            message=decision.reason,
            correlation_id=signal.correlation_id,
            details={
                "decision_id": decision.decision_id,
                "incident_id": signal.id,
                "priority_score": decision.priority_score,
                "requires_governance_hook": decision.requires_governance_hook,
            },
            db=db,
        )

    async def _emit_decision_event(self, signal: IncidentSignal, decision: ImmuneDecision) -> None:
        if self.event_stream is None or Event is None:
            return
        try:
            payload = build_runtime_event_payload(
                event_type="immune.decision",
                severity=(
                    EventSeverity.CRITICAL
                    if signal.severity == SignalSeverity.CRITICAL
                    else EventSeverity.WARNING
                    if signal.severity == SignalSeverity.WARNING
                    else EventSeverity.INFO
                ),
                source="immune_orchestrator",
                entity=signal.entity,
                correlation_id=signal.correlation_id,
                data={
                    "decision_id": decision.decision_id,
                    "incident_id": signal.id,
                    "signal_source": signal.source,
                    "signal_type": signal.type,
                    "priority_score": decision.priority_score,
                    "action": decision.action.value,
                    "requires_governance_hook": decision.requires_governance_hook,
                },
            )

            event = build_event_instance(
                Event,
                event_type="immune.decision",
                source="immune_orchestrator",
                payload=payload,
                correlation_id=signal.correlation_id,
            )
            await self.event_stream.publish(event)
        except Exception as exc:  # pragma: no cover
            logger.error("[ImmuneOrchestrator] event publish failed: %s", exc)

    async def _trigger_repair_if_needed(self, signal: IncidentSignal, decision: ImmuneDecision) -> None:
        if self._repair_trigger is None:
            return
        if decision.action not in {DecisionAction.ISOLATE, DecisionAction.ESCALATE}:
            return
        try:
            await self._repair_trigger(
                {
                    "source_module": "immune_orchestrator",
                    "source_event_type": "immune.decision",
                    "subject_id": signal.id,
                    "summary": decision.reason,
                    "severity": "high" if decision.action == DecisionAction.ISOLATE else "critical",
                    "correlation_id": signal.correlation_id,
                    "context": {
                        "signal_id": signal.id,
                        "action": decision.action.value,
                        "priority_score": decision.priority_score,
                    },
                    "actor": "immune_orchestrator",
                }
            )
        except Exception:
            return

    async def _persist_signal_and_decision(
        self,
        *,
        signal: IncidentSignal,
        decision: ImmuneDecision,
        db: AsyncSession | None,
    ) -> None:
        async with self._session(db) as session:
            if session is None:
                return
            try:
                signal_model = ImmuneSignalModel(
                    id=signal.id,
                    type=signal.type,
                    source=signal.source,
                    severity=signal.severity.value,
                    entity=signal.entity,
                    timestamp=self._naive_utc(signal.timestamp),
                    context=signal.context,
                    correlation_id=signal.correlation_id,
                    blast_radius=signal.blast_radius,
                    confidence=signal.confidence,
                    recurrence=signal.recurrence,
                )
                decision_model = ImmuneDecisionModel(
                    decision_id=decision.decision_id,
                    signal_id=decision.signal_id,
                    action=decision.action.value,
                    priority_score=decision.priority_score,
                    reason=decision.reason,
                    requires_governance_hook="true" if decision.requires_governance_hook else "false",
                    correlation_id=decision.correlation_id,
                    created_at=self._naive_utc(decision.created_at),
                )
                session.add(signal_model)
                session.add(decision_model)
                await session.commit()
            except Exception as exc:
                logger.warning("[ImmuneOrchestrator] persistence fallback to memory: %s", exc)

    async def _persist_audit_entry(self, entry: ImmuneAuditEntry, db: AsyncSession | None) -> None:
        async with self._session(db) as session:
            if session is None:
                return
            try:
                session.add(
                    ImmuneAuditModel(
                        audit_id=entry.audit_id,
                        event_type=entry.event_type,
                        actor=entry.actor,
                        action=entry.action,
                        severity=entry.severity.value,
                        resource_type=entry.resource_type,
                        resource_id=entry.resource_id,
                        correlation_id=entry.correlation_id,
                        details=entry.details,
                        timestamp=self._naive_utc(entry.timestamp),
                    )
                )
                await session.commit()
            except Exception as exc:
                logger.warning("[ImmuneOrchestrator] audit persistence fallback to memory: %s", exc)

    async def _fetch_all_signals(self, db: AsyncSession | None) -> List[IncidentSignal]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                result = await session.execute(select(ImmuneSignalModel).order_by(desc(ImmuneSignalModel.created_at)))
                rows = result.scalars().all()
                return [
                    IncidentSignal(
                        id=row.id,
                        type=row.type,
                        source=row.source,
                        severity=SignalSeverity(row.severity),
                        entity=row.entity,
                        timestamp=row.timestamp,
                        context=row.context or {},
                        correlation_id=row.correlation_id,
                        blast_radius=row.blast_radius,
                        confidence=row.confidence,
                        recurrence=row.recurrence,
                    )
                    for row in rows
                ]
            except Exception:
                return []

    async def _fetch_all_decisions(self, db: AsyncSession | None) -> List[ImmuneDecision]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                result = await session.execute(select(ImmuneDecisionModel).order_by(desc(ImmuneDecisionModel.created_at)))
                rows = result.scalars().all()
                return [
                    ImmuneDecision(
                        decision_id=row.decision_id,
                        signal_id=row.signal_id,
                        action=DecisionAction(row.action),
                        priority_score=row.priority_score,
                        reason=row.reason,
                        requires_governance_hook=(row.requires_governance_hook == "true"),
                        created_at=row.created_at,
                        correlation_id=row.correlation_id,
                    )
                    for row in rows
                ]
            except Exception:
                return []

    async def _fetch_all_audit_entries(self, db: AsyncSession | None) -> List[ImmuneAuditEntry]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                result = await session.execute(select(ImmuneAuditModel).order_by(desc(ImmuneAuditModel.timestamp)))
                rows = result.scalars().all()
                return [
                    ImmuneAuditEntry(
                        audit_id=row.audit_id,
                        event_type=row.event_type,
                        actor=row.actor,
                        action=row.action,
                        severity=SignalSeverity(row.severity),
                        resource_type=row.resource_type,
                        resource_id=row.resource_id,
                        correlation_id=row.correlation_id,
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

    @staticmethod
    def _reason_for(action: DecisionAction, signal: IncidentSignal, score: float) -> str:
        if action == DecisionAction.ESCALATE:
            return f"Critical escalation due to score={score:.2f}, recurrence={signal.recurrence}"
        if action == DecisionAction.ISOLATE:
            return f"Isolation selected for critical signal with score={score:.2f}"
        if action == DecisionAction.MITIGATE:
            return f"Mitigation selected due to elevated risk score={score:.2f}"
        if action == DecisionAction.WARN:
            return f"Warning issued for moderate signal score={score:.2f}"
        return "Observed for monitoring; no immediate mitigation required"


_service: Optional[ImmuneOrchestratorService] = None


def get_immune_orchestrator_service(event_stream: Optional["EventStream"] = None) -> ImmuneOrchestratorService:
    global _service
    if _service is None:
        _service = ImmuneOrchestratorService(event_stream=event_stream)
    elif event_stream is not None and _service.event_stream is None:
        _service.event_stream = event_stream
    return _service
