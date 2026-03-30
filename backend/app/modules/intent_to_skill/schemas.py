from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.modules.skill_engine.schemas import SkillRunExecutionReport, SkillRunResponse, TriggerType


class IntentResolutionType(str, Enum):
    MATCHED_SKILL = "matched_skill"
    DRAFT_REQUIRED = "draft_required"


class IntentCandidateSkill(BaseModel):
    skill_key: str
    version: int
    score: float
    reason: str


class IntentDraftSuggestion(BaseModel):
    suggested_skill_key: str
    rationale: str
    recommended_capabilities: list[str] = Field(default_factory=list)


class IntentExecuteRequest(BaseModel):
    intent_text: str | None = Field(default=None, max_length=4000)
    source_url: str | None = Field(default=None, max_length=1000)
    problem_statement: str | None = Field(default=None, max_length=4000)
    context: dict[str, Any] = Field(default_factory=dict)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    auto_execute: bool = False
    min_confidence: float = Field(default=0.2, ge=0.0, le=1.0)
    trigger_type: TriggerType = Field(default=TriggerType.API)
    mission_id: str | None = Field(default=None, max_length=120)


class IntentExecuteResponse(BaseModel):
    resolution_type: IntentResolutionType
    normalized_intent: str
    confidence: float
    reason: str
    matched_skill_key: str | None = None
    matched_skill_version: int | None = None
    candidates: list[IntentCandidateSkill] = Field(default_factory=list)
    draft_suggestion: IntentDraftSuggestion | None = None
    skill_run: SkillRunResponse | None = None
    execution_report: SkillRunExecutionReport | None = None
