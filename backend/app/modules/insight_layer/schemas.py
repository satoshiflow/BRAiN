from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class InsightCandidateResponse(BaseModel):
    id: UUID
    tenant_id: str
    experience_id: UUID
    skill_run_id: UUID
    status: str
    confidence: float
    scope: str
    hypothesis: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InsightDeriveResponse(BaseModel):
    skill_run_id: UUID
    insight: InsightCandidateResponse
