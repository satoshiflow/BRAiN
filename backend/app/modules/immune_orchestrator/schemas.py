"""Schemas for the Immune Orchestrator module."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SignalSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class DecisionAction(str, Enum):
    OBSERVE = "observe"
    WARN = "warn"
    MITIGATE = "mitigate"
    ISOLATE = "isolate"
    ESCALATE = "escalate"


class IncidentSignal(BaseModel):
    id: str
    type: str
    source: str
    severity: SignalSeverity
    entity: str
    timestamp: datetime = Field(default_factory=_utc_now)
    context: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    blast_radius: int = Field(default=1, ge=1, le=1000)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    recurrence: int = Field(default=0, ge=0)


class ImmuneDecision(BaseModel):
    decision_id: str
    signal_id: str
    action: DecisionAction
    priority_score: float = Field(ge=0.0, le=1.0)
    reason: str
    requires_governance_hook: bool = False
    created_at: datetime = Field(default_factory=_utc_now)
    correlation_id: Optional[str] = None


class ImmuneAuditEntry(BaseModel):
    audit_id: str
    event_type: str
    actor: str
    action: str
    severity: SignalSeverity
    resource_type: str
    resource_id: str
    correlation_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


class ImmuneMetrics(BaseModel):
    total_signals: int = 0
    total_decisions: int = 0
    actions: Dict[str, int] = Field(default_factory=dict)
    by_source: Dict[str, int] = Field(default_factory=dict)


class EvaluateSignalResponse(BaseModel):
    signal: IncidentSignal
    decision: ImmuneDecision


class DecisionsResponse(BaseModel):
    items: List[ImmuneDecision] = Field(default_factory=list)


class SignalsResponse(BaseModel):
    items: List[IncidentSignal] = Field(default_factory=list)


class ImmuneAuditResponse(BaseModel):
    items: List[ImmuneAuditEntry] = Field(default_factory=list)
