from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class OwnerScope(str, Enum):
    TENANT = "tenant"
    SYSTEM = "system"


class SkillDefinitionStatus(str, Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"
    REJECTED = "rejected"


class QualityProfile(str, Enum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    HIGH = "high"
    STRICT = "strict"


class FallbackPolicy(str, Enum):
    FORBIDDEN = "forbidden"
    ALLOWED = "allowed"
    REQUIRED = "required"


class RiskTier(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrustTier(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    RESTRICTED = "restricted"
    SENSITIVE = "sensitive"


class VersionSelector(str, Enum):
    ACTIVE = "active"
    EXACT = "exact"
    MIN = "min"


class SkillSortBy(str, Enum):
    SKILL_KEY = "skill_key"
    UPDATED_AT = "updated_at"
    VALUE_SCORE = "value_score"


class CapabilityRef(BaseModel):
    capability_key: str = Field(..., min_length=1, max_length=120)
    version_selector: VersionSelector = Field(default=VersionSelector.ACTIVE)
    version_value: int | None = Field(default=None, ge=1)

    @field_validator("version_value")
    @classmethod
    def validate_version_value(cls, value: int | None, info):
        selector = info.data.get("version_selector")
        if selector in {VersionSelector.EXACT, VersionSelector.MIN} and value is None:
            raise ValueError("version_value is required for exact or min selectors")
        return value


class SkillDefinitionCreate(BaseModel):
    owner_scope: OwnerScope = Field(default=OwnerScope.TENANT)
    skill_key: str = Field(..., min_length=1, max_length=120)
    version: int | None = Field(default=None, ge=1)
    purpose: str = Field(..., min_length=1)
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    required_capabilities: list[CapabilityRef] = Field(default_factory=list)
    optional_capabilities: list[CapabilityRef] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    quality_profile: QualityProfile = Field(default=QualityProfile.STANDARD)
    fallback_policy: FallbackPolicy = Field(default=FallbackPolicy.ALLOWED)
    evaluation_criteria: dict[str, Any] = Field(default_factory=dict)
    risk_tier: RiskTier = Field(default=RiskTier.MEDIUM)
    policy_pack_ref: str = Field(default="default", min_length=1, max_length=120)
    trust_tier_min: TrustTier = Field(default=TrustTier.INTERNAL)
    value_score: float = Field(default=0.0, ge=0.0, le=1.0)
    effort_saved_hours: float = Field(default=0.0, ge=0.0)
    complexity_level: str = Field(default="medium", min_length=1, max_length=32)
    quality_impact: float = Field(default=0.0, ge=0.0, le=1.0)
    builder_role: str = Field(default="manual", min_length=1, max_length=64)
    definition_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    example_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    builder_artifact_refs: list[dict[str, Any]] = Field(default_factory=list)


class SkillDefinitionUpdate(BaseModel):
    purpose: str | None = Field(default=None, min_length=1)
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    required_capabilities: list[CapabilityRef] | None = None
    optional_capabilities: list[CapabilityRef] | None = None
    constraints: dict[str, Any] | None = None
    quality_profile: QualityProfile | None = None
    fallback_policy: FallbackPolicy | None = None
    evaluation_criteria: dict[str, Any] | None = None
    risk_tier: RiskTier | None = None
    policy_pack_ref: str | None = Field(default=None, min_length=1, max_length=120)
    trust_tier_min: TrustTier | None = None
    value_score: float | None = Field(default=None, ge=0.0, le=1.0)
    effort_saved_hours: float | None = Field(default=None, ge=0.0)
    complexity_level: str | None = Field(default=None, min_length=1, max_length=32)
    quality_impact: float | None = Field(default=None, ge=0.0, le=1.0)
    definition_artifact_refs: list[dict[str, Any]] | None = None
    example_artifact_refs: list[dict[str, Any]] | None = None
    builder_artifact_refs: list[dict[str, Any]] | None = None


class SkillDefinitionResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    owner_scope: OwnerScope
    skill_key: str
    version: int
    status: SkillDefinitionStatus
    purpose: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    required_capabilities: list[CapabilityRef]
    optional_capabilities: list[CapabilityRef]
    constraints: dict[str, Any]
    quality_profile: QualityProfile
    fallback_policy: FallbackPolicy
    evaluation_criteria: dict[str, Any]
    risk_tier: RiskTier
    policy_pack_ref: str
    trust_tier_min: TrustTier
    value_score: float
    effort_saved_hours: float
    complexity_level: str
    quality_impact: float
    builder_role: str
    definition_artifact_refs: list[dict[str, Any]]
    example_artifact_refs: list[dict[str, Any]]
    builder_artifact_refs: list[dict[str, Any]]
    checksum_sha256: str
    created_by: str
    updated_by: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillDefinitionListResponse(BaseModel):
    items: list[SkillDefinitionResponse] = Field(default_factory=list)
    total: int


class SkillRegistryResolveResponse(BaseModel):
    skill_key: str
    version: int
    owner_scope: OwnerScope
    tenant_id: str | None
    checksum_sha256: str
    required_capabilities: list[CapabilityRef]
    optional_capabilities: list[CapabilityRef]
    status: SkillDefinitionStatus


class SkillDefinitionTransitionResponse(BaseModel):
    skill_key: str
    version: int
    previous_status: SkillDefinitionStatus
    status: SkillDefinitionStatus


class SkillDefinitionValueResponse(BaseModel):
    skill_key: str
    version: int
    value_score: float
    source: str
    effort_saved_hours: float
    quality_impact: float
    complexity_level: str
    risk_tier: str
    breakdown: dict[str, Any] = Field(default_factory=dict)


class SkillValueHistoryItem(BaseModel):
    run_id: str
    skill_version: int
    state: str
    created_at: datetime
    overall_score: float | None = None
    value_score: float | None = None
    quality_impact: float | None = None
    effort_saved_hours: float | None = None
    source: str | None = None


class SkillValueHistoryResponse(BaseModel):
    skill_key: str
    items: list[SkillValueHistoryItem] = Field(default_factory=list)
    total: int
