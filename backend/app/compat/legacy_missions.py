"""Compatibility bridge for legacy mission runtime modules.

All imports from `backend/modules/missions` and `backend/modules/mission_system`
should be routed through this adapter to keep legacy coupling centralized.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.core.config import get_settings

# Re-export legacy mission API schemas used by legacy route handlers.
from modules.missions.schemas import (  # noqa: F401
    MissionEnqueueRequest,
    MissionEnqueueResponse,
    MissionEvent,
    MissionEventHistoryResponse,
    MissionEventStatsResponse,
    MissionHealthDetails,
    MissionHealthResponse,
    MissionInfoResponse,
    MissionQueueItem,
    MissionQueueResponse,
)


def get_mission_runtime():
    from modules.missions.mission_control_runtime import get_mission_runtime as _impl

    return _impl()


def get_worker_status() -> dict:
    from modules.missions.worker import get_worker_status as _impl

    return _impl()


async def start_mission_worker(event_stream=None):
    from modules.missions.worker import start_mission_worker as _impl

    return await _impl(event_stream=event_stream)


async def stop_mission_worker() -> None:
    from modules.missions.worker import stop_mission_worker as _impl

    await _impl()


async def get_mission_health_metrics() -> dict[str, Any]:
    from modules.missions.queue import MissionQueue

    settings = get_settings()
    queue = MissionQueue(redis_url=settings.REDIS_URL)
    return await queue.get_health_metrics()


async def register_credit_hooks(
    *,
    on_start: Callable[..., Awaitable[dict]],
    on_complete: Callable[..., Awaitable[dict]],
    on_failed: Callable[..., Awaitable[dict]],
    on_cancelled: Callable[..., Awaitable[dict]],
) -> None:
    from modules.mission_system import register_hooks

    await register_hooks(
        on_start=on_start,
        on_complete=on_complete,
        on_failed=on_failed,
        on_cancelled=on_cancelled,
    )
