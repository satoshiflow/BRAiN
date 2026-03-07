"""Schemas for the Unified Recovery Policy Engine."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    CIRCUIT_BREAK = "circuit_break"
    ROLLBACK = "rollback"
    BACKPRESSURE = "backpressure"
    DETOX = "detox"
    ISOLATE = "isolate"
    ESCALATE = "escalate"


class RecoverySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryRequest(BaseModel):
    id: str
    source: str
    entity_id: str
    failure_type: str
    severity: RecoverySeverity
    retry_count: int = Field(default=0, ge=0)
    recurrence: int = Field(default=0, ge=0)
    context: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=_utc_now)


class RecoveryPolicyConfig(BaseModel):
    max_retries: int = Field(default=3, ge=0)
    cooldown_seconds: int = Field(default=60, ge=0)
    escalation_threshold: int = Field(default=3, ge=1)
    allowed_actions: List[RecoveryStrategy] = Field(
        default_factory=lambda: [
            RecoveryStrategy.RETRY,
            RecoveryStrategy.CIRCUIT_BREAK,
            RecoveryStrategy.ROLLBACK,
            RecoveryStrategy.BACKPRESSURE,
            RecoveryStrategy.DETOX,
            RecoveryStrategy.ISOLATE,
            RecoveryStrategy.ESCALATE,
        ]
    )


class RecoveryDecision(BaseModel):
    decision_id: str
    request_id: str
    action: RecoveryStrategy
    reason: str
    cooldown_seconds: int
    requires_governance_hook: bool = False
    correlation_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=_utc_now)


class RecoveryAuditEntry(BaseModel):
    audit_id: str
    event_type: str
    actor: str
    action: str
    request_id: str
    correlation_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utc_now)


class RecoveryMetrics(BaseModel):
    total_requests: int = 0
    total_decisions: int = 0
    by_action: Dict[str, int] = Field(default_factory=dict)
    by_source: Dict[str, int] = Field(default_factory=dict)


class RecoveryAdapterRequest(BaseModel):
    payload: Dict[str, Any] = Field(default_factory=dict)


class RecoveryDecisionResponse(BaseModel):
    request: RecoveryRequest
    decision: RecoveryDecision


class RecoveryDecisionListResponse(BaseModel):
    items: List[RecoveryDecision] = Field(default_factory=list)


class RecoveryAuditListResponse(BaseModel):
    items: List[RecoveryAuditEntry] = Field(default_factory=list)
