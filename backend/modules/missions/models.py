"""
BRAIN Mission System V1 - Data Models (Lightweight)
---------------------------------------------------

Vereinfachte, aber saubere Version des Mission-Systems:

- Mission: Hauptaufgabe im System
- MissionStatus: Lifecycle State
- MissionPriority: Wichtigkeit
- MissionQueueEntry: Ansicht für /api/missions/queue
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class MissionStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MissionPriority(int, Enum):
    LOW = 10
    NORMAL = 20
    HIGH = 30
    CRITICAL = 40


class MissionPayload(BaseModel):
    """
    Payload, den wir von außen annehmen.
    Wird in eine interne Mission gewandelt.
    """
    type: str = Field(..., description="Missions-Typ, z.B. 'agent.chat' oder 'analysis.report'")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Beliebige JSON-Daten")
    priority: MissionPriority = Field(default=MissionPriority.NORMAL)


class Mission(BaseModel):
    """
    Interne Missions-Repräsentation, wie sie in der Queue liegt.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    payload: Dict[str, Any]
    priority: MissionPriority = MissionPriority.NORMAL

    # Status / Lifecycle
    status: MissionStatus = MissionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Retry / Meta
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def mark_queued(self) -> None:
        self.status = MissionStatus.QUEUED
        self.touch()


class MissionQueueEntry(BaseModel):
    """
    Vereinfachte Ansicht für die Queue-Preview.
    """
    id: str
    type: str
    status: MissionStatus
    priority: MissionPriority
    created_at: datetime
    score: float

    @classmethod
    def from_mission(cls, mission: Mission, score: float) -> "MissionQueueEntry":
        return cls(
            id=mission.id,
            type=mission.type,
            status=mission.status,
            priority=mission.priority,
            created_at=mission.created_at,
            score=score,
        )


class MissionEnqueueResult(BaseModel):
    mission_id: str
    status: MissionStatus