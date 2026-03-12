from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceThresholdsResponse(BaseModel):
    min_pattern_confidence: float
    min_recurrence_support: float
    min_observer_signals: int
    min_knowledge_items: int


class ProposalEvidenceResponse(BaseModel):
    evidence_sources: list[str] = Field(default_factory=list)
    observer_signal_count: int = 0
    knowledge_item_count: int = 0
    thresholds: EvidenceThresholdsResponse
    evidence_score: float


class SkillGapResponse(BaseModel):
    id: UUID
    tenant_id: str
    skill_run_id: UUID
    pattern_id: UUID
    gap_type: str
    summary: str
    severity: str
    confidence: float
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class CapabilityGapResponse(BaseModel):
    id: UUID
    tenant_id: str
    skill_run_id: UUID
    pattern_id: UUID
    capability_key: str
    summary: str
    severity: str
    confidence: float
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillProposalResponse(BaseModel):
    id: UUID
    tenant_id: str
    skill_run_id: UUID
    pattern_id: UUID
    skill_gap_id: UUID
    capability_gap_id: UUID
    target_skill_key: str
    status: str
    proposal_summary: str
    proposal_evidence: dict[str, Any] = Field(default_factory=dict)
    dedup_key: str
    evidence_score: float
    priority_score: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DiscoveryAnalyzeResponse(BaseModel):
    skill_run_id: UUID
    skill_gap: SkillGapResponse
    capability_gap: CapabilityGapResponse
    proposal: SkillProposalResponse
    evidence: ProposalEvidenceResponse


class QueueReviewResponse(BaseModel):
    proposal: SkillProposalResponse
    evolution_proposal_id: UUID


class DiscoveryListResponse(BaseModel):
    proposals: list[SkillProposalResponse]
