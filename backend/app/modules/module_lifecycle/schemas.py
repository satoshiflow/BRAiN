from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field


class ModuleClassification(str, Enum):
    CORE = "CORE"
    CONSOLIDATE = "CONSOLIDATE"
    MIGRATE = "MIGRATE"
    FREEZE = "FREEZE"
    REPLACE = "REPLACE"
    NEW = "NEW"


class ModuleLifecycleStatus(str, Enum):
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ModuleLifecycleResponse(BaseModel):
    id: UUID
    module_id: str
    owner_scope: str
    classification: ModuleClassification
    lifecycle_status: ModuleLifecycleStatus
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


class ModuleDecommissionMatrix(BaseModel):
    module_id: str
    lifecycle_status: ModuleLifecycleStatus
    replacement_target: str | None = None
    migration_adapter: str | None = None
    kill_switch: str | None = None
    sunset_phase: str | None = None
    notes: str | None = None


class ModuleDecommissionLedgerEntry(BaseModel):
    module_id: str
    lifecycle_status: ModuleLifecycleStatus
    replacement_target: str | None = None
    kill_switch: str | None = None
    sunset_phase: str | None = None
    migration_adapter: str | None = None
    decommission_ready: bool
    blockers: list[str] = Field(default_factory=list)


class ModuleDecommissionLedgerResponse(BaseModel):
    items: list[ModuleDecommissionLedgerEntry] = Field(default_factory=list)
    total: int


class ModuleLifecycleTransitionRequest(BaseModel):
    replacement_target: str | None = Field(default=None, max_length=120)
    sunset_phase: str | None = Field(default=None, max_length=64)
    notes: str | None = Field(default=None, max_length=2000)
