# backend/api/routes/missions.py
"""
BRAIN Mission System V2 - API Routes
------------------------------------

Integration des Redis-basierten Mission-Systems + EventStream aus mission_control_core.

Expose:
- GET  /api/missions/info
- GET  /api/missions/health
- POST /api/missions/enqueue
- GET  /api/missions/queue
- GET  /api/missions/events/history
- GET  /api/missions/events/stats
- GET  /api/missions/worker/status
- GET  /api/missions/agents/info
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from backend.modules.missions.mission_control_runtime import get_mission_runtime
from backend.modules.missions.schemas import (
    MissionInfoResponse,
    MissionHealthResponse,
    MissionHealthDetails,
    MissionEnqueueRequest,
    MissionEnqueueResponse,
    MissionQueueResponse,
    MissionQueueItem,
    MissionEventHistoryResponse,
    MissionEventStatsResponse,
    MissionEvent,
)
from backend.modules.missions.worker import get_worker_status

router = APIRouter(
    prefix="/api/missions",
    tags=["missions"],
)


@router.get("/info", response_model=MissionInfoResponse)
async def missions_info() -> MissionInfoResponse:
    """
    Basis-Info über das Mission-System.
    Wird später im Control Deck (Mission Deck) angezeigt.
    """
    return MissionInfoResponse()


@router.get("/health", response_model=MissionHealthResponse)
async def missions_health() -> MissionHealthResponse:
    """
    Health-Endpoint für das Mission-System.

    Aggregiert:
    - Queue-Status (Redis erreichbar? Queue-Länge?)
    - Worker-Status (läuft / läuft nicht, Poll-Intervall)
    """
    runtime = get_mission_runtime()

    try:
        queue_healthy = await runtime.get_queue_health()
        queue_stats = await runtime.get_queue_stats(preview_limit=0)
        queue_length = int(queue_stats.get("length", 0))
    except Exception:
        queue_healthy = False
        queue_length = 0

    worker = get_worker_status()

    overall_status = "ok" if queue_healthy else "degraded"

    details = MissionHealthDetails(
        queue_healthy=queue_healthy,
        queue_length=queue_length,
        worker_running=bool(worker.get("running")),
        worker_poll_interval=worker.get("poll_interval"),
        redis_url=worker.get("redis_url"),
    )

    return MissionHealthResponse(status=overall_status, details=details)


@router.post("/enqueue", response_model=MissionEnqueueResponse)
async def enqueue_mission(payload: MissionEnqueueRequest) -> MissionEnqueueResponse:
    """
    Enqueue eines Missionsjobs.

    Nutzt:
    - MissionQueue (Redis ZSET)
    - EventStream (TASK_CREATED-Event)
    """
    runtime = get_mission_runtime()

    try:
        result = await runtime.enqueue_mission(
            payload=payload,
            created_by=payload.created_by,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Enqueue failed: {exc}") from exc

    return MissionEnqueueResponse(
        mission_id=result.mission_id,
        status=result.status,
    )


@router.get("/queue", response_model=MissionQueueResponse)
async def get_queue_preview(
    limit: int = Query(20, ge=1, le=100),
) -> MissionQueueResponse:
    """
    Liefert eine Queue-Preview für das Mission Deck.
    """
    runtime = get_mission_runtime()
    preview = await runtime.get_queue_preview(limit=limit)
    stats = await runtime.get_queue_stats(preview_limit=0)

    items = [
        MissionQueueItem(
            id=entry.id,
            type=entry.type,
            status=entry.status,
            priority=entry.priority,
            score=entry.score,
            created_at=entry.created_at.isoformat(),
        )
        for entry in preview
    ]

    return MissionQueueResponse(
        items=items,
        length=int(stats.get("length", len(items))),
    )


@router.get("/events/history", response_model=MissionEventHistoryResponse)
async def get_mission_events_history(
    limit: int = Query(100, ge=1, le=1000),
    agent_id: Optional[str] = Query(None),
) -> MissionEventHistoryResponse:
    """
    Liefert Event-Historie aus dem EventStream.
    Ideal für einen "Event Feed" im Control Deck.
    """
    runtime = get_mission_runtime()
    events = await runtime.get_event_history(limit=limit, agent_id=agent_id)

    return MissionEventHistoryResponse(
        events=[
            MissionEvent(
                id=e.id,
                type=e.type.value,
                source=e.source,
                target=e.target,
                payload=e.payload,
                timestamp=e.timestamp.isoformat(),
                mission_id=e.mission_id,
                task_id=e.task_id,
                correlation_id=e.correlation_id,
            )
            for e in events
        ]
    )


@router.get("/events/stats", response_model=MissionEventStatsResponse)
async def get_mission_events_stats() -> MissionEventStatsResponse:
    """
    Aggregierte Event-Statistiken (z.B. Anzahl Events, Verteilung nach Typen).
    Eignet sich für Health-/Monitoring-Ansichten.
    """
    runtime = get_mission_runtime()
    stats = await runtime.get_event_stats()
    return MissionEventStatsResponse(stats=stats)


@router.get("/worker/status")
async def missions_worker_status() -> dict:
    """
    Liefert Basisinfos zum MissionWorker (läuft / läuft nicht etc.).
    Gut für Health-Ansichten im Control Deck.
    """
    return get_worker_status()


@router.get("/agents/info")
async def missions_agents_info() -> dict:
    """
    Placeholder für spätere Agenten-Mission-Mapping-Infos.
    Wird aktuell nur vom Debug-UI genutzt.
    """
    return {
        "name": "BRAIN Mission Agents View",
        "version": "1.0.0",
        "description": "Placeholder für Agent<->Mission Zuordnung.",
        "agents": [],
    }
# -----------------------------------------------------------------------------
# backend/modules/missions/mission_control_runtime.py