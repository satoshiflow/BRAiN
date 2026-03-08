from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ModuleLifecycleResponse(BaseModel):
    id: UUID
    module_id: str
    owner_scope: str
    classification: str
    lifecycle_status: str
    canonical_path: str
    active_routes: list[str]
    data_owner: str
    auth_surface: str
    event_contract_status: str
    audit_policy: str
    migration_adapter: str | None = None
    kill_switch: str | None = None
    replacement_target: str | None = None
    sunset_phase: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ModuleLifecycleListResponse(BaseModel):
    items: list[ModuleLifecycleResponse] = Field(default_factory=list)
    total: int


class ModuleLifecycleTransitionRequest(BaseModel):
    replacement_target: str | None = Field(default=None, max_length=120)
    sunset_phase: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)
