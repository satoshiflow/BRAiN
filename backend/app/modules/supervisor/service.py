from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
import time
import logging

from ..missions.models import MissionStatus
from ..missions.service import get_stats
from .schemas import AgentStatus, SupervisorHealth, SupervisorStatus

logger = logging.getLogger(__name__)

# Optional EventStream import (Sprint 5: EventStream Integration)
try:
    from app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level EventStream (Sprint 5: EventStream Integration)
_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
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


async def get_status() -> SupervisorStatus:
    """Get supervisor status with mission statistics.

    Returns:
        SupervisorStatus: Status object with mission counts

    Events:
        - supervisor.status_queried: Status queried with statistics
    """
    stats_response = await get_stats()
    stats = stats_response.stats

    def count(status: MissionStatus) -> int:
        return int(stats.by_status.get(status, 0))

    total = int(stats.total)
    running = count(MissionStatus.RUNNING)
    pending = count(MissionStatus.PENDING)
    completed = count(MissionStatus.COMPLETED)
    failed = count(MissionStatus.FAILED)
    cancelled = count(MissionStatus.CANCELLED)

    agents: List[AgentStatus] = []

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


async def list_agents() -> List[AgentStatus]:
    """List all supervised agents.

    Returns:
        List[AgentStatus]: List of agent statuses

    Events:
        - supervisor.agents_listed (optional): Agents queried
    """
    result = []  # Stub implementation

    # EVENT: supervisor.agents_listed (optional - Sprint 5)
    await _emit_event_safe("supervisor.agents_listed", {
        "agent_count": len(result),
        "queried_at": time.time(),
    })

    return result
