from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.skills_registry.schemas import OwnerScope


class ProviderType(str, Enum):
    CLOUD = "cloud"
    GATEWAY = "gateway"
    LOCAL = "local"


class AuthMode(str, Enum):
    API_KEY = "api_key"
    NONE = "none"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ProviderAccountCreate(BaseModel):
    owner_scope: OwnerScope = Field(default=OwnerScope.SYSTEM)
    slug: str = Field(..., min_length=1, max_length=120)
    display_name: str = Field(..., min_length=1, max_length=160)
    provider_type: ProviderType = Field(default=ProviderType.CLOUD)
    base_url: str = Field(..., min_length=1, max_length=255)
    auth_mode: AuthMode = Field(default=AuthMode.API_KEY)
    is_enabled: bool = True
    is_local: bool = False
    supports_chat: bool = True
    supports_embeddings: bool = False
    supports_responses: bool = False
    notes: str | None = None


class ProviderAccountUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=160)
    provider_type: ProviderType | None = None
    base_url: str | None = Field(default=None, min_length=1, max_length=255)
    auth_mode: AuthMode | None = None
    is_enabled: bool | None = None
    is_local: bool | None = None
    supports_chat: bool | None = None
    supports_embeddings: bool | None = None
    supports_responses: bool | None = None
    notes: str | None = None


class ProviderAccountResponse(BaseModel):
    id: UUID
    tenant_id: str | None
    owner_scope: OwnerScope
    slug: str
    display_name: str
    provider_type: ProviderType
    base_url: str
    auth_mode: AuthMode
    is_enabled: bool
    is_local: bool
    supports_chat: bool
    supports_embeddings: bool
    supports_responses: bool
    notes: str | None
    health_status: HealthStatus
    last_health_at: datetime | None
    last_health_error: str | None
    secret_configured: bool = False
    key_hint_masked: str | None = None
    created_by: str
    updated_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderCredentialSetRequest(BaseModel):
    api_key: str = Field(..., min_length=10, max_length=4096)
    activate: bool = True


class ProviderCredentialResponse(BaseModel):
    provider_id: UUID
    is_active: bool
    key_hint_masked: str
    updated_at: datetime


class ProviderModelCreate(BaseModel):
    provider_id: UUID
    model_name: str = Field(..., min_length=1, max_length=160)
    display_name: str | None = Field(default=None, max_length=160)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True
    priority: int = Field(default=100, ge=0)
    cost_class: str | None = Field(default=None, max_length=32)
    latency_class: str | None = Field(default=None, max_length=32)
    quality_class: str | None = Field(default=None, max_length=32)
    supports_tools: bool = False
    supports_json: bool = False
    supports_streaming: bool = True


class ProviderModelUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=160)
    capabilities: dict[str, Any] | None = None
    is_enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0)
    cost_class: str | None = Field(default=None, max_length=32)
    latency_class: str | None = Field(default=None, max_length=32)
    quality_class: str | None = Field(default=None, max_length=32)
    supports_tools: bool | None = None
    supports_json: bool | None = None
    supports_streaming: bool | None = None


class ProviderModelResponse(BaseModel):
    id: UUID
    provider_id: UUID
    model_name: str
    display_name: str | None
    capabilities: dict[str, Any]
    is_enabled: bool
    priority: int
    cost_class: str | None
    latency_class: str | None
    quality_class: str | None
    supports_tools: bool
    supports_json: bool
    supports_streaming: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProviderTestRequest(BaseModel):
    model_name: str | None = Field(default=None, max_length=160)
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)


class ProviderTestResponse(BaseModel):
    provider_id: UUID
    status: HealthStatus
    success: bool
    latency_ms: int | None = None
    error_code: str | None = None
    error_message: str | None = None
    checked_at: datetime
    binding_projection: dict[str, Any] = Field(default_factory=dict)


class ProviderBindingProjectionResponse(BaseModel):
    provider_id: UUID
    projection: dict[str, Any]


class ProviderRunRequest(BaseModel):
    provider_id: UUID
    model_name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ProviderRunResponse(BaseModel):
    accepted: bool = True
    message: str
    route: str = "/api/capabilities/execute"
