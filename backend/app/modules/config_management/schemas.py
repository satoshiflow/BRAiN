"""Config Management - Schemas"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
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
