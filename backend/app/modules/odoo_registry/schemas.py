"""
Odoo Module Registry Schemas

Models for module version tracking and storage.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Module Version Models
# ============================================================================


class ModuleVersion(BaseModel):
    """Represents a specific version of a module."""

    module_name: str = Field(..., description="Module technical name")
    version: str = Field(..., description="Version string (e.g., 1.0.0)")
    module_hash: str = Field(..., description="SHA256 hash of module content")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Version creation timestamp"
    )
    storage_path: str = Field(..., description="Path to stored module")
    file_count: int = Field(..., description="Number of files in module")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModuleReleaseRecord(BaseModel):
    """
    Release record for tracking deployed versions.

    Similar to WebGenesis release tracking pattern.
    """

    release_id: str = Field(..., description="Unique release identifier")
    module_name: str = Field(..., description="Module technical name")
    version: str = Field(..., description="Module version")
    module_hash: str = Field(..., description="SHA256 hash")
    installed_at: Optional[datetime] = Field(None, description="Installation timestamp")
    odoo_status: Optional[str] = Field(None, description="Odoo module state")
    is_current: bool = Field(False, description="Is currently deployed")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Release metadata"
    )


class ModuleRegistryInfo(BaseModel):
    """Information about a registered module."""

    module_name: str = Field(..., description="Module technical name")
    versions: List[ModuleVersion] = Field(..., description="All versions")
    current_version: Optional[str] = Field(None, description="Currently deployed version")
    latest_version: str = Field(..., description="Latest generated version")
    total_versions: int = Field(..., description="Total version count")
    created_at: datetime = Field(..., description="First version creation time")
    updated_at: datetime = Field(..., description="Last version creation time")


class RegistryListResponse(BaseModel):
    """Response for listing all registered modules."""

    modules: List[ModuleRegistryInfo] = Field(..., description="Registered modules")
    total_count: int = Field(..., description="Total number of modules")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict, description="Filters applied"
    )
