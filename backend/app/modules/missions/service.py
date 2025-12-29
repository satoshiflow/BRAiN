from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from ...core.redis_client import get_redis
from .models import (
    Mission,
    MissionCreate,
    MissionListResponse,
    MissionLogEntry,
    MissionLogResponse,
    MissionStats,
    MissionStatsResponse,
    MissionStatus,
)

logger = logging.getLogger(__name__)

# Optional EventStream import (Sprint 5: EventStream Integration)
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

MISSION_KEY_PREFIX = "brain:missions:mission:"
MISSION_INDEX_KEY = "brain:missions:index"
MISSION_LOG_PREFIX = "brain:missions:log:"
MISSION_STATS_KEY = "brain:missions:stats"

# Module-level EventStream (Sprint 5: EventStream Integration)
_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for Missions module (Sprint 5).

    Args:
        stream: EventStream instance for publishing events

    Note:
        This is called during application startup to inject the EventStream
        dependency into the Missions module for event publishing.
    """
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit Missions event with error handling (non-blocking).

    Args:
        event_type: Event type (e.g., "mission.created", "mission.status_changed")
        payload: Event payload dictionary

    Note:
        - Never raises exceptions (fully non-blocking)
        - Logs failures at ERROR level with full traceback
        - Gracefully handles missing EventStream (optional dependency)
        - All Missions events are broadcast (target=None)
    """
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[MissionsService] EventStream not available, skipping event")
        return

    try:
        event = Event(
            type=event_type,
            source="missions_service",
            target=None,  # Broadcast to all subscribers
            payload=payload
        )
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"[MissionsService] Event publishing failed: {e}", exc_info=True)


def _mission_key(mission_id: str) -> str:
    return f"{MISSION_KEY_PREFIX}{mission_id}"


def _mission_log_key(mission_id: str) -> str:
    return f"{MISSION_LOG_PREFIX}{mission_id}"


async def create_mission(payload: MissionCreate) -> Mission:
    """Create new mission in Redis.

    Args:
        payload: Mission creation payload

    Returns:
        Created Mission object

    Events:
        - mission.created (HIGH PRIORITY): Emitted after mission is created
    """
    redis: Any = await get_redis()
    mission_id = payload.id or str(uuid.uuid4())
    now = time.time()
    mission = Mission(
        id=mission_id,
        name=payload.name,
        description=payload.description,
        data=payload.data,
        status=MissionStatus.PENDING,
        created_at=now,
        updated_at=now,
    )
    await redis.set(_mission_key(mission_id), mission.model_dump_json())
    await redis.sadd(MISSION_INDEX_KEY, mission_id)
    await _update_stats_on_create(redis, mission.status)
    entry = MissionLogEntry(
        level="info",
        message="Mission created",
        data={"name": mission.name, "description": mission.description},
    )
    await append_log_entry(mission_id, entry)

    # EVENT: mission.created (HIGH PRIORITY - Sprint 5)
    await _emit_event_safe("mission.created", {
        "mission_id": mission.id,
        "name": mission.name,
        "description": mission.description or "",
        "status": mission.status.value,
        "created_at": mission.created_at,
    })

    return mission


async def get_mission(mission_id: str) -> Optional[Mission]:
    redis: Any = await get_redis()
    raw = await redis.get(_mission_key(mission_id))
    if not raw:
        return None
    data = json.loads(raw)
    return Mission.model_validate(data)


async def list_missions(status: Optional[MissionStatus] = None) -> MissionListResponse:
    redis: Any = await get_redis()
    ids = await redis.smembers(MISSION_INDEX_KEY)
    missions: List[Mission] = []
    for mission_id in ids or []:
        mission = await get_mission(mission_id)
        if not mission:
            continue
        if status is not None and mission.status != status:
            continue
        missions.append(mission)
    missions.sort(key=lambda m: m.created_at, reverse=True)
    return MissionListResponse(missions=missions)


