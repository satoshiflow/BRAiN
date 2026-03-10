"""Schemas for OpenCode repair loop."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RepairTicketStatus(str, Enum):
    OPEN = "open"
    TRIAGED = "triaged"
    PATCH_PROPOSED = "patch_proposed"
    VALIDATED = "validated"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"


class RepairTicketSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OpenCodeJobMode(str, Enum):
    PLAN = "plan"
    BUILD = "build"
    HEAL = "heal"
    EVOLVE = "evolve"


class OpenCodeJobStatus(str, Enum):
    REQUESTED = "requested"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class OpenCodeJobScope(BaseModel):
    module: str = Field(..., min_length=1, max_length=128)
    entity_id: str = Field(..., min_length=1, max_length=256)
    tenant_id: str = Field(..., min_length=1, max_length=128)


class OpenCodeJobConstraints(BaseModel):
    timeout_seconds: int = Field(default=600, ge=30, le=7200)
    max_iterations: int = Field(default=1, ge=1, le=10)
    risk_level: str = Field(default="low", pattern="^(low|medium|high)$")
    approval_required: bool = False
    blast_radius_limit: int = Field(default=1, ge=1, le=100)


class OpenCodeJobContext(BaseModel):
    trigger_event: str = Field(..., min_length=1, max_length=128)
    original_request: Dict[str, Any] = Field(default_factory=dict)


class OpenCodeJobContractCreateRequest(BaseModel):
    correlation_id: str = Field(..., min_length=8, max_length=128)
    mode: OpenCodeJobMode
    scope: OpenCodeJobScope
    constraints: OpenCodeJobConstraints
    context: OpenCodeJobContext
    created_by: str = Field(default="system", min_length=1, max_length=128)


class OpenCodeJobContract(BaseModel):
    job_id: str
    correlation_id: str
    mode: OpenCodeJobMode
    scope: OpenCodeJobScope
    constraints: OpenCodeJobConstraints
    context: OpenCodeJobContext
    status: OpenCodeJobStatus
    created_at: datetime
    created_by: str


class RepairTicketCreateRequest(BaseModel):
    source_module: str = Field(..., min_length=1, max_length=128)
    source_event_type: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=3, max_length=256)
    description: str = Field(..., min_length=3, max_length=5000)
    severity: RepairTicketSeverity = RepairTicketSeverity.MEDIUM
    correlation_id: Optional[str] = Field(default=None, max_length=128)
    actor: str = Field(default="system", min_length=1, max_length=128)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    governance_required: bool = False


class RepairTicketUpdateRequest(BaseModel):
    ticket_id: str = Field(..., min_length=1, max_length=128)
    status: RepairTicketStatus
    note: str = Field(..., min_length=1, max_length=4000)
    actor: str = Field(default="system", min_length=1, max_length=128)
    evidence: Dict[str, Any] = Field(default_factory=dict)


class RepairTicket(BaseModel):
    ticket_id: str
    source_module: str
    source_event_type: str
    title: str
    description: str
    severity: RepairTicketSeverity
    status: RepairTicketStatus
    correlation_id: Optional[str] = None
    actor: str
    governance_required: bool
    evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RepairAuditEntry(BaseModel):
    audit_id: str
    ticket_id: str
    action: str
    actor: str
    details: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    timestamp: datetime


class RepairTicketResponse(BaseModel):
    ticket: RepairTicket


class RepairTicketsResponse(BaseModel):
    items: List[RepairTicket]


class RepairAuditResponse(BaseModel):
    items: List[RepairAuditEntry]


class OpenCodeJobResponse(BaseModel):
    job: OpenCodeJobContract


class RepairAutotriggerRequest(BaseModel):
    source_module: str = Field(..., min_length=1, max_length=128)
    source_event_type: str = Field(..., min_length=1, max_length=128)
    subject_id: str = Field(..., min_length=1, max_length=128)
    summary: str = Field(..., min_length=3, max_length=1000)
    severity: RepairTicketSeverity = RepairTicketSeverity.MEDIUM
    correlation_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    actor: str = Field(default="system")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
