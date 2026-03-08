from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.skills_registry.schemas import OwnerScope, VersionSelector


class CapabilityDefinitionStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    BLOCKED = "blocked"


class CapabilityDefinitionCreate(BaseModel):
    owner_scope: OwnerScope = Field(default=OwnerScope.TENANT)
    capability_key: str = Field(..., min_length=1, max_length=120)
    version: int | None = Field(default=None, ge=1)
    domain: str = Field(..., min_length=1, max_length=80)
    description: str = Field(..., min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    default_timeout_ms: int = Field(default=30000, ge=1)
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    qos_targets: dict[str, Any] = Field(default_factory=dict)
    fallback_capability_key: str | None = Field(default=None, max_length=120)
    policy_constraints: dict[str, Any] = Field(default_factory=dict)


class CapabilityDefinitionUpdate(BaseModel):
    domain: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, min_length=1)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    default_timeout_ms: int | None = Field(default=None, ge=1)
    retry_policy: dict[str, Any] | None = None
    qos_targets: dict[str, Any] | None = None
    fallback_capability_key: str | None = Field(default=None, max_length=120)
    policy_constraints: dict[str, Any] | None = None


class CapabilityDefinitionResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    owner_scope: OwnerScope
    capability_key: str
    version: int
    status: CapabilityDefinitionStatus
    domain: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    default_timeout_ms: int
    retry_policy: dict[str, Any]
    qos_targets: dict[str, Any]
    fallback_capability_key: str | None = None
    policy_constraints: dict[str, Any]
    checksum_sha256: str
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CapabilityDefinitionListResponse(BaseModel):
    items: list[CapabilityDefinitionResponse] = Field(default_factory=list)
    total: int


class CapabilityDefinitionTransitionResponse(BaseModel):
    capability_key: str
    version: int
    previous_status: CapabilityDefinitionStatus
    status: CapabilityDefinitionStatus


class CapabilityRegistryResolveResponse(BaseModel):
    capability_key: str
    version: int
    owner_scope: OwnerScope
    tenant_id: str | None
    status: CapabilityDefinitionStatus
    checksum_sha256: str
    domain: str
    fallback_capability_key: str | None = None
