from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CognitiveAssessmentRequest(BaseModel):
    intent_text: str | None = Field(default=None, max_length=4000)
    problem_statement: str | None = Field(default=None, max_length=4000)
    source_url: str | None = Field(default=None, max_length=1000)
    mission_id: str | None = Field(default=None, max_length=120)
    context: dict[str, Any] = Field(default_factory=dict)
    min_confidence: float = Field(default=0.2, ge=0.0, le=1.0)


class PerceptionSnapshot(BaseModel):
    normalized_intent: str
    intent_keywords: list[str] = Field(default_factory=list)
    intent_modes: list[str] = Field(default_factory=list)
    risk_hints: list[str] = Field(default_factory=list)
    impact_hints: list[str] = Field(default_factory=list)
    novelty_hints: list[str] = Field(default_factory=list)


class AssociationCase(BaseModel):
    source_type: str
    source_id: str
    title: str
    score: float
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssociationTrace(BaseModel):
    memory_cases: list[AssociationCase] = Field(default_factory=list)
    knowledge_cases: list[AssociationCase] = Field(default_factory=list)
    total_cases: int = 0


class EvaluationSignal(BaseModel):
    confidence: float
    novelty_score: float
    impact_score: float
    governance_hints: list[str] = Field(default_factory=list)
    risk_hints: list[str] = Field(default_factory=list)


class CognitiveAssessmentResult(BaseModel):
    result_version: str = "v1"
    confidence: float
    risk: list[str] = Field(default_factory=list)
    impact: float
    novelty: float
    governance_flags: list[str] = Field(default_factory=list)
    routing_hint: str | None = None


class CognitiveSkillCandidate(BaseModel):
    skill_key: str
    version: int
    score: float
    reason: str


class CognitiveAssessmentResponse(BaseModel):
    assessment_id: UUID
    tenant_id: str | None = None
    mission_id: str | None = None
    perception: PerceptionSnapshot
    association: AssociationTrace
    evaluation: EvaluationSignal
    result: CognitiveAssessmentResult
    recommended_skill_candidates: list[CognitiveSkillCandidate] = Field(default_factory=list)
    created_at: datetime


class CognitiveLearningFeedbackResponse(BaseModel):
    id: UUID
    assessment_id: UUID
    skill_run_id: UUID
    evaluation_result_id: UUID | None = None
    experience_record_id: UUID | None = None
    outcome_state: str
    overall_score: float | None = None
    success: bool
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
