# backend/modules/missions/schemas.py

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from .models import MissionPriority, MissionStatus, MissionPayload


class MissionInfoResponse(BaseModel):
    name: str = "BRAIN Mission System"
    version: str = "0.1.0"
    description: str = "Lightweight Mission Queue + EventStream integration"


class MissionHealthDetails(BaseModel):
    queue_healthy: bool
    queue_length: int
    worker_running: bool
    worker_poll_interval: Optional[float]
    redis_url: Optional[str]


class MissionHealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    details: MissionHealthDetails


class MissionEnqueueRequest(MissionPayload):
    """
    Request-Payload für /api/missions/enqueue

    Erbt:
    - type
    - payload
    - priority
    """
    created_by: str = Field(
        default="api",
        description="Quelle der Mission (z.B. 'api', 'control-deck', 'scheduler')",
    )


class MissionEnqueueResponse(BaseModel):
    mission_id: str
    status: MissionStatus


class MissionQueueItem(BaseModel):
    id: str
    type: str
    status: MissionStatus
    priority: MissionPriority
    score: float
    created_at: str


class MissionQueueResponse(BaseModel):
    items: List[MissionQueueItem]
    length: int


class MissionEvent(BaseModel):
    id: str
    type: str
    source: str
    target: Optional[str]
    payload: Dict[str, Any]
    timestamp: str
    mission_id: Optional[str]
    task_id: Optional[str]
    correlation_id: Optional[str]


class MissionEventHistoryResponse(BaseModel):
    events: List[MissionEvent]


class MissionEventStatsResponse(BaseModel):
    stats: Dict[str, Any] # Flexible Struktur für verschiedene Statistiken