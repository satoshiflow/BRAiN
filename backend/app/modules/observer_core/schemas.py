from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ObserverSignalResponse(BaseModel):
    id: UUID
    tenant_id: str
    source_module: str
    source_event_type: str
    source_event_id: str | None = None
    correlation_id: str | None = None
    entity_type: str
    entity_id: str
    signal_class: str
    severity: str
    occurred_at: datetime
    ingested_at: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    payload_hash: str
    ordering_key: str | None = None

    model_config = {"from_attributes": True}


class ObserverSignalListResponse(BaseModel):
    items: list[ObserverSignalResponse] = Field(default_factory=list)
    total: int


class ObserverStateResponse(BaseModel):
    id: UUID
    tenant_id: str
    scope_type: str
    scope_entity_type: str
    scope_entity_id: str
    snapshot_version: int
    last_signal_id: UUID | None = None
    last_occurred_at: datetime | None = None
    health_summary: dict[str, Any] = Field(default_factory=dict)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    execution_summary: dict[str, Any] = Field(default_factory=dict)
    queue_summary: dict[str, Any] = Field(default_factory=dict)
    audit_refs: list[dict[str, Any] | str] = Field(default_factory=list)
    snapshot_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ObserverSummaryResponse(BaseModel):
    tenant_id: str
    snapshot_version: int
    health_summary: dict[str, Any] = Field(default_factory=dict)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    execution_summary: dict[str, Any] = Field(default_factory=dict)
    queue_summary: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime
