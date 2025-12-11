from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.modules.missions.models import MissionStatus
from app.modules.missions.service import get_stats
from .schemas import AgentStatus, SupervisorHealth, SupervisorStatus


async def get_health() -> SupervisorHealth:
    return SupervisorHealth(status="ok", timestamp=datetime.now(timezone.utc))


async def get_status() -> SupervisorStatus:
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

    return SupervisorStatus(
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


async def list_agents() -> List[AgentStatus]:
    return []
