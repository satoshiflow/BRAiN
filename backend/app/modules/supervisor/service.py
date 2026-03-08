from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List
import time
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.agent_management.models import AgentModel, AgentStatus as ManagedAgentStatus
from app.modules.skill_engine.models import SkillRunModel

from .schemas import AgentStatus, SupervisorHealth, SupervisorStatus

logger = logging.getLogger(__name__)

# Optional EventStream import (Sprint 5: EventStream Integration)
try:
    from app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level EventStream (Sprint 5: EventStream Integration)
_event_stream: Any = None


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
