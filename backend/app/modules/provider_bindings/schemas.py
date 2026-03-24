from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.skills_registry.schemas import OwnerScope


class ProviderType(str, Enum):
    LLM = "llm"
    TOOL = "tool"
    SERVICE = "service"
    SELF_HOSTED = "self_hosted"


class ProviderBindingStatus(str, Enum):
    DRAFT = "draft"
    ENABLED = "enabled"
    DISABLED = "disabled"
    QUARANTINED = "quarantined"


class ProviderBindingCreate(BaseModel):
    owner_scope: OwnerScope = Field(default=OwnerScope.SYSTEM)
    capability_key: str = Field(..., min_length=1, max_length=120)
    capability_version: int = Field(..., ge=1)
    provider_key: str = Field(..., min_length=1, max_length=120)
    provider_type: ProviderType = Field(default=ProviderType.SERVICE)
    adapter_key: str = Field(..., min_length=1, max_length=120)
    endpoint_ref: str = Field(..., min_length=1, max_length=255)
    model_or_tool_ref: str | None = Field(default=None, max_length=255)
    region: str | None = Field(default=None, max_length=64)
    priority: int = Field(default=100, ge=0)
    weight: float | None = Field(default=None, ge=0.0)
    cost_profile: dict[str, Any] = Field(default_factory=dict)
    sla_profile: dict[str, Any] = Field(default_factory=dict)
    policy_constraints: dict[str, Any] = Field(default_factory=dict)
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    definition_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    evidence_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)


class ProviderBindingResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    owner_scope: OwnerScope
    capability_id: UUID | None = None
    capability_key: str
    capability_version: int
    provider_key: str
    provider_type: ProviderType
    adapter_key: str
    endpoint_ref: str
    model_or_tool_ref: str | None = None
    region: str | None = None
    priority: int
    weight: float | None = None
    cost_profile: dict[str, Any]
    sla_profile: dict[str, Any]
    policy_constraints: dict[str, Any]
    status: ProviderBindingStatus
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    config: dict[str, Any]
    definition_artifact_refs: list[dict[str, Any]]
    evidence_artifact_refs: list[dict[str, Any]]
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResolvedProviderSelection(BaseModel):
    provider_binding_id: str
    selection_strategy: str = "priority_first"
    selection_reason: str
    policy_context: dict[str, Any] = Field(default_factory=dict)
    resolved_at: datetime
    binding_snapshot: dict[str, Any] = Field(default_factory=dict)
