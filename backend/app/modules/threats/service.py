from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from app.core.redis_client import get_redis
from .models import (
    Threat,
    ThreatCreate,
    ThreatListResponse,
    ThreatSeverity,
    ThreatStats,
    ThreatStatsResponse,
    ThreatStatus,
)

THREAT_KEY_PREFIX = "brain:threats:threat:"
THREAT_INDEX_KEY = "brain:threats:index"
THREAT_STATS_KEY = "brain:threats:stats"


def _threat_key(threat_id: str) -> str:
    return f"{THREAT_KEY_PREFIX}{threat_id}"


async def create_threat(payload: ThreatCreate) -> Threat:
    redis: Any = await get_redis()
    threat_id = str(uuid.uuid4())
    now = time.time()
    threat = Threat(
        id=threat_id,
        type=payload.type,
        source=payload.source,
        severity=payload.severity,
        status=ThreatStatus.OPEN,
        description=payload.description,
        metadata=payload.metadata,
        created_at=now,
        last_seen_at=now,
    )
    await redis.set(_threat_key(threat_id), threat.model_dump_json())
    await redis.sadd(THREAT_INDEX_KEY, threat_id)
    await _update_stats_on_create(redis, threat)
    return threat


async def get_threat(threat_id: str) -> Optional[Threat]:
    redis: Any = await get_redis()
    raw = await redis.get(_threat_key(threat_id))
    if not raw:
        return None
    data = json.loads(raw)
    return Threat.model_validate(data)


async def list_threats(
    status: Optional[ThreatStatus] = None,
    severity: Optional[ThreatSeverity] = None,
) -> ThreatListResponse:
    redis: Any = await get_redis()
    ids = await redis.smembers(THREAT_INDEX_KEY)
    threats: List[Threat] = []
    for threat_id in ids or []:
        threat = await get_threat(threat_id)
        if not threat:
            continue
        if status is not None and threat.status != status:
            continue
        if severity is not None and threat.severity != severity:
            continue
        threats.append(threat)
    threats.sort(key=lambda t: t.last_seen_at, reverse=True)
    return ThreatListResponse(threats=threats)


async def update_threat_status(
    threat_id: str,
    status: ThreatStatus,
) -> Optional[Threat]:
    redis: Any = await get_redis()
    threat = await get_threat(threat_id)
    if not threat:
        return None
    old_status = threat.status
    threat.status = status
    threat.last_seen_at = time.time()
    await redis.set(_threat_key(threat_id), threat.model_dump_json())
    await _update_stats_on_status_change(redis, threat, old_status)
    return threat


async def get_stats() -> ThreatStatsResponse:
    redis: Any = await get_redis()
    raw = await redis.get(THREAT_STATS_KEY)
    if not raw:
        by_severity: Dict[ThreatSeverity, int] = {
            s: 0 for s in ThreatSeverity
        }
        by_status: Dict[ThreatStatus, int] = {
            s: 0 for s in ThreatStatus
        }
        stats = ThreatStats(
            total=0,
            by_severity=by_severity,
            by_status=by_status,
            last_updated=time.time(),
        )
        return ThreatStatsResponse(stats=stats)
    data = json.loads(raw)
    by_severity: Dict[ThreatSeverity, int] = {}
    for k, v in data.get("by_severity", {}).items():
        by_severity[ThreatSeverity(k)] = int(v)
    by_status: Dict[ThreatStatus, int] = {}
    for k, v in data.get("by_status", {}).items():
        by_status[ThreatStatus(k)] = int(v)
    stats = ThreatStats(
        total=int(data.get("total", 0)),
        by_severity=by_severity,
        by_status=by_status,
        last_updated=float(data.get("last_updated", time.time())),
    )
    return ThreatStatsResponse(stats=stats)


async def _update_stats_on_create(redis: Any, threat: Threat) -> None:
    raw = await redis.get(THREAT_STATS_KEY)
    if raw:
        data = json.loads(raw)
    else:
        data = {
            "total": 0,
            "by_severity": {s.value: 0 for s in ThreatSeverity},
            "by_status": {s.value: 0 for s in ThreatStatus},
            "last_updated": time.time(),
        }
    data["total"] = int(data.get("total", 0)) + 1
    by_severity = data.get("by_severity", {})
    by_severity[threat.severity.value] = int(
        by_severity.get(threat.severity.value, 0)
    ) + 1
    data["by_severity"] = by_severity
    by_status = data.get("by_status", {})
    by_status[threat.status.value] = int(
        by_status.get(threat.status.value, 0)
    ) + 1
    data["by_status"] = by_status
    data["last_updated"] = time.time()
    await redis.set(THREAT_STATS_KEY, json.dumps(data))


async def _update_stats_on_status_change(
    redis: Any,
    threat: Threat,
    old_status: ThreatStatus,
) -> None:
    raw = await redis.get(THREAT_STATS_KEY)
    if not raw:
        return
    data = json.loads(raw)
    by_status = data.get("by_status", {})
    if old_status.value in by_status:
        by_status[old_status.value] = max(
            0,
            int(by_status.get(old_status.value, 0)) - 1,
        )
    by_status[threat.status.value] = int(
        by_status.get(threat.status.value, 0)
    ) + 1
    data["by_status"] = by_status
    data["last_updated"] = time.time()
    await redis.set(THREAT_STATS_KEY, json.dumps(data))