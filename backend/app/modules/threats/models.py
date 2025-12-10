from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ThreatSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ThreatStatus(str, Enum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    MITIGATED = "MITIGATED"
    IGNORED = "IGNORED"
    ESCALATED = "ESCALATED"


class Threat(BaseModel):
    id: str
    type: str
    source: str
    severity: ThreatSeverity
    status: ThreatStatus = ThreatStatus.OPEN
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: float = Field(default_factory=lambda: time.time())
    last_seen_at: float = Field(default_factory=lambda: time.time())


class ThreatCreate(BaseModel):
    type: str
    source: str
    severity: ThreatSeverity
    description: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ThreatListResponse(BaseModel):
    threats: List[Threat]


class ThreatStats(BaseModel):
    total: int
    by_severity: Dict[ThreatSeverity, int]
    by_status: Dict[ThreatStatus, int]
    last_updated: float


class ThreatStatsResponse(BaseModel):
    stats: ThreatStats