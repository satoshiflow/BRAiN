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
