from __future__ import annotations

import enum
import time
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MissionStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class MissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class MissionCreate(MissionBase):
    id: Optional[str] = None


class Mission(MissionBase):
    id: str
    status: MissionStatus = MissionStatus.PENDING
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class MissionLogEntry(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    level: str = "info"
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


class MissionListResponse(BaseModel):
    missions: List[Mission]


class MissionLogResponse(BaseModel):
    mission_id: str
    log: List[MissionLogEntry]


class MissionStats(BaseModel):
    total: int
    by_status: Dict[MissionStatus, int]
    last_updated: float = Field(default_factory=time.time)


class MissionStatsResponse(BaseModel):
    stats: MissionStats
# backend/app/modules/missions/__init__.py