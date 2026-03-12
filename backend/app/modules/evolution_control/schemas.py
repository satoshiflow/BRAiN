from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvolutionProposalResponse(BaseModel):
    id: UUID
    tenant_id: str
    pattern_id: UUID
    skill_run_id: UUID
    status: str
    target_skill_key: str
    summary: str
    governance_required: str
    validation_state: str
    metadata: dict[str, Any] = Field(default_factory=dict, alias="proposal_metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class EvolutionProposalCreateResponse(BaseModel):
    pattern_id: UUID
    proposal: EvolutionProposalResponse


class EvolutionReviewQueueItem(BaseModel):
    proposal: EvolutionProposalResponse
    ranking_score: float


class EvolutionReviewQueueResponse(BaseModel):
    items: list[EvolutionReviewQueueItem]


class EvolutionProposalTransitionRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
