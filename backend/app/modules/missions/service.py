from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.redis_client import get_redis
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

MISSION_KEY_PREFIX = "brain:missions:mission:"
MISSION_INDEX_KEY = "brain:missions:index"
MISSION_LOG_PREFIX = "brain:missions:log:"
MISSION_STATS_KEY = "brain:missions:stats"


def _mission_key(mission_id: str) -> str:
    return f"{MISSION_KEY_PREFIX}{mission_id}"


def _mission_log_key(mission_id: str) -> str:
    return f"{MISSION_LOG_PREFIX}{mission_id}"


async def create_mission(payload: MissionCreate) -> Mission:
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
    redis: Any = await get_redis()
    await redis.rpush(_mission_log_key(mission_id), entry.model_dump_json())


async def get_log(mission_id: str) -> MissionLogResponse:
    redis: Any = await get_redis()
    raw_entries = await redis.lrange(_mission_log_key(mission_id), 0, -1)
    entries: List[MissionLogEntry] = []
    for raw in raw_entries or []:
        data = json.loads(raw)
        entries.append(MissionLogEntry.model_validate(data))
    return MissionLogResponse(mission_id=mission_id, log=entries)


async def update_status(mission_id: str, status: MissionStatus) -> Optional[Mission]:
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