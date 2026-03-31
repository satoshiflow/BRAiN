"""Config Management - Schemas"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ConfigType(str):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    JSON = "json"


class ConfigCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: Any = Field(...)
    type: str = Field(default="string")
    environment: str = Field(default="default")
    is_secret: bool = Field(default=False)
    description: Optional[str] = Field(default=None)


class ConfigUpdate(BaseModel):
    value: Optional[Any] = Field(default=None)
    type: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    is_secret: Optional[bool] = Field(default=None)


class ConfigResponse(BaseModel):
    id: UUID = Field(...)
    key: str = Field(...)
    value: Any = Field(...)
    type: str = Field(...)
    environment: str = Field(...)
    is_secret: bool = Field(...)
    description: Optional[str] = Field(default=None)
    version: int = Field(...)
    created_by: Optional[str] = Field(default=None)
    updated_by: Optional[str] = Field(default=None)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)

    class Config:
        from_attributes = True


class ConfigListResponse(BaseModel):
    items: List[ConfigResponse] = Field(default_factory=list)
    total: int = Field(...)
    environment: str = Field(default="all")


class ConfigBulkUpdate(BaseModel):
    configs: Dict[str, Any] = Field(..., description="Key-value pairs to update")
    environment: str = Field(default="default")


class ConfigEvent(BaseModel):
    event_type: str = Field(...)
    key: str = Field(...)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)


ConfigClassification = Literal["secret", "sensitive", "public_config"]
ConfigValueType = Literal["string", "integer", "boolean", "url", "json", "pem"]


class VaultDefinitionResponse(BaseModel):
    key: str
    label: str
    description: str
    classification: ConfigClassification
    value_type: ConfigValueType
    editable: bool
    generator_supported: bool
    rotation_supported: bool
    validation: dict[str, Any] = Field(default_factory=dict)


class VaultDefinitionsListResponse(BaseModel):
    items: list[VaultDefinitionResponse]
    total: int


class VaultValueResponse(BaseModel):
    key: str
    classification: ConfigClassification
    value_type: ConfigValueType
    effective_source: Literal["db_override", "environment", "default"]
    is_set: bool
    masked_value: Any = None
    updated_at: datetime | None = None
    updated_by: str | None = None


class VaultValuesListResponse(BaseModel):
    items: list[VaultValueResponse]
    total: int


class VaultUpsertRequest(BaseModel):
    value: Any
    reason: str | None = Field(default=None, max_length=500)


class VaultValidateRequest(BaseModel):
    value: Any


class VaultValidateResponse(BaseModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class VaultGenerateRequest(BaseModel):
    length: int | None = Field(default=None, ge=16, le=256)
    reason: str | None = Field(default=None, max_length=500)


class VaultGenerateResponse(BaseModel):
    key: str
    generated: bool
    masked_value: Any = None
    revealed_value: str | None = None


class VaultRotationRequestCreate(BaseModel):
    value: Any = None
    generate: bool = False
    length: int | None = Field(default=None, ge=16, le=256)
    reason: str | None = Field(default=None, max_length=500)


class VaultRotationDecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class VaultRotationRequestResponse(BaseModel):
    key: str
    status: Literal["pending", "approved", "rejected"]
    classification: ConfigClassification
    requested_by: str
    requested_at: datetime
    requested_reason: str | None = None
    masked_candidate: Any = None


class VaultRotationListResponse(BaseModel):
    items: list[VaultRotationRequestResponse]
    total: int
