from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.capabilities.schemas import CapabilityExecutionResponse


class SkillRunState(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class TriggerType(str, Enum):
    API = "api"
    SCHEDULE = "schedule"
    MISSION = "mission"
    RETRY = "retry"


class SkillRunCreate(BaseModel):
    skill_key: str = Field(..., min_length=1, max_length=120)
    version: int | None = Field(default=None, ge=1)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(..., min_length=1, max_length=160)
    trigger_type: TriggerType = Field(default=TriggerType.API)
    mission_id: str | None = Field(default=None, max_length=120)
    deadline_at: datetime | None = None
    causation_id: str | None = Field(default=None, max_length=160)


class SkillRunResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    skill_key: str
    skill_version: int
    state: SkillRunState
    input_payload: dict[str, Any]
    plan_snapshot: dict[str, Any]
    provider_selection_snapshot: dict[str, Any]
    requested_by: str
    requested_by_type: str
    trigger_type: TriggerType
    policy_decision_id: UUID | None = None
    policy_decision: dict[str, Any]
    policy_snapshot: dict[str, Any]
    risk_tier: str
    correlation_id: str
    causation_id: str | None = None
    idempotency_key: str
    mission_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    deadline_at: datetime | None = None
    retry_count: int
    state_sequence: int = 0
    state_changed_at: datetime | None = None
    cost_estimate: float | None = None
    cost_actual: float | None = None
    output_payload: dict[str, Any]
    input_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    output_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    evidence_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    evaluation_summary: dict[str, Any]
    failure_code: str | None = None
    failure_reason_sanitized: str | None = None

    model_config = {"from_attributes": True}


class SkillRunListResponse(BaseModel):
    items: list[SkillRunResponse] = Field(default_factory=list)
    total: int


class SkillRunExecutionReport(BaseModel):
    skill_run: SkillRunResponse
    capability_results: list[CapabilityExecutionResponse] = Field(default_factory=list)
