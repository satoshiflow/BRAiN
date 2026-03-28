from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class SkillOptimizerRecommendationResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    skill_key: str
    skill_version: int
    recommendation_type: str
    confidence: float
    status: str
    rationale: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    source_snapshot: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    created_by: str

    model_config = {"from_attributes": True}


class SkillOptimizerRecommendationListResponse(BaseModel):
    items: list[SkillOptimizerRecommendationResponse] = Field(default_factory=list)
    total: int


class OptimizerRecommendationStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


class SkillOptimizerRecommendationStatusUpdateRequest(BaseModel):
    status: OptimizerRecommendationStatus
    reason: str | None = Field(default=None, max_length=500)


class SkillOptimizerRecommendationSummaryResponse(BaseModel):
    skill_key: str
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_type: dict[str, int] = Field(default_factory=dict)
    average_confidence: float | None = None


class SkillOptimizerOpsSnapshotResponse(BaseModel):
    skill_key: str
    recommendation_summary: SkillOptimizerRecommendationSummaryResponse
    evaluation_total: int
    evaluation_passed: int
    evaluation_failed: int
    evaluation_non_compliant: int
    latest_evaluation_score: float | None = None
