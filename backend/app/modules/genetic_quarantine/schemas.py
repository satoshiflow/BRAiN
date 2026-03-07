"""Schemas for Genetic Quarantine Manager."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuarantineState(str, Enum):
    CANDIDATE = "candidate"
    QUARANTINED = "quarantined"
    PROBATION = "probation"
    APPROVED = "approved"
    REJECTED = "rejected"


class QuarantineSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class QuarantineRequest(BaseModel):
    agent_id: str = Field(..., min_length=1, max_length=128)
    snapshot_version: int = Field(..., ge=0)
    reason: str = Field(..., min_length=3, max_length=2000)
    requested_state: QuarantineState = QuarantineState.QUARANTINED
    severity: QuarantineSeverity = QuarantineSeverity.MEDIUM
    source: str = Field(default="genetic_quarantine", min_length=1, max_length=128)
    actor: str = Field(default="system", min_length=1, max_length=128)
    correlation_id: Optional[str] = Field(default=None, max_length=128)
    context: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QuarantineRecord(BaseModel):
    quarantine_id: str
    agent_id: str
    snapshot_version: int
    state: QuarantineState
    previous_state: Optional[QuarantineState] = None
    reason: str
    severity: QuarantineSeverity
    source: str
    actor: str
    correlation_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class QuarantineTransitionRequest(BaseModel):
    quarantine_id: str = Field(..., min_length=1, max_length=128)
    target_state: QuarantineState
    reason: str = Field(..., min_length=3, max_length=2000)
    actor: str = Field(default="system", min_length=1, max_length=128)
    correlation_id: Optional[str] = Field(default=None, max_length=128)
    context: Dict[str, Any] = Field(default_factory=dict)


class QuarantineAuditEntry(BaseModel):
    audit_id: str
    quarantine_id: str
    event_type: str
    action: str
    actor: str
    details: Dict[str, Any]
    correlation_id: Optional[str] = None
    timestamp: datetime


class QuarantineResponse(BaseModel):
    record: QuarantineRecord


class QuarantineRecordsResponse(BaseModel):
    items: List[QuarantineRecord]


class QuarantineAuditResponse(BaseModel):
    items: List[QuarantineAuditEntry]
