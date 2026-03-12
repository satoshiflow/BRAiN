from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class PatternCandidateResponse(BaseModel):
    id: UUID
    tenant_id: str
    insight_id: UUID
    skill_run_id: UUID
    status: str
    confidence: float
    recurrence_support: float
    pattern_summary: str
    failure_modes: list[str] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PatternDeriveResponse(BaseModel):
    skill_run_id: UUID
    pattern: PatternCandidateResponse
