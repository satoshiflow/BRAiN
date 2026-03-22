from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ExperienceRecordResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    skill_run_id: UUID
    evaluation_result_id: UUID | None = None
    idempotency_key: str
    state: str
    failure_code: str | None = None
    summary: str
    evaluation_summary: dict[str, Any] = Field(default_factory=dict)
    signals: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class ExperienceIngestResponse(BaseModel):
    skill_run_id: UUID
    experience: ExperienceRecordResponse
