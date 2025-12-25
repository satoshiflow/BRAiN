"""
Odoo Orchestrator Schemas

DTOs for orchestration operations.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Operation Status
# ============================================================================


class OdooOrchestrationStatus(str, Enum):
    """Orchestration operation status."""

    PENDING = "pending"
    GENERATING = "generating"
    STORING = "storing"
    COPYING = "copying"
    INSTALLING = "installing"
    UPGRADING = "upgrading"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Request Models
# ============================================================================


class ModuleGenerateRequest(BaseModel):
    """Request to generate Odoo module from text spec."""

    spec_text: str = Field(..., description="Module specification (text format)")
    auto_install: bool = Field(
        False, description="Automatically install after generation"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModuleInstallRequest(BaseModel):
    """Request to install a previously generated module."""

    module_name: str = Field(..., description="Module technical name")
    version: str = Field(..., description="Version to install")
    force: bool = Field(False, description="Force reinstall if already installed")


class ModuleUpgradeRequest(BaseModel):
    """Request to upgrade an installed module."""

    module_name: str = Field(..., description="Module technical name")
    spec_text: Optional[str] = Field(
        None, description="New spec (if None, upgrade existing version)"
    )
    new_version: Optional[str] = Field(None, description="New version number")


class ModuleRollbackRequest(BaseModel):
    """Request to rollback to previous module version."""

    module_name: str = Field(..., description="Module technical name")
    target_version: Optional[str] = Field(
        None, description="Target version (if None, rollback to previous)"
    )


# ============================================================================
# Response Models
# ============================================================================


class OdooOrchestrationResult(BaseModel):
    """Result of orchestration operation."""

    success: bool = Field(..., description="Operation succeeded")
    status: OdooOrchestrationStatus = Field(..., description="Operation status")
    module_name: str = Field(..., description="Module name")
    version: str = Field(..., description="Module version")
    operation: str = Field(..., description="Operation type")

    # Generation details
    generation_success: bool = Field(False, description="Generation succeeded")
    module_hash: Optional[str] = Field(None, description="Module SHA256 hash")
    file_count: int = Field(0, description="Number of generated files")

    # Installation details
    installation_success: bool = Field(False, description="Installation succeeded")
    odoo_status: Optional[str] = Field(None, description="Odoo module status")
    release_id: Optional[str] = Field(None, description="Release ID (if installed)")

    # Messages
    message: str = Field(..., description="Human-readable result message")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    errors: List[str] = Field(default_factory=list, description="Error messages")

    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "status": "completed",
                "module_name": "my_custom_crm",
                "version": "1.0.0",
                "operation": "generate_and_install",
                "generation_success": True,
                "module_hash": "abc123...",
                "file_count": 7,
                "installation_success": True,
                "odoo_status": "installed",
                "release_id": "odoo_my_custom_crm_1.0.0_a1b2c3d4",
                "message": "Module successfully generated and installed",
                "warnings": [],
                "errors": [],
            }
        }
