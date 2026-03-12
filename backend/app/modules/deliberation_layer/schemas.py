from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


_FORBIDDEN_REASONING_KEYS = {
    "chain_of_thought",
    "raw_chain_of_thought",
    "reasoning_trace",
    "internal_reasoning",
    "cot",
}


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _contains_forbidden_reasoning_keys(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).strip().lower()
            if lowered in _FORBIDDEN_REASONING_KEYS:
                return True
            if _contains_forbidden_reasoning_keys(nested):
                return True
    elif isinstance(value, list):
        for nested in value:
            if _contains_forbidden_reasoning_keys(nested):
                return True
    return False


class DeliberationSummaryCreate(BaseModel):
    alternatives: list[str] = Field(default_factory=list, max_length=10)
    rationale_summary: str = Field(..., min_length=1, max_length=2000)
    uncertainty: float = Field(default=0.0, ge=0.0, le=1.0)
    open_tensions: list[str] = Field(default_factory=list, max_length=20)
    evidence: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    @field_validator("evidence")
    @classmethod
    def validate_evidence(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 20:
            raise ValueError("evidence may contain at most 20 keys")
        if _contains_forbidden_reasoning_keys(value):
            raise ValueError("evidence contains forbidden reasoning fields")
        for key, nested in value.items():
            if len(str(key)) > 80:
                raise ValueError("evidence keys must be <= 80 characters")
            if not _is_scalar(nested):
                raise ValueError("evidence supports scalar values only")
            if isinstance(nested, str) and len(nested) > 300:
                raise ValueError("evidence string values must be <= 300 characters")
        return value


class DeliberationSummaryResponse(BaseModel):
    id: UUID
    tenant_id: str
    mission_id: str
    alternatives: list[str]
    rationale_summary: str
    uncertainty: float
    open_tensions: list[str]
    evidence: dict[str, Any]
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class MissionTensionCreate(BaseModel):
    hypothesis: str = Field(..., min_length=1, max_length=1500)
    perspective: str = Field(..., min_length=1, max_length=1500)
    tension: str = Field(..., min_length=1, max_length=1500)
    evidence: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}

    @field_validator("evidence")
    @classmethod
    def validate_evidence(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 20:
            raise ValueError("evidence may contain at most 20 keys")
        if _contains_forbidden_reasoning_keys(value):
            raise ValueError("evidence contains forbidden reasoning fields")
        for key, nested in value.items():
            if len(str(key)) > 80:
                raise ValueError("evidence keys must be <= 80 characters")
            if not _is_scalar(nested):
                raise ValueError("evidence supports scalar values only")
            if isinstance(nested, str) and len(nested) > 300:
                raise ValueError("evidence string values must be <= 300 characters")
        return value


class MissionTensionResponse(BaseModel):
    id: UUID
    tenant_id: str
    mission_id: str
    hypothesis: str
    perspective: str
    tension: str
    status: str
    evidence: dict[str, Any]
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MissionTensionListResponse(BaseModel):
    items: list[MissionTensionResponse] = Field(default_factory=list)
    total: int
