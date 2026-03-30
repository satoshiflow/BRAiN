from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.discovery_layer.schemas import SkillProposalResponse


class EconomyAssessmentResponse(BaseModel):
    id: UUID
    tenant_id: str
    discovery_proposal_id: UUID
    skill_run_id: UUID
    status: str
    confidence_score: float
    frequency_score: float
    impact_score: float
    cost_score: float
    weighted_score: float
    score_breakdown: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class EconomyAnalyzeResponse(BaseModel):
    assessment: EconomyAssessmentResponse
    proposal: SkillProposalResponse


class EconomyQueueReviewResponse(BaseModel):
    assessment: EconomyAssessmentResponse


class SkillLifecycleItemResponse(BaseModel):
    skill_key: str
    latest_version: int
    value_score: float
    success_rate: float
    avg_overall_score: float
    total_runs: int
    succeeded_runs: int
    failed_runs: int
    trend_delta: float
    last_run_at: datetime | None = None


class SkillLifecycleSummaryResponse(BaseModel):
    total_skills: int
    total_runs: int
    avg_value_score: float
    avg_success_rate: float
    window_days: int


class SkillLifecycleAnalyticsResponse(BaseModel):
    summary: SkillLifecycleSummaryResponse
    items: list[SkillLifecycleItemResponse] = Field(default_factory=list)


class SkillMarketplaceRankItemResponse(BaseModel):
    rank: int
    skill_key: str
    latest_version: int
    market_score: float
    value_score: float
    success_rate: float
    avg_overall_score: float
    run_volume_score: float
    trend_delta: float
    last_run_at: datetime | None = None


class SkillMarketplaceRankingResponse(BaseModel):
    window_days: int
    generated_at: datetime
    items: list[SkillMarketplaceRankItemResponse] = Field(default_factory=list)
