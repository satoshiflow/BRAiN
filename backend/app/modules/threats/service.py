from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from loguru import logger

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

# EventStream integration (Sprint 3)
try:
    from backend.mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None
    import warnings
    warnings.warn(
        "[ThreatService] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )

THREAT_KEY_PREFIX = "brain:threats:threat:"
THREAT_INDEX_KEY = "brain:threats:index"
THREAT_STATS_KEY = "brain:threats:stats"

# Module-level EventStream (set at startup via set_event_stream())
_event_stream: Optional["EventStream"] = None


def _threat_key(threat_id: str) -> str:
    return f"{THREAT_KEY_PREFIX}{threat_id}"


def set_event_stream(event_stream: Optional["EventStream"]) -> None:
    """
    Set EventStream for threats module (called at startup).

    Args:
        event_stream: EventStream instance or None to disable events
    """
    global _event_stream
    _event_stream = event_stream
    logger.info("[ThreatService] EventStream configured: %s", event_stream is not None)


async def _emit_event_safe(
    event_type: str,
    threat: Threat,
    old_status: Optional[ThreatStatus] = None,
    new_status: Optional[ThreatStatus] = None,
) -> None:
    """
    Emit threat event with error handling (non-blocking).

    Charter v1.0 Compliance:
    - Event publishing MUST NOT block business logic
    - Failures are logged but NOT raised
    - Graceful degradation when EventStream unavailable

    Args:
        event_type: Event type (e.g., "threat.detected")
        threat: Threat instance
        old_status: Previous status (for status_changed events)
        new_status: New status (for status_changed events)
    """
    global _event_stream

    if _event_stream is None or Event is None:
        logger.debug("[ThreatService] EventStream not available, skipping event: %s", event_type)
        return

    try:
        # Build base payload
        payload = {
            "threat_id": threat.id,
            "type": threat.type,
            "source": threat.source,
            "severity": threat.severity.value,
        }

        # Add description if present
        if threat.description:
            payload["description"] = threat.description

        # Event-specific payload fields
        if event_type == "threat.detected":
            payload["status"] = threat.status.value
            payload["metadata"] = threat.metadata
            payload["detected_at"] = threat.created_at

        elif event_type == "threat.status_changed":
            if old_status:
                payload["old_status"] = old_status.value
            if new_status:
                payload["new_status"] = new_status.value
            payload["changed_at"] = time.time()

        elif event_type == "threat.escalated":
            if old_status:
                payload["old_status"] = old_status.value
            payload["escalated_at"] = time.time()

        elif event_type == "threat.mitigated":
            if old_status:
                payload["old_status"] = old_status.value
            payload["mitigated_at"] = time.time()

            # Calculate duration if we have created_at
            if threat.created_at:
                payload["duration_seconds"] = time.time() - threat.created_at

        # Create Event instance
        event = Event(
            type=event_type,
            source="threat_service",
            target=None,
            payload=payload,
        )

        # Publish event (non-blocking)
        await _event_stream.publish(event)

        logger.debug(
            "[ThreatService] Event published: %s (threat_id=%s)",
            event_type,
            threat.id,
        )

    except Exception as e:
        logger.error(
            "[ThreatService] Event publishing failed: %s (event_type=%s, threat_id=%s)",
            e,
            event_type,
            threat.id,
            exc_info=True,
        )
        # DO NOT raise - business logic must continue


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

    # EVENT: threat.detected
    await _emit_event_safe(
        event_type="threat.detected",
        threat=threat,
    )

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

    # EVENT: threat.status_changed (always emit)
    await _emit_event_safe(
        event_type="threat.status_changed",
        threat=threat,
        old_status=old_status,
        new_status=status,
    )

    # EVENT: threat.escalated (conditional: if status -> ESCALATED)
    if status == ThreatStatus.ESCALATED:
        await _emit_event_safe(
            event_type="threat.escalated",
            threat=threat,
            old_status=old_status,
        )

    # EVENT: threat.mitigated (conditional: if status -> MITIGATED)
    if status == ThreatStatus.MITIGATED:
        await _emit_event_safe(
            event_type="threat.mitigated",
            threat=threat,
            old_status=old_status,
        )

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