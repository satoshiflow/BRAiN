from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluatorType(str, Enum):
    RULE = "rule"
    MODEL = "model"
    HUMAN = "human"
    HYBRID = "hybrid"


class EvaluationStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PolicyCompliance(str, Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    UNKNOWN = "unknown"


class EvaluationResultResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    skill_run_id: UUID
    skill_key: str
    skill_version: int
    evaluator_type: EvaluatorType
    status: EvaluationStatus
    overall_score: float | None = None
    dimension_scores: dict[str, float] = Field(default_factory=dict)
    passed: bool
    criteria_snapshot: dict[str, Any] = Field(default_factory=dict)
    findings: dict[str, Any] = Field(default_factory=dict)
    recommendations: dict[str, Any] = Field(default_factory=dict)
    metrics_summary: dict[str, Any] = Field(default_factory=dict)
    provider_selection_snapshot: dict[str, Any] = Field(default_factory=dict)
    error_classification: str | None = None
    policy_compliance: PolicyCompliance
    policy_violations: list[dict[str, Any]] = Field(default_factory=list)
    correlation_id: str | None = None
    evaluation_revision: int
    created_at: datetime
    completed_at: datetime | None = None
    created_by: str

    model_config = {"from_attributes": True}


class EvaluationResultListResponse(BaseModel):
    items: list[EvaluationResultResponse] = Field(default_factory=list)
    total: int
