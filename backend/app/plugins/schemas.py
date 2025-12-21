"""
Plugin Schemas

API request/response models for plugin system.

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .base import PluginStatus, PluginType


# ============================================================================
# Request Models
# ============================================================================

class PluginLoadRequest(BaseModel):
    """Load plugin request."""

    plugin_id: str = Field(..., description="Plugin identifier")
    config: Dict[str, Any] = Field(default_factory=dict, description="Plugin configuration")


class PluginUploadRequest(BaseModel):
    """Upload plugin file request."""

    file_content: str = Field(..., description="Plugin file content (base64)")
    filename: str = Field(..., description="Plugin filename")
    config: Dict[str, Any] = Field(default_factory=dict, description="Plugin configuration")


class PluginEnableRequest(BaseModel):
    """Enable plugin request."""

    plugin_id: str = Field(..., description="Plugin identifier")


class PluginDisableRequest(BaseModel):
    """Disable plugin request."""

    plugin_id: str = Field(..., description="Plugin identifier")


class PluginUnloadRequest(BaseModel):
    """Unload plugin request."""

    plugin_id: str = Field(..., description="Plugin identifier")


class PluginConfigUpdateRequest(BaseModel):
    """Update plugin configuration request."""

    plugin_id: str = Field(..., description="Plugin identifier")
    config: Dict[str, Any] = Field(..., description="New configuration")


# ============================================================================
# Response Models
# ============================================================================

class PluginMetadataResponse(BaseModel):
    """Plugin metadata response."""

    id: str = Field(..., description="Plugin identifier")
    name: str = Field(..., description="Plugin name")
    version: str = Field(..., description="Plugin version")
    description: str = Field(..., description="Plugin description")
    author: str = Field(..., description="Plugin author")
    plugin_type: PluginType = Field(..., description="Plugin type")
    status: PluginStatus = Field(..., description="Current status")
    dependencies: List[str] = Field(default_factory=list, description="Plugin dependencies")
    config_schema: Optional[Dict[str, Any]] = Field(None, description="Configuration schema")
    error: Optional[str] = Field(None, description="Error message if in error state")


class PluginListResponse(BaseModel):
    """Plugin list response."""

    plugins: List[PluginMetadataResponse] = Field(..., description="List of plugins")
    total: int = Field(..., description="Total plugin count")


class PluginOperationResponse(BaseModel):
    """Plugin operation response."""

    success: bool = Field(..., description="Operation success")
    message: str = Field(..., description="Result message")
    plugin_id: Optional[str] = Field(None, description="Plugin identifier")


class PluginStatsResponse(BaseModel):
    """Plugin statistics response."""

    total: int = Field(..., description="Total plugins")
    by_status: Dict[str, int] = Field(..., description="Plugins by status")
    by_type: Dict[str, int] = Field(..., description="Plugins by type")


class PluginInfoResponse(BaseModel):
    """Plugin system information response."""

    name: str = Field(..., description="Plugin system name")
    version: str = Field(..., description="Plugin system version")
    plugin_types: List[str] = Field(..., description="Supported plugin types")
    total_plugins: int = Field(..., description="Total registered plugins")
    enabled_plugins: int = Field(..., description="Enabled plugins")


class PluginHookResponse(BaseModel):
    """Plugin hook information response."""

    name: str = Field(..., description="Hook name")
    callback_count: int = Field(..., description="Number of registered callbacks")


class PluginHooksResponse(BaseModel):
    """All plugin hooks response."""

    hooks: List[PluginHookResponse] = Field(..., description="List of hooks")
    total: int = Field(..., description="Total hook count")


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Request models
    "PluginLoadRequest",
    "PluginUploadRequest",
    "PluginEnableRequest",
    "PluginDisableRequest",
    "PluginUnloadRequest",
    "PluginConfigUpdateRequest",
    # Response models
    "PluginMetadataResponse",
    "PluginListResponse",
    "PluginOperationResponse",
    "PluginStatsResponse",
    "PluginInfoResponse",
    "PluginHookResponse",
    "PluginHooksResponse",
]
