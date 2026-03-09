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
