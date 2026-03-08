from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CapabilityExecutionStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class CapabilityExecutionRequest(BaseModel):
    tenant_id: str | None = None
    skill_run_id: str | None = None
    capability_key: str = Field(..., min_length=1, max_length=120)
    capability_version: int = Field(..., ge=1)
    provider_binding_id: str = Field(..., min_length=1, max_length=160)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    policy_snapshot_hash: str | None = Field(default=None, max_length=128)
    correlation_id: str = Field(..., min_length=1, max_length=160)
    causation_id: str | None = Field(default=None, max_length=160)
    actor_id: str | None = Field(default=None, max_length=120)
    risk_tier: str = Field(default="medium", min_length=1, max_length=32)
    deadline_at: datetime | None = None


class CapabilityExecutionSuccess(BaseModel):
    status: CapabilityExecutionStatus = CapabilityExecutionStatus.SUCCEEDED
    output: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0
    cost_actual: float | None = None
    provider_facts: dict[str, Any] = Field(default_factory=dict)
    trace_refs: dict[str, Any] = Field(default_factory=dict)
    adapter_version: str = "v1"


class CapabilityExecutionError(BaseModel):
    status: CapabilityExecutionStatus = CapabilityExecutionStatus.FAILED
    error_code: str
    retryable: bool = False
    provider_unavailable: bool = False
    provider_content_blocked: bool = False
    timeout: bool = False
    sanitized_message: str
    provider_error_ref: str | None = None
    trace_refs: dict[str, Any] = Field(default_factory=dict)
    adapter_version: str = "v1"


class CapabilityAdapterHealth(BaseModel):
    provider_binding_id: str
    capability_key: str
    healthy: bool
    latency_ms: float | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class ProviderBindingSpec(BaseModel):
    provider_binding_id: str = Field(..., min_length=1, max_length=160)
    tenant_id: str | None = None
    owner_scope: str = Field(default="system", min_length=1, max_length=16)
    capability_key: str = Field(..., min_length=1, max_length=120)
    capability_version: int = Field(..., ge=1)
    adapter_key: str = Field(..., min_length=1, max_length=120)
    provider_key: str = Field(..., min_length=1, max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)
    enabled: bool = True


class CapabilityExecutionResponse(BaseModel):
    capability_key: str
    capability_version: int
    provider_binding_id: str
    result: CapabilityExecutionSuccess | CapabilityExecutionError
