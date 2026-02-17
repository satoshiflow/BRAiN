"""
NeuroRail Audit Schemas.

Defines audit event models for immutable logging of all NeuroRail events.
Integrates with EventStream for real-time observability.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import uuid4
from pydantic import BaseModel, Field


# ============================================================================
# Audit Event Model
# ============================================================================

class AuditEvent(BaseModel):
    """
    Immutable audit event for NeuroRail system.

    All events are:
    - Append-only (no updates or deletes)
    - Traced to entity hierarchy (mission → plan → job → attempt → resource)
    - Published to EventStream for real-time monitoring
    - Persisted to PostgreSQL for querying and analysis
    """
    audit_id: str = Field(
        default_factory=lambda: f"aud_{uuid4().hex[:12]}",
        description="Unique audit event identifier"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Event timestamp (UTC)"
    )

    # Trace Context (hierarchical entity IDs)
    mission_id: Optional[str] = Field(None, description="Mission ID (m_xxxxx)")
    plan_id: Optional[str] = Field(None, description="Plan ID (p_xxxxx)")
    job_id: Optional[str] = Field(None, description="Job ID (j_xxxxx)")
    attempt_id: Optional[str] = Field(None, description="Attempt ID (a_xxxxx)")
    resource_uuid: Optional[str] = Field(None, description="Resource UUID (r_xxxxx)")

    # Event Details
    event_type: str = Field(
        ...,
        description="Event type: state_transition, resource_allocation, error, decision, budget_check, reflex_trigger"
    )
    event_category: str = Field(
        ...,
        description="Event category: execution, governance, safety, telemetry"
    )
    severity: str = Field(
        default="info",
        description="Severity: info, warning, error, critical"
    )

    # Content
    message: str = Field(..., description="Human-readable event message")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event-specific details (error_code, budget_consumed, etc.)"
    )

    # Attribution
    caused_by_agent: Optional[str] = Field(
        None,
        description="Agent that triggered this event"
    )
    caused_by_event: Optional[str] = Field(
        None,
        description="Audit ID of event that caused this event"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "audit_id": "aud_abc123def456",
                "timestamp": "2025-12-30T14:00:00Z",
                "mission_id": "m_a1b2c3d4e5f6",
                "plan_id": "p_f6e5d4c3b2a1",
                "job_id": "j_123456789abc",
                "attempt_id": "a_abc123def456",
                "event_type": "state_transition",
                "event_category": "execution",
                "severity": "info",
                "message": "Job j_123456789abc transitioned from ready to running",
                "details": {"from_state": "ready", "to_state": "running"},
                "caused_by_agent": "worker_1",
                "caused_by_event": None
            }
        }


# ============================================================================
# Audit Query
# ============================================================================

class AuditQuery(BaseModel):
    """Query parameters for audit log search."""
    mission_id: Optional[str] = None
    job_id: Optional[str] = None
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    severity: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditQueryResponse(BaseModel):
    """Response for audit query."""
    events: List[AuditEvent]
    total: int
    limit: int
    offset: int


# ============================================================================
# Specialized Audit Event Types
# ============================================================================

class StateTransitionAudit(BaseModel):
    """Audit event for state transitions."""
    entity_type: str
    entity_id: str
    from_state: Optional[str]
    to_state: str
    transition: str


class ResourceAllocationAudit(BaseModel):
    """Audit event for resource allocations."""
    resource_type: str
    allocated: float
    limit: Optional[float]
    unit: str  # "tokens", "ms", "mb"


class BudgetCheckAudit(BaseModel):
    """Audit event for budget checks."""
    check_type: str  # "time", "tokens", "memory"
    consumed: float
    limit: float
    remaining: float
    allowed: bool


class ErrorAudit(BaseModel):
    """Audit event for errors."""
    error_code: str
    error_category: str  # "mechanical", "ethical", "system"
    error_message: str
    retriable: bool


class GovernanceDecisionAudit(BaseModel):
    """Audit event for governance decisions."""
    decision_type: str
    decision_id: str
    allowed: bool
    reason: str
    enforcement_actions: List[str]


# ============================================================================
# Audit Statistics
# ============================================================================

class AuditStats(BaseModel):
    """Audit log statistics."""
    total_events: int
    events_by_category: Dict[str, int]
    events_by_severity: Dict[str, int]
    events_by_type: Dict[str, int]
    time_range_start: datetime
    time_range_end: datetime