async def append_log_entry(mission_id: str, entry: MissionLogEntry) -> None:
    """Append log entry to mission's log (Redis LIST).

    Args:
        mission_id: Mission ID
        entry: Log entry to append

    Events:
        - mission.log_appended (MEDIUM PRIORITY): Emitted after log entry is appended
    """
    redis: Any = await get_redis()
    await redis.rpush(_mission_log_key(mission_id), entry.model_dump_json())

    # EVENT: mission.log_appended (MEDIUM PRIORITY - Sprint 5)
    await _emit_event_safe("mission.log_appended", {
        "mission_id": mission_id,
        "log_level": entry.level,
        "message": entry.message,
        "appended_at": entry.timestamp,
    })


async def get_log(mission_id: str) -> MissionLogResponse:
    redis: Any = await get_redis()
    raw_entries = await redis.lrange(_mission_log_key(mission_id), 0, -1)
    entries: List[MissionLogEntry] = []
    for raw in raw_entries or []:
        data = json.loads(raw)
        entries.append(MissionLogEntry.model_validate(data))
    return MissionLogResponse(mission_id=mission_id, log=entries)


async def update_status(mission_id: str, status: MissionStatus) -> Optional[Mission]:
    """Update mission status.

    Args:
        mission_id: Mission ID
        status: New status

    Returns:
        Updated Mission object, or None if not found

    Events:
        - mission.status_changed (HIGH PRIORITY): Emitted after status change
    """
    redis: Any = await get_redis()
    mission = await get_mission(mission_id)
    if not mission:
        return None
    old_status = mission.status
    mission.status = status
    mission.updated_at = time.time()
    await redis.set(_mission_key(mission_id), mission.model_dump_json())
    await _update_stats_on_status_change(redis, old_status, status)
    entry = MissionLogEntry(
        level="info",
        message="Mission status changed",
        data={"from": old_status, "to": status},
    )
    await append_log_entry(mission_id, entry)

    # EVENT: mission.status_changed (HIGH PRIORITY - Sprint 5)
    await _emit_event_safe("mission.status_changed", {
        "mission_id": mission.id,
        "old_status": old_status.value,
        "new_status": mission.status.value,
        "changed_at": mission.updated_at,
    })

    return mission


async def get_stats() -> MissionStatsResponse:
    redis: Any = await get_redis()
    raw = await redis.get(MISSION_STATS_KEY)
    if not raw:
        stats = MissionStats(total=0, by_status={s: 0 for s in MissionStatus})
        return MissionStatsResponse(stats=stats)
    data = json.loads(raw)
    by_status: Dict[MissionStatus, int] = {}
    for key, value in data.get("by_status", {}).items():
        by_status[MissionStatus(key)] = int(value)
    stats = MissionStats(
        total=int(data.get("total", 0)),
        by_status=by_status,
        last_updated=float(data.get("last_updated", time.time())),
    )
    return MissionStatsResponse(stats=stats)


async def _update_stats_on_create(redis: Any, status: MissionStatus) -> None:
    raw = await redis.get(MISSION_STATS_KEY)
    if raw:
        data = json.loads(raw)
    else:
        data = {
            "total": 0,
            "by_status": {s.value: 0 for s in MissionStatus},
            "last_updated": time.time(),
        }
    data["total"] = int(data.get("total", 0)) + 1
    by_status = data.get("by_status", {})
    by_status[status.value] = int(by_status.get(status.value, 0)) + 1
    data["by_status"] = by_status
    data["last_updated"] = time.time()
    await redis.set(MISSION_STATS_KEY, json.dumps(data))


async def _update_stats_on_status_change(redis: Any, old_status: MissionStatus, new_status: MissionStatus) -> None:
    raw = await redis.get(MISSION_STATS_KEY)
    if not raw:
        return
    data = json.loads(raw)
    by_status = data.get("by_status", {})
    if old_status.value in by_status:
        by_status[old_status.value] = max(0, int(by_status.get(old_status.value, 0)) - 1)
    by_status[new_status.value] = int(by_status.get(new_status.value, 0)) + 1
    data["by_status"] = by_status
    data["last_updated"] = time.time()
    await redis.set(MISSION_STATS_KEY, json.dumps(data))