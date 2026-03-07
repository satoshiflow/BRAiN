"""Service layer for Unified Recovery Policy Engine."""

from __future__ import annotations

import uuid
import inspect
import time
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List, Optional

from loguru import logger
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit_bridge import write_unified_audit
from app.core.event_contract import EventSeverity, build_event_instance, build_runtime_event_payload
from app.modules.recovery_policy_engine.adapters import (
    neurorail_adapter,
    planning_adapter,
    task_queue_adapter,
)
from app.modules.recovery_policy_engine.policy_engine import RecoveryPolicyEngine
from app.modules.recovery_policy_engine.schemas import (
    RecoveryAuditEntry,
    RecoveryDecision,
    RecoveryMetrics,
    RecoveryPolicyConfig,
    RecoveryRequest,
    RecoverySeverity,
    RecoveryStrategy,
)
from app.modules.recovery_policy_engine.models import (
    RecoveryAuditModel,
    RecoveryDecisionModel,
    RecoveryRequestModel,
)

try:
    from mission_control_core.core import EventStream, Event
except ImportError:  # pragma: no cover
    EventStream = None
    Event = None


class RecoveryPolicyService:
    """Central decision point for runtime recovery actions."""

    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self.event_stream = event_stream
        self.policy = RecoveryPolicyConfig()
        self.engine = RecoveryPolicyEngine()
        self._requests: List[RecoveryRequest] = []
        self._decisions: List[RecoveryDecision] = []
        self._audit_entries: List[RecoveryAuditEntry] = []
        self._repair_trigger: Optional[Callable[[dict], Awaitable[None]]] = None
        self._adapters: Dict[str, Callable[[dict], RecoveryRequest]] = {
            "planning": planning_adapter.from_payload,
            "neurorail": neurorail_adapter.from_payload,
            "task_queue": task_queue_adapter.from_payload,
        }

    def set_repair_trigger(self, trigger: Callable[[dict], Awaitable[None]]) -> None:
        self._repair_trigger = trigger

    @staticmethod
    def _naive_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    async def decide(self, request: RecoveryRequest, db: AsyncSession | None = None) -> RecoveryDecision:
        action = self.engine.decide(request, self.policy)
        decision = RecoveryDecision(
            decision_id=f"recdec-{uuid.uuid4().hex[:12]}",
            request_id=request.id,
            action=action,
            reason=self._reason_for(action, request),
            cooldown_seconds=self.policy.cooldown_seconds,
            requires_governance_hook=action in {
                RecoveryStrategy.ISOLATE,
                RecoveryStrategy.ESCALATE,
                RecoveryStrategy.ROLLBACK,
            },
            correlation_id=request.correlation_id,
        )

        self._requests.append(request)
        self._decisions.append(decision)

        await self._persist_request_and_decision(request=request, decision=decision, db=db)
        await self._append_audit(request, decision, db=db)
        await self._emit_action_event(request, decision)
        await self._trigger_repair_if_needed(request, decision)

        logger.info(
            "[RecoveryPolicy] source=%s request=%s action=%s",
            request.source,
            request.id,
            decision.action.value,
        )
        return decision

    async def decide_from_adapter(self, adapter_name: str, payload: dict, db: AsyncSession | None = None) -> RecoveryDecision:
        request = self.build_request_from_adapter(adapter_name, payload)
        return await self.decide(request, db=db)

    def build_request_from_adapter(self, adapter_name: str, payload: dict) -> RecoveryRequest:
        adapter = self._adapters.get(adapter_name)
        if adapter is None:
            raise ValueError(f"Unknown adapter: {adapter_name}")
        return adapter(payload)

    def update_policy(self, config: RecoveryPolicyConfig) -> RecoveryPolicyConfig:
        self.policy = config
        return self.policy

    def get_policy(self) -> RecoveryPolicyConfig:
        return self.policy

    async def list_decisions(self, db: AsyncSession | None = None) -> List[RecoveryDecision]:
        if db is None:
            return list(self._decisions)
        rows = await self._fetch_all_decisions(db=db)
        if rows:
            return rows
        return list(self._decisions)

    async def list_audit_entries(self, db: AsyncSession | None = None) -> List[RecoveryAuditEntry]:
        if db is None:
            return list(self._audit_entries)
        rows = await self._fetch_all_audits(db=db)
        if rows:
            return rows
        return list(self._audit_entries)

    async def metrics(self, db: AsyncSession | None = None) -> RecoveryMetrics:
        if db is None:
            decisions = list(self._decisions)
            by_action = Counter([d.action.value for d in decisions])
            by_source = Counter([r.source for r in self._requests])
            return RecoveryMetrics(
                total_requests=len(self._requests),
                total_decisions=len(decisions),
                by_action=dict(by_action),
                by_source=dict(by_source),
            )
        decisions = await self.list_decisions(db=db)
        by_action = Counter([d.action.value for d in decisions])
        requests = await self._fetch_all_requests(db=db)
        if not requests:
            requests = list(self._requests)
        by_source = Counter([r.source for r in requests])
        return RecoveryMetrics(
            total_requests=len(requests),
            total_decisions=len(decisions),
            by_action=dict(by_action),
            by_source=dict(by_source),
        )

    async def _append_audit(self, request: RecoveryRequest, decision: RecoveryDecision, db: AsyncSession | None) -> None:
        entry = RecoveryAuditEntry(
                audit_id=f"recaud-{uuid.uuid4().hex[:12]}",
                event_type="recovery.action",
                actor="recovery_policy_engine",
                action=decision.action.value,
                request_id=request.id,
                correlation_id=request.correlation_id,
                details={
                    "source": request.source,
                    "entity_id": request.entity_id,
                    "failure_type": request.failure_type,
                    "retry_count": request.retry_count,
                    "recurrence": request.recurrence,
                    "requires_governance_hook": decision.requires_governance_hook,
                },
            )
        self._audit_entries.append(entry)

        await self._persist_audit_entry(entry, db=db)
        await write_unified_audit(
            event_type="recovery.action",
            action=decision.action.value,
            actor="recovery_policy_engine",
            actor_type="system",
            resource_type="recovery_request",
            resource_id=request.id,
            severity=("critical" if decision.requires_governance_hook else "warning"),
            message=decision.reason,
            correlation_id=request.correlation_id,
            details={
                "decision_id": decision.decision_id,
                "request_id": request.id,
                "requires_governance_hook": decision.requires_governance_hook,
            },
            db=db,
        )

    async def _emit_action_event(self, request: RecoveryRequest, decision: RecoveryDecision) -> None:
        if self.event_stream is None or Event is None:
            return
        try:
            payload = build_runtime_event_payload(
                event_type="recovery.action",
                severity=(
                    EventSeverity.CRITICAL
                    if decision.requires_governance_hook
                    else EventSeverity.WARNING
                ),
                source="recovery_policy_engine",
                entity=request.entity_id,
                correlation_id=request.correlation_id,
                data={
                    "decision_id": decision.decision_id,
                    "request_id": request.id,
                    "source": request.source,
                    "failure_type": request.failure_type,
                    "severity": request.severity.value,
                    "action": decision.action.value,
                    "reason": decision.reason,
                    "requires_governance_hook": decision.requires_governance_hook,
                },
            )
            event = build_event_instance(
                Event,
                event_type="recovery.action",
                source="recovery_policy_engine",
                payload=payload,
                correlation_id=request.correlation_id,
            )
            await self.event_stream.publish(event)
        except Exception as exc:  # pragma: no cover
            logger.error("[RecoveryPolicy] event publish failed: %s", exc)

    async def _trigger_repair_if_needed(self, request: RecoveryRequest, decision: RecoveryDecision) -> None:
        if self._repair_trigger is None:
            return
        if decision.action not in {
            RecoveryStrategy.ESCALATE,
            RecoveryStrategy.ISOLATE,
            RecoveryStrategy.ROLLBACK,
        }:
            return
        try:
            severity = "critical" if decision.action == RecoveryStrategy.ESCALATE else "high"
            await self._repair_trigger(
                {
                    "source_module": "recovery_policy_engine",
                    "source_event_type": "recovery.action",
                    "subject_id": request.id,
                    "summary": decision.reason,
                    "severity": severity,
                    "correlation_id": request.correlation_id,
                    "context": {
                        "request_id": request.id,
                        "entity_id": request.entity_id,
                        "action": decision.action.value,
                        "failure_type": request.failure_type,
                    },
                    "actor": "recovery_policy_engine",
                }
            )
        except Exception:
            return

    async def _persist_request_and_decision(
        self,
        *,
        request: RecoveryRequest,
        decision: RecoveryDecision,
        db: AsyncSession | None,
    ) -> None:
        async with self._session(db) as session:
            if session is None:
                return
            try:
                session.add(
                    RecoveryRequestModel(
                        id=request.id,
                        source=request.source,
                        entity_id=request.entity_id,
                        failure_type=request.failure_type,
                        severity=request.severity.value,
                        retry_count=request.retry_count,
                        recurrence=request.recurrence,
                        context=request.context,
                        correlation_id=request.correlation_id,
                        timestamp=self._naive_utc(request.timestamp),
                    )
                )
                session.add(
                    RecoveryDecisionModel(
                        decision_id=decision.decision_id,
                        request_id=decision.request_id,
                        action=decision.action.value,
                        reason=decision.reason,
                        cooldown_seconds=decision.cooldown_seconds,
                        requires_governance_hook="true" if decision.requires_governance_hook else "false",
                        correlation_id=decision.correlation_id,
                        timestamp=self._naive_utc(decision.timestamp),
                    )
                )
                await session.commit()
            except Exception as exc:
                logger.warning("[RecoveryPolicy] persistence fallback to memory: %s", exc)

    async def _persist_audit_entry(self, entry: RecoveryAuditEntry, db: AsyncSession | None) -> None:
        async with self._session(db) as session:
            if session is None:
                return
            try:
                session.add(
                    RecoveryAuditModel(
                        audit_id=entry.audit_id,
                        event_type=entry.event_type,
                        actor=entry.actor,
                        action=entry.action,
                        request_id=entry.request_id,
                        correlation_id=entry.correlation_id,
                        details=entry.details,
                        timestamp=self._naive_utc(entry.timestamp),
                    )
                )
                await session.commit()
            except Exception as exc:
                logger.warning("[RecoveryPolicy] audit persistence fallback to memory: %s", exc)

    async def _fetch_all_requests(self, db: AsyncSession | None) -> List[RecoveryRequest]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                result = await session.execute(select(RecoveryRequestModel).order_by(desc(RecoveryRequestModel.created_at)))
                rows = result.scalars().all()
                return [
                    RecoveryRequest(
                        id=row.id,
                        source=row.source,
                        entity_id=row.entity_id,
                        failure_type=row.failure_type,
                        severity=RecoverySeverity(row.severity),
                        retry_count=row.retry_count,
                        recurrence=row.recurrence,
                        context=row.context or {},
                        correlation_id=row.correlation_id,
                        timestamp=row.timestamp,
                    )
                    for row in rows
                ]
            except Exception:
                return []

    async def _fetch_all_decisions(self, db: AsyncSession | None) -> List[RecoveryDecision]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                result = await session.execute(select(RecoveryDecisionModel).order_by(desc(RecoveryDecisionModel.timestamp)))
                rows = result.scalars().all()
                return [
                    RecoveryDecision(
                        decision_id=row.decision_id,
                        request_id=row.request_id,
                        action=RecoveryStrategy(row.action),
                        reason=row.reason,
                        cooldown_seconds=row.cooldown_seconds,
                        requires_governance_hook=(row.requires_governance_hook == "true"),
                        correlation_id=row.correlation_id,
                        timestamp=row.timestamp,
                    )
                    for row in rows
                ]
            except Exception:
                return []

    async def _fetch_all_audits(self, db: AsyncSession | None) -> List[RecoveryAuditEntry]:
        async with self._session(db) as session:
            if session is None:
                return []
            try:
                result = await session.execute(select(RecoveryAuditModel).order_by(desc(RecoveryAuditModel.timestamp)))
                rows = result.scalars().all()
                return [
                    RecoveryAuditEntry(
                        audit_id=row.audit_id,
                        event_type=row.event_type,
                        actor=row.actor,
                        action=row.action,
                        request_id=row.request_id,
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
    def _reason_for(action: RecoveryStrategy, request: RecoveryRequest) -> str:
        if action == RecoveryStrategy.RETRY:
            return f"Retry allowed for {request.failure_type} (retry_count={request.retry_count})"
        if action == RecoveryStrategy.CIRCUIT_BREAK:
            return "Timeout class error detected, applying circuit break"
        if action == RecoveryStrategy.BACKPRESSURE:
            return "Elevated severity with retry exhaustion, applying backpressure"
        if action == RecoveryStrategy.ROLLBACK:
            return "High-risk failure pattern, selecting rollback"
        if action == RecoveryStrategy.DETOX:
            return "Applying detox for non-critical residual failures"
        if action == RecoveryStrategy.ISOLATE:
            return "Critical signal requires workload isolation"
        return "Escalating to governance/operations due to risk threshold"


_service: Optional[RecoveryPolicyService] = None


def get_recovery_policy_service(event_stream: Optional["EventStream"] = None) -> RecoveryPolicyService:
    global _service
    if _service is None:
        _service = RecoveryPolicyService(event_stream=event_stream)
    elif event_stream is not None and _service.event_stream is None:
        _service.event_stream = event_stream
    return _service
