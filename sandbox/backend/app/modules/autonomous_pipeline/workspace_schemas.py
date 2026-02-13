"""
Workspace & Multi-Tenancy Schemas (Sprint 9-C)

Data isolation and tenant separation without product UI.
Prepare BRAiN for multiple customers/organizations.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class WorkspaceStatus(str, Enum):
    """Workspace lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class ProjectStatus(str, Enum):
    """Project lifecycle status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Workspace(BaseModel):
    """
    Tenant/Organization workspace.

    Provides hard isolation for:
    - Secrets & API keys
    - Evidence packs
    - Run contracts
    - Projects
    """

    # Identity
    workspace_id: str = Field(..., description="Unique workspace ID (UUIDv7)")
    name: str = Field(..., description="Workspace name", min_length=1, max_length=100)
    slug: str = Field(..., description="URL-safe identifier", pattern=r"^[a-z0-9-]+$")

    # Metadata
    description: Optional[str] = Field(None, description="Workspace description")
    status: WorkspaceStatus = Field(default=WorkspaceStatus.ACTIVE)

    # Ownership
    owner_id: Optional[str] = Field(None, description="Owner user/org ID")
    created_by: Optional[str] = Field(None, description="Creator user ID")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Isolation paths (storage)
    storage_path: Optional[str] = Field(
        None,
        description="Isolated storage path for this workspace"
    )

    # Limits & Quotas
    max_projects: int = Field(default=100, ge=1, le=10000)
    max_runs_per_day: int = Field(default=1000, ge=1, le=100000)
    max_storage_gb: float = Field(default=100.0, ge=0.1, le=10000.0)

    # Settings
    settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Workspace-specific settings"
    )

    # Tags
    tags: List[str] = Field(default_factory=list, description="Workspace tags")

    class Config:
        json_schema_extra = {
            "example": {
                "workspace_id": "ws_01j12k34m56n78p90qrs",
                "name": "Acme Corp",
                "slug": "acme-corp",
                "description": "Production workspace for Acme Corporation",
                "status": "active",
                "owner_id": "user_abc123",
                "max_projects": 50,
                "max_runs_per_day": 500,
                "max_storage_gb": 50.0,
            }
        }


class Project(BaseModel):
    """
    Project within a workspace.

    Groups related pipeline runs and resources.
    """

    # Identity
    project_id: str = Field(..., description="Unique project ID (UUIDv7)")
    workspace_id: str = Field(..., description="Parent workspace ID")
    name: str = Field(..., description="Project name", min_length=1, max_length=100)
    slug: str = Field(..., description="URL-safe identifier", pattern=r"^[a-z0-9-]+$")

    # Metadata
    description: Optional[str] = Field(None, description="Project description")
    status: ProjectStatus = Field(default=ProjectStatus.ACTIVE)

    # Ownership
    created_by: Optional[str] = Field(None, description="Creator user ID")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Project settings
    default_budget: Optional[Dict[str, Any]] = Field(
        None,
        description="Default execution budget for runs"
    )
    default_policy: Optional[Dict[str, Any]] = Field(
        None,
        description="Default execution policy for runs"
    )

    # Statistics
    total_runs: int = Field(default=0, ge=0)
    successful_runs: int = Field(default=0, ge=0)
    failed_runs: int = Field(default=0, ge=0)

    # Tags
    tags: List[str] = Field(default_factory=list, description="Project tags")

    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj_01j12k34m56n78p90qrs",
                "workspace_id": "ws_01j12k34m56n78p90qrs",
                "name": "E-Commerce Platform",
                "slug": "ecommerce-platform",
                "description": "Main e-commerce business automation project",
                "status": "active",
                "total_runs": 42,
                "successful_runs": 38,
                "failed_runs": 4,
            }
        }


class WorkspaceCreateRequest(BaseModel):
    """Request to create a new workspace."""

    name: str = Field(..., description="Workspace name", min_length=1, max_length=100)
    slug: str = Field(..., description="URL-safe identifier", pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    owner_id: Optional[str] = None
    max_projects: int = Field(default=100, ge=1, le=10000)
    max_runs_per_day: int = Field(default=1000, ge=1, le=100000)
    max_storage_gb: float = Field(default=100.0, ge=0.1, le=10000.0)
    settings: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class WorkspaceUpdateRequest(BaseModel):
    """Request to update workspace."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[WorkspaceStatus] = None
    max_projects: Optional[int] = Field(None, ge=1, le=10000)
    max_runs_per_day: Optional[int] = Field(None, ge=1, le=100000)
    max_storage_gb: Optional[float] = Field(None, ge=0.1, le=10000.0)
    settings: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class ProjectCreateRequest(BaseModel):
    """Request to create a new project."""

    name: str = Field(..., description="Project name", min_length=1, max_length=100)
    slug: str = Field(..., description="URL-safe identifier", pattern=r"^[a-z0-9-]+$")
    description: Optional[str] = None
    default_budget: Optional[Dict[str, Any]] = None
    default_policy: Optional[Dict[str, Any]] = None
    tags: List[str] = Field(default_factory=list)


class ProjectUpdateRequest(BaseModel):
    """Request to update project."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    default_budget: Optional[Dict[str, Any]] = None
    default_policy: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class WorkspaceStats(BaseModel):
    """Workspace statistics."""

    workspace_id: str
    total_projects: int = Field(default=0, ge=0)
    active_projects: int = Field(default=0, ge=0)
    total_runs: int = Field(default=0, ge=0)
    runs_today: int = Field(default=0, ge=0)
    storage_used_gb: float = Field(default=0.0, ge=0.0)
    storage_limit_gb: float = Field(default=100.0, ge=0.0)
    quota_usage_percent: float = Field(default=0.0, ge=0.0, le=100.0)


class ProjectStats(BaseModel):
    """Project statistics."""

    project_id: str
    workspace_id: str
    total_runs: int = Field(default=0, ge=0)
    successful_runs: int = Field(default=0, ge=0)
    failed_runs: int = Field(default=0, ge=0)
    success_rate_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    avg_duration_seconds: float = Field(default=0.0, ge=0.0)
    last_run_at: Optional[datetime] = None
