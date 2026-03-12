from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, List
import time
import uuid
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    AgentStatus,
    DomainEscalationDecisionRequest,
    DomainEscalationRequest,
    DomainEscalationResponse,
    SupervisorHealth,
    SupervisorStatus,
)

from loguru import logger

# Optional EventStream import (Sprint 5: EventStream Integration)
try:
    from app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level EventStream (Sprint 5: EventStream Integration)
_event_stream: Any = None
_domain_escalations: list[DomainEscalationResponse] = []

_ALLOWED_ESCALATION_TRANSITIONS: dict[str, set[str]] = {
    # queued -> in_review is a manual reviewer action via POST /escalations/domain/{id}/decision.
    # There is no background worker that auto-advances to in_review.
    # Reviewers must explicitly set status="in_review" before approving or denying.
    "queued": {"in_review", "cancelled"},
    "in_review": {"approved", "denied", "cancelled"},
    "approved": set(),   # terminal
    "denied": set(),     # terminal
    "cancelled": set(),  # terminal
}


def _to_external_escalation_id(value: str) -> str:
    return f"esc-{value}"


def _from_external_escalation_id(value: str) -> str:
    return value[4:] if value.startswith("esc-") else value


def set_event_stream(stream: Any) -> None:
    """Initialize EventStream for Supervisor module (Sprint 5)."""
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit Supervisor event with error handling (non-blocking).

    Args:
        event_type: Event type (e.g., "supervisor.status_queried")
        payload: Event payload dictionary

    Note:
        - Never raises exceptions
        - Logs failures at ERROR level
        - Gracefully handles missing EventStream
    """
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[SupervisorService] EventStream not available, skipping event")
        return

    try:
        event = Event(
            type=event_type,
            source="supervisor_service",
            target=None,
            payload=payload
        )
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"[SupervisorService] Event publishing failed: {e}", exc_info=True)


async def get_health() -> SupervisorHealth:
    """Get supervisor health status.

    Returns:
        SupervisorHealth: Health status object

    Events:
        - supervisor.health_checked (optional): Health check performed
    """
    result = SupervisorHealth(status="ok", timestamp=datetime.now(timezone.utc))

    # EVENT: supervisor.health_checked (optional - Sprint 5)
    await _emit_event_safe("supervisor.health_checked", {
        "status": result.status,
        "checked_at": result.timestamp.timestamp(),
    })

    return result


async def get_status(db: AsyncSession | None = None) -> SupervisorStatus:
    """Get supervisor status with mission statistics.

    Returns:
        SupervisorStatus: Status object with mission counts

    Events:
        - supervisor.status_queried: Status queried with statistics

    Note:
        When DB is available, canonical execution counts are derived from `SkillRun`.
        Compatibility response fields keep the historic `*_missions` naming for now.
    """
    total = 0
    running = 0
    pending = 0
    completed = 0
    failed = 0
    cancelled = 0
    agents: List[AgentStatus] = []

    if db is not None:
        from app.modules.skill_engine.models import SkillRunModel

        total = (await db.execute(select(func.count(SkillRunModel.id)))).scalar() or 0
        running = (
            await db.execute(select(func.count(SkillRunModel.id)).where(SkillRunModel.state == "running"))
        ).scalar() or 0
        pending = (
            await db.execute(
                select(func.count(SkillRunModel.id)).where(
                    SkillRunModel.state.in_(["queued", "planning", "waiting_approval"])
                )
            )
        ).scalar() or 0
        completed = (
            await db.execute(select(func.count(SkillRunModel.id)).where(SkillRunModel.state == "succeeded"))
        ).scalar() or 0
        failed = (
            await db.execute(select(func.count(SkillRunModel.id)).where(SkillRunModel.state == "failed"))
        ).scalar() or 0
        cancelled = (
            await db.execute(
                select(func.count(SkillRunModel.id)).where(SkillRunModel.state.in_(["cancelled", "timed_out"]))
            )
        ).scalar() or 0
        agents = await list_agents(db)
    else:
        # Backward compatibility path used by legacy tests/callers that monkeypatch
        # `get_stats()` and expect status aggregation from missions-like counters.
        try:
            stats_response = await get_stats()
            stats = getattr(stats_response, "stats", None)
            if stats is not None:
                by_status = getattr(stats, "by_status", {}) or {}
                total = int(getattr(stats, "total", 0) or 0)
                running = int(by_status.get("RUNNING", 0) or 0)
                pending = int(by_status.get("PENDING", 0) or 0)
                completed = int(by_status.get("COMPLETED", 0) or 0)
                failed = int(by_status.get("FAILED", 0) or 0)
                cancelled = int(by_status.get("CANCELLED", 0) or 0)
        except Exception:
            # Keep non-blocking behavior and fall back to zeroed counters.
            pass

    result = SupervisorStatus(
        status="ok",
        timestamp=datetime.now(timezone.utc),
        total_missions=total,
        running_missions=running,
        pending_missions=pending,
        completed_missions=completed,
        failed_missions=failed,
        cancelled_missions=cancelled,
        agents=agents,
    )

    # EVENT: supervisor.status_queried (recommended - Sprint 5)
    await _emit_event_safe("supervisor.status_queried", {
        "total_missions": result.total_missions,
        "running_missions": result.running_missions,
        "pending_missions": result.pending_missions,
        "completed_missions": result.completed_missions,
        "failed_missions": result.failed_missions,
        "cancelled_missions": result.cancelled_missions,
        "agent_count": len(result.agents),
        "queried_at": time.time(),
    })

    return result


async def list_agents(db: AsyncSession | None = None) -> List[AgentStatus]:
    """List all supervised agents.

    Returns:
        List[AgentStatus]: List of agent statuses

    Events:
        - supervisor.agents_listed (optional): Agents queried
    """
    result: List[AgentStatus] = []

    if db is not None:
        from app.modules.agent_management.models import AgentModel, AgentStatus as ManagedAgentStatus
        from app.modules.skill_engine.models import SkillRunModel

        running_query = (
            select(SkillRunModel.requested_by, func.count(SkillRunModel.id))
            .where(SkillRunModel.state == "running")
            .group_by(SkillRunModel.requested_by)
        )
        running_result = await db.execute(running_query)
        running_by_agent = {row[0]: row[1] for row in running_result.all()}

        agents_result = await db.execute(select(AgentModel).order_by(AgentModel.registered_at.desc()))
        for agent in agents_result.scalars().all():
            state = agent.status.value if isinstance(agent.status, ManagedAgentStatus) else str(agent.status)
            result.append(
                AgentStatus(
                    id=agent.agent_id,
                    name=agent.name,
                    role=agent.agent_type,
                    state=state,
                    last_heartbeat=agent.last_heartbeat,
                    missions_running=running_by_agent.get(agent.agent_id, 0),
                )
            )

    # EVENT: supervisor.agents_listed (optional - Sprint 5)
    await _emit_event_safe("supervisor.agents_listed", {
        "agent_count": len(result),
        "queried_at": time.time(),
    })

    return result


async def get_stats() -> Any:
    """Compatibility helper for legacy supervisor status consumers.

    Returns an object with `.stats.total` and `.stats.by_status` fields.
    Tests may monkeypatch this function directly.
    """
    try:
        from app.modules.missions.service import get_stats as missions_get_stats

        return await missions_get_stats()
    except Exception:
        # Stable fallback contract
        return SimpleNamespace(
            stats=SimpleNamespace(
                total=0,
                by_status={
                    "PENDING": 0,
                    "RUNNING": 0,
                    "COMPLETED": 0,
                    "FAILED": 0,
                    "CANCELLED": 0,
                },
                last_updated=time.time(),
            )
        )


async def create_domain_escalation_handoff(
    payload: DomainEscalationRequest,
    db: AsyncSession | None = None,
) -> DomainEscalationResponse:
    """Create a supervisor handoff record for a domain escalation."""
    if db is not None:
        from app.modules.supervisor.models import DomainEscalationModel

        model = DomainEscalationModel(
            tenant_id=payload.tenant_id,
            domain_key=payload.domain_key,
            requested_by=payload.requested_by,
            requested_by_type=payload.requested_by_type,
            status="queued",
            reason=payload.reason,
            reasons=payload.reasons,
            recommended_next_actions=payload.recommended_next_actions,
            risk_tier=payload.risk_tier,
            correlation_id=payload.correlation_id,
            context=payload.context,
        )
        db.add(model)
        await db.commit()
        await db.refresh(model)

        item = DomainEscalationResponse(
            escalation_id=_to_external_escalation_id(str(model.id)),
            status=model.status,
            received_at=model.created_at,
            domain_key=model.domain_key,
            requested_by=model.requested_by,
            risk_tier=model.risk_tier,
            correlation_id=model.correlation_id,
        )
    else:
        item = DomainEscalationResponse(
            escalation_id=_to_external_escalation_id(str(uuid4())),
            status="queued",
            received_at=datetime.now(timezone.utc),
            domain_key=payload.domain_key,
            requested_by=payload.requested_by,
            risk_tier=payload.risk_tier,
            correlation_id=payload.correlation_id,
        )
        _domain_escalations.insert(0, item)

    await _emit_event_safe(
        "supervisor.domain_escalation.received",
        {
            "escalation_id": item.escalation_id,
            "domain_key": payload.domain_key,
            "requested_by": payload.requested_by,
            "risk_tier": payload.risk_tier,
            "correlation_id": payload.correlation_id,
            "received_at": item.received_at.timestamp(),
        },
    )

    return item


async def list_domain_escalation_handoffs(
    limit: int = 50,
    db: AsyncSession | None = None,
    tenant_id: str | None = None,
) -> list[DomainEscalationResponse]:
    """List recent supervisor escalation handoff records."""
    limit = max(1, min(limit, 200))
    if db is not None:
        from app.modules.supervisor.models import DomainEscalationModel

        query = select(DomainEscalationModel).order_by(DomainEscalationModel.created_at.desc())
        if tenant_id is not None:
            query = query.where(DomainEscalationModel.tenant_id == tenant_id)
        result = await db.execute(query.limit(limit))
        items = list(result.scalars().all())
        return [
            DomainEscalationResponse(
                escalation_id=_to_external_escalation_id(str(item.id)),
                status=item.status,
                received_at=item.created_at,
                domain_key=item.domain_key,
                requested_by=item.requested_by,
                risk_tier=item.risk_tier,
                correlation_id=item.correlation_id,
            )
            for item in items
        ]
    return _domain_escalations[:limit]


async def get_domain_escalation_handoff(
    escalation_id: str,
    db: AsyncSession | None = None,
    tenant_id: str | None = None,
) -> DomainEscalationResponse | None:
    normalized_id = _from_external_escalation_id(escalation_id)
    if db is not None:
        from app.modules.supervisor.models import DomainEscalationModel

        try:
            escalation_uuid = uuid.UUID(normalized_id)
        except ValueError:
            return None

        query = select(DomainEscalationModel).where(DomainEscalationModel.id == escalation_uuid)
        if tenant_id is not None:
            query = query.where(DomainEscalationModel.tenant_id == tenant_id)
        item = (await db.execute(query.limit(1))).scalar_one_or_none()
        if item is None:
            return None
        return DomainEscalationResponse(
            escalation_id=_to_external_escalation_id(str(item.id)),
            status=item.status,
            received_at=item.created_at,
            domain_key=item.domain_key,
            requested_by=item.requested_by,
            risk_tier=item.risk_tier,
            correlation_id=item.correlation_id,
        )

    for item in _domain_escalations:
        if item.escalation_id == escalation_id:
            return item
    return None


async def decide_domain_escalation_handoff(
    escalation_id: str,
    decision: DomainEscalationDecisionRequest,
    db: AsyncSession | None = None,
    tenant_id: str | None = None,
) -> DomainEscalationResponse | None:
    normalized_id = _from_external_escalation_id(escalation_id)
    if db is not None:
        from app.modules.supervisor.models import DomainEscalationModel

        try:
            escalation_uuid = uuid.UUID(normalized_id)
        except ValueError:
            return None

        query = select(DomainEscalationModel).where(DomainEscalationModel.id == escalation_uuid)
        if tenant_id is not None:
            query = query.where(DomainEscalationModel.tenant_id == tenant_id)
        model = (await db.execute(query.limit(1))).scalar_one_or_none()
        if model is None:
            return None

        current_status = str(model.status)
        next_status = decision.status.value
        if next_status != current_status and next_status not in _ALLOWED_ESCALATION_TRANSITIONS.get(current_status, set()):
            raise ValueError(f"Invalid escalation transition: {current_status} -> {next_status}")

        model.status = next_status
        model.reviewed_by = decision.reviewer_id
        model.reviewed_at = datetime.now(timezone.utc)
        model.decision_reason = decision.decision_reason
        model.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(model)

        await _emit_event_safe(
            "supervisor.domain_escalation.decided",
            {
                "escalation_id": _to_external_escalation_id(str(model.id)),
                "status": model.status,
                "reviewed_by": decision.reviewer_id,
                "risk_tier": model.risk_tier,
            },
        )

        return DomainEscalationResponse(
            escalation_id=_to_external_escalation_id(str(model.id)),
            status=model.status,
            received_at=model.created_at,
            domain_key=model.domain_key,
            requested_by=model.requested_by,
            risk_tier=model.risk_tier,
            correlation_id=model.correlation_id,
        )

    for idx, item in enumerate(_domain_escalations):
        if item.escalation_id == escalation_id:
            current_status = item.status
            next_status = decision.status.value
            if next_status != current_status and next_status not in _ALLOWED_ESCALATION_TRANSITIONS.get(current_status, set()):
                raise ValueError(f"Invalid escalation transition: {current_status} -> {next_status}")

            updated = DomainEscalationResponse(
                escalation_id=item.escalation_id,
                status=next_status,
                received_at=item.received_at,
                domain_key=item.domain_key,
                requested_by=item.requested_by,
                risk_tier=item.risk_tier,
                correlation_id=item.correlation_id,
            )
            _domain_escalations[idx] = updated

            await _emit_event_safe(
                "supervisor.domain_escalation.decided",
                {
                    "escalation_id": updated.escalation_id,
                    "status": updated.status,
                    "reviewed_by": decision.reviewer_id,
                    "risk_tier": updated.risk_tier,
                },
            )
            return updated
    return None
