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


class EvolutionProposalFromRunResponse(BaseModel):
    skill_run_id: UUID
    proposal: EvolutionProposalResponse
    blocked: bool = False
    block_reason: str | None = None


class EvolutionReviewQueueItem(BaseModel):
    proposal: EvolutionProposalResponse
    ranking_score: float


class EvolutionReviewQueueResponse(BaseModel):
    items: list[EvolutionReviewQueueItem]


class EvolutionProposalTransitionRequest(BaseModel):
    status: str = Field(..., min_length=1, max_length=32)
    metadata_patch: dict[str, Any] = Field(default_factory=dict)


class AdaptiveFreezeRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class AdaptiveFreezeStatusResponse(BaseModel):
    tenant_id: str
    adaptive_frozen: bool
    freeze_reason: str | None = None
    frozen_by: str | None = None
    frozen_at: datetime | None = None
    updated_at: datetime | None = None


class EvolutionOpsSummaryResponse(BaseModel):
    tenant_id: str
    adaptive_frozen: bool
    proposal_counts: dict[str, int] = Field(default_factory=dict)
    review_queue_count: int
    blocked_count: int
    applied_count: int
    recent_events: list[dict[str, Any]] = Field(default_factory=list)
