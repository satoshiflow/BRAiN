"""Audit Logging - Schemas"""
from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

class AuditEventCreate(BaseModel):
    event_type: str = Field(...)
    action: str = Field(...)
    actor: str = Field(...)
    actor_type: str = Field(default="user")
    resource_type: Optional[str] = Field(default=None)
    resource_id: Optional[str] = Field(default=None)
    old_values: Optional[Dict[str, Any]] = Field(default=None)
    new_values: Optional[Dict[str, Any]] = Field(default=None)
    severity: str = Field(default="info")
    message: Optional[str] = Field(default=None)
    extra_data: Dict[str, Any] = Field(default_factory=dict)

class AuditEventResponse(BaseModel):
    id: UUID = Field(...)
    event_type: str = Field(...)
    action: str = Field(...)
    actor: str = Field(...)
    actor_type: str = Field(...)
    resource_type: Optional[str] = Field(default=None)
    resource_id: Optional[str] = Field(default=None)
    old_values: Optional[Dict[str, Any]] = Field(default=None)
    new_values: Optional[Dict[str, Any]] = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    severity: str = Field(...)
    message: Optional[str] = Field(default=None)
    extra_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(...)
    
    class Config:
        from_attributes = True

class AuditEventListResponse(BaseModel):
    items: List[AuditEventResponse] = Field(default_factory=list)
    total: int = Field(...)

class AuditStats(BaseModel):
    total_events: int = Field(...)
    by_type: Dict[str, int] = Field(default_factory=dict)
    by_action: Dict[str, int] = Field(default_factory=dict)
    by_severity: Dict[str, int] = Field(default_factory=dict)
