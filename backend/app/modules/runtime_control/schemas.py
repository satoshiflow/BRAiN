from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RuntimeOverrideLevel(str, Enum):
    EMERGENCY = "emergency_override"
    GOVERNOR = "governor_override"
    MANUAL = "manual_approved_override"
    POLICY = "policy_decision"
    FEATURE_FLAGS = "feature_flags"
    REGISTRY = "registry_config"
    DEFAULTS = "hard_defaults"


class RuntimeDecisionContext(BaseModel):
    tenant_id: str | None = None
    environment: str = Field(default="local")
    mission_type: str = Field(default="general")
    skill_type: str | None = None
    agent_role: str | None = None
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    budget_state: dict[str, Any] = Field(default_factory=dict)
    system_health: dict[str, Any] = Field(default_factory=dict)
    feature_context: dict[str, Any] = Field(default_factory=dict)


class ResolverRequest(BaseModel):
    context: RuntimeDecisionContext


class AppliedPolicy(BaseModel):
    policy_id: str
    reason: str
    effect: str


class AppliedOverride(BaseModel):
    level: RuntimeOverrideLevel
    key: str
    value: Any
    reason: str


class ExplainTraceStep(BaseModel):
    level: RuntimeOverrideLevel
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)


class ResolverValidation(BaseModel):
    valid: bool
    issues: list[str] = Field(default_factory=list)


class ResolverResponse(BaseModel):
    decision_id: str
    effective_config: dict[str, Any]
    selected_model: str
    selected_worker: str
    selected_route: str
    applied_policies: list[AppliedPolicy] = Field(default_factory=list)
    applied_overrides: list[AppliedOverride] = Field(default_factory=list)
    explain_trace: list[ExplainTraceStep] = Field(default_factory=list)
    validation: ResolverValidation


class RuntimeControlInfo(BaseModel):
    name: str
    resolver_path: str
    override_priority: list[RuntimeOverrideLevel]
    notes: list[str] = Field(default_factory=list)


class OverrideRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RuntimeOverrideRequestCreate(BaseModel):
    key: str = Field(..., min_length=3, max_length=200)
    value: Any
    reason: str = Field(..., min_length=3, max_length=500)
    tenant_scope: str = Field(default="tenant", pattern="^(tenant|system)$")
    expires_at: str | None = None


class RuntimeOverrideRequestDecision(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class RuntimeOverrideRequestItem(BaseModel):
    request_id: str
    tenant_id: str | None = None
    tenant_scope: str
    key: str
    value: Any
    reason: str
    status: OverrideRequestStatus
    created_by: str
    created_at: str
    updated_at: str
    approved_by: str | None = None
    approved_at: str | None = None
    rejected_by: str | None = None
    rejected_at: str | None = None
    decision_reason: str | None = None
    expires_at: str | None = None


class RuntimeOverrideRequestListResponse(BaseModel):
    items: list[RuntimeOverrideRequestItem] = Field(default_factory=list)
    total: int


class RuntimeActiveOverride(BaseModel):
    request_id: str
    key: str
    value: Any
    reason: str
    tenant_id: str | None = None
    expires_at: str | None = None


class RuntimeActiveOverrideListResponse(BaseModel):
    items: list[RuntimeActiveOverride] = Field(default_factory=list)
    total: int


class RegistryVersionStatus(str, Enum):
    DRAFT = "draft"
    PROMOTED = "promoted"
    SUPERSEDED = "superseded"


class RuntimeRegistryVersionCreate(BaseModel):
    scope: str = Field(default="tenant", pattern="^(tenant|system)$")
    config_patch: dict[str, Any] = Field(default_factory=dict)
    reason: str = Field(..., min_length=3, max_length=500)


class RuntimeRegistryVersionPromoteRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class RuntimeRegistryVersionItem(BaseModel):
    version_id: str
    scope: str
    tenant_id: str | None = None
    status: RegistryVersionStatus
    config_patch: dict[str, Any]
    reason: str
    created_by: str
    created_at: str
    updated_at: str
    promoted_by: str | None = None
    promoted_at: str | None = None
    promotion_reason: str | None = None


class RuntimeRegistryVersionListResponse(BaseModel):
    items: list[RuntimeRegistryVersionItem] = Field(default_factory=list)
    total: int


class RuntimeControlTimelineEvent(BaseModel):
    event_id: str
    event_type: str
    entity_type: str
    entity_id: str
    actor_id: str | None = None
    actor_type: str | None = None
    tenant_id: str | None = None
    correlation_id: str | None = None
    created_at: str
    payload: dict[str, Any] = Field(default_factory=dict)


class RuntimeControlTimelineResponse(BaseModel):
    items: list[RuntimeControlTimelineEvent] = Field(default_factory=list)
    total: int


class ExternalOpsAlertItem(BaseModel):
    alert_id: str
    severity: str
    category: str
    title: str
    summary: str
    app_slug: str | None = None
    request_id: str | None = None
    escalation_id: str | None = None
    target_ref: str | None = None
    skill_run_id: str | None = None
    task_id: str | None = None
    age_seconds: int


class ExternalOpsSloMetrics(BaseModel):
    pending_action_requests: int = 0
    stale_action_requests: int = 0
    stale_supervisor_escalations: int = 0
    handoff_failures_24h: int = 0
    retry_approvals_24h: int = 0
    avg_action_request_age_seconds: int = 0


class ExternalOpsObservabilityResponse(BaseModel):
    generated_at: str
    metrics: ExternalOpsSloMetrics
    alerts: list[ExternalOpsAlertItem] = Field(default_factory=list)
