"""
Odoo Connector Schemas

DTOs for Odoo integration operations.
Sprint IV: AXE × Odoo Integration
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class OdooModuleState(str, Enum):
    """Odoo module installation state."""

    UNINSTALLED = "uninstalled"
    INSTALLED = "installed"
    TO_INSTALL = "to install"
    TO_UPGRADE = "to upgrade"
    TO_REMOVE = "to remove"
    UNKNOWN = "unknown"


class OdooConnectionStatus(str, Enum):
    """Connection status to Odoo instance."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


# ============================================================================
# Connection Models
# ============================================================================


class OdooConnectionInfo(BaseModel):
    """Odoo connection configuration."""

    base_url: str = Field(..., description="Odoo base URL (e.g., http://localhost:8069)")
    database: str = Field(..., description="Odoo database name")
    username: str = Field(..., description="Admin username")
    password: str = Field(..., description="Admin password (not logged)")

    class Config:
        json_schema_extra = {
            "example": {
                "base_url": "http://localhost:8069",
                "database": "production",
                "username": "admin",
                "password": "***",
            }
        }


class OdooStatusResponse(BaseModel):
    """Odoo instance status."""

    connected: bool = Field(..., description="Connection successful")
    status: OdooConnectionStatus = Field(..., description="Connection status")
    odoo_version: Optional[str] = Field(None, description="Odoo version (e.g., 19.0)")
    server_version: Optional[str] = Field(None, description="Full server version string")
    database: Optional[str] = Field(None, description="Database name")
    protocol_version: Optional[int] = Field(None, description="XML-RPC protocol version")
    uid: Optional[int] = Field(None, description="User ID (if authenticated)")
    error: Optional[str] = Field(None, description="Error message if connection failed")

    class Config:
        json_schema_extra = {
            "example": {
                "connected": True,
                "status": "connected",
                "odoo_version": "19.0",
                "server_version": "19.0-20251201",
                "database": "production",
                "protocol_version": 2,
                "uid": 2,
                "error": None,
            }
        }


# ============================================================================
# Module Models
# ============================================================================


class OdooModuleInfo(BaseModel):
    """Information about an Odoo module."""

    name: str = Field(..., description="Technical module name")
    display_name: Optional[str] = Field(None, description="Human-readable name")
    state: OdooModuleState = Field(..., description="Installation state")
    version: Optional[str] = Field(None, description="Module version")
    summary: Optional[str] = Field(None, description="Short description")
    author: Optional[str] = Field(None, description="Module author")
    website: Optional[str] = Field(None, description="Module website")
    depends: List[str] = Field(default_factory=list, description="Dependencies")
    installed_version: Optional[str] = Field(None, description="Currently installed version")
    latest_version: Optional[str] = Field(None, description="Latest available version")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "my_custom_crm",
                "display_name": "My Custom CRM",
                "state": "installed",
                "version": "1.0.0",
                "summary": "Custom CRM extension",
                "author": "BRAiN AXE Generator",
                "website": "https://brain.example.com",
                "depends": ["base", "crm"],
                "installed_version": "1.0.0",
                "latest_version": "1.0.0",
            }
        }


class OdooModuleListResponse(BaseModel):
    """Response for listing Odoo modules."""

    modules: List[OdooModuleInfo] = Field(..., description="List of modules")
    total_count: int = Field(..., description="Total number of modules")
    filters_applied: Dict[str, Any] = Field(
        default_factory=dict, description="Filters applied to query"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "modules": [
                    {
                        "name": "my_custom_crm",
                        "display_name": "My Custom CRM",
                        "state": "installed",
                        "version": "1.0.0",
                    }
                ],
                "total_count": 1,
                "filters_applied": {"state": "installed"},
            }
        }


# ============================================================================
# Operation Models
# ============================================================================


class OdooModuleInstallRequest(BaseModel):
    """Request to install an Odoo module."""

    module_name: str = Field(..., description="Technical module name")
    force: bool = Field(False, description="Force reinstall if already installed")


class OdooModuleUpgradeRequest(BaseModel):
    """Request to upgrade an Odoo module."""

    module_name: str = Field(..., description="Technical module name")


class OdooModuleUninstallRequest(BaseModel):
    """Request to uninstall an Odoo module."""

    module_name: str = Field(..., description="Technical module name")
    remove_dependencies: bool = Field(
        False, description="Also uninstall dependent modules"
    )


class OdooOperationResult(BaseModel):
    """Result of an Odoo operation (install/upgrade/uninstall)."""

    success: bool = Field(..., description="Operation succeeded")
    module_name: str = Field(..., description="Module name")
    operation: str = Field(..., description="Operation type (install/upgrade/uninstall)")
    message: str = Field(..., description="Human-readable result message")
    previous_state: Optional[OdooModuleState] = Field(
        None, description="State before operation"
    )
    new_state: Optional[OdooModuleState] = Field(None, description="State after operation")
    error: Optional[str] = Field(None, description="Error message if failed")
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional operation metadata"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "module_name": "my_custom_crm",
                "operation": "install",
                "message": "Module 'my_custom_crm' installed successfully",
                "previous_state": "uninstalled",
                "new_state": "installed",
                "error": None,
                "warnings": [],
                "metadata": {"duration_seconds": 12.5},
            }
        }
