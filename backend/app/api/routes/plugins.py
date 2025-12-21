"""
Plugin API Routes

REST API endpoints for plugin management.

Endpoints:
    GET /api/plugins             - List all plugins
    GET /api/plugins/{id}        - Get plugin details
    POST /api/plugins/load       - Load plugin
    POST /api/plugins/enable     - Enable plugin
    POST /api/plugins/disable    - Disable plugin
    POST /api/plugins/unload     - Unload plugin
    GET /api/plugins/stats       - Get plugin statistics
    GET /api/plugins/hooks       - List plugin hooks
    GET /api/plugins/info        - Get plugin system info

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.core.security import Principal, require_admin
from backend.app.plugins.base import PluginStatus, PluginType
from backend.app.plugins.manager import get_plugin_manager
from backend.app.plugins.schemas import (
    PluginDisableRequest,
    PluginEnableRequest,
    PluginHookResponse,
    PluginHooksResponse,
    PluginInfoResponse,
    PluginListResponse,
    PluginLoadRequest,
    PluginMetadataResponse,
    PluginOperationResponse,
    PluginStatsResponse,
    PluginUnloadRequest,
)

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


# ============================================================================
# Helper Functions
# ============================================================================

def plugin_to_response(plugin) -> PluginMetadataResponse:
    """Convert plugin instance to response model."""
    metadata = plugin.get_metadata()

    return PluginMetadataResponse(
        id=metadata.id,
        name=metadata.name,
        version=metadata.version,
        description=metadata.description,
        author=metadata.author,
        plugin_type=metadata.plugin_type,
        status=plugin.get_status(),
        dependencies=metadata.dependencies,
        config_schema=metadata.config_schema,
        error=plugin.get_error(),
    )


# ============================================================================
# Plugin List & Details
# ============================================================================

@router.get("", response_model=PluginListResponse)
async def list_plugins(
    plugin_type: Optional[PluginType] = Query(None, description="Filter by plugin type"),
    status_filter: Optional[PluginStatus] = Query(None, description="Filter by status"),
    principal: Principal = Depends(require_admin),
) -> PluginListResponse:
    """
    List all registered plugins.

    **Permissions:** Admin only

    **Query Parameters:**
    - plugin_type: Filter by plugin type
    - status_filter: Filter by status

    **Returns:**
    - List of plugins with metadata and status
    """
    manager = get_plugin_manager()

    plugins = manager.list_plugins(plugin_type=plugin_type, status=status_filter)

    plugin_responses = [plugin_to_response(p) for p in plugins]

    return PluginListResponse(
        plugins=plugin_responses,
        total=len(plugin_responses),
    )


@router.get("/{plugin_id}", response_model=PluginMetadataResponse)
async def get_plugin(
    plugin_id: str,
    principal: Principal = Depends(require_admin),
) -> PluginMetadataResponse:
    """
    Get plugin details by ID.

    **Permissions:** Admin only

    **Parameters:**
    - plugin_id: Plugin identifier

    **Returns:**
    - Plugin metadata and status
    """
    manager = get_plugin_manager()

    plugin = manager.get_plugin(plugin_id)

    if not plugin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plugin not found: {plugin_id}",
        )

    return plugin_to_response(plugin)


# ============================================================================
# Plugin Lifecycle Operations
# ============================================================================

@router.post("/load", status_code=status.HTTP_201_CREATED)
async def load_plugin(
    request: PluginLoadRequest,
    principal: Principal = Depends(require_admin),
) -> PluginOperationResponse:
    """
    Load plugin by ID.

    **Permissions:** Admin only

    **Request Body:**
    - plugin_id: Plugin identifier
    - config: Plugin configuration (optional)

    **Returns:**
    - Operation result

    **Example:**
    ```json
    {
        "plugin_id": "my_custom_agent",
        "config": {
            "api_key": "xxx",
            "timeout": 30
        }
    }
    ```
    """
    manager = get_plugin_manager()

    try:
        success = await manager.load_plugin(request.plugin_id, request.config)

        if not success:
            return PluginOperationResponse(
                success=False,
                message=f"Failed to load plugin: {request.plugin_id}",
                plugin_id=request.plugin_id,
            )

        return PluginOperationResponse(
            success=True,
            message=f"Plugin loaded successfully: {request.plugin_id}",
            plugin_id=request.plugin_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load plugin: {str(e)}",
        )


@router.post("/enable", status_code=status.HTTP_200_OK)
async def enable_plugin(
    request: PluginEnableRequest,
    principal: Principal = Depends(require_admin),
) -> PluginOperationResponse:
    """
    Enable plugin.

    **Permissions:** Admin only

    **Request Body:**
    - plugin_id: Plugin identifier

    **Returns:**
    - Operation result
    """
    manager = get_plugin_manager()

    try:
        success = await manager.enable_plugin(request.plugin_id)

        if not success:
            return PluginOperationResponse(
                success=False,
                message=f"Failed to enable plugin: {request.plugin_id}",
                plugin_id=request.plugin_id,
            )

        return PluginOperationResponse(
            success=True,
            message=f"Plugin enabled successfully: {request.plugin_id}",
            plugin_id=request.plugin_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable plugin: {str(e)}",
        )


@router.post("/disable", status_code=status.HTTP_200_OK)
async def disable_plugin(
    request: PluginDisableRequest,
    principal: Principal = Depends(require_admin),
) -> PluginOperationResponse:
    """
    Disable plugin.

    **Permissions:** Admin only

    **Request Body:**
    - plugin_id: Plugin identifier

    **Returns:**
    - Operation result
    """
    manager = get_plugin_manager()

    try:
        success = await manager.disable_plugin(request.plugin_id)

        if not success:
            return PluginOperationResponse(
                success=False,
                message=f"Failed to disable plugin: {request.plugin_id}",
                plugin_id=request.plugin_id,
            )

        return PluginOperationResponse(
            success=True,
            message=f"Plugin disabled successfully: {request.plugin_id}",
            plugin_id=request.plugin_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable plugin: {str(e)}",
        )


@router.post("/unload", status_code=status.HTTP_200_OK)
async def unload_plugin(
    request: PluginUnloadRequest,
    principal: Principal = Depends(require_admin),
) -> PluginOperationResponse:
    """
    Unload plugin.

    **Permissions:** Admin only

    **Request Body:**
    - plugin_id: Plugin identifier

    **Returns:**
    - Operation result

    **Warning:** Unloading removes the plugin from memory. You'll need to reload it to use again.
    """
    manager = get_plugin_manager()

    try:
        success = await manager.unload_plugin(request.plugin_id)

        if not success:
            return PluginOperationResponse(
                success=False,
                message=f"Failed to unload plugin: {request.plugin_id}",
                plugin_id=request.plugin_id,
            )

        return PluginOperationResponse(
            success=True,
            message=f"Plugin unloaded successfully: {request.plugin_id}",
            plugin_id=request.plugin_id,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unload plugin: {str(e)}",
        )


# ============================================================================
# Plugin Statistics
# ============================================================================

@router.get("/stats", response_model=PluginStatsResponse)
async def get_plugin_stats(
    principal: Principal = Depends(require_admin),
) -> PluginStatsResponse:
    """
    Get plugin system statistics.

    **Permissions:** Admin only

    **Returns:**
    - Total plugins
    - Plugins by status
    - Plugins by type
    """
    manager = get_plugin_manager()

    stats = manager.registry.get_stats()

    return PluginStatsResponse(
        total=stats["total"],
        by_status=stats["by_status"],
        by_type=stats["by_type"],
    )


# ============================================================================
# Plugin Hooks
# ============================================================================

@router.get("/hooks", response_model=PluginHooksResponse)
async def list_hooks(
    principal: Principal = Depends(require_admin),
) -> PluginHooksResponse:
    """
    List all plugin hooks.

    **Permissions:** Admin only

    **Returns:**
    - List of hooks with callback counts
    """
    manager = get_plugin_manager()

    hook_responses = []

    for name, hook in manager.hooks.items():
        hook_responses.append(
            PluginHookResponse(
                name=name,
                callback_count=len(hook.callbacks),
            )
        )

    return PluginHooksResponse(
        hooks=hook_responses,
        total=len(hook_responses),
    )


# ============================================================================
# Plugin System Info
# ============================================================================

@router.get("/info", response_model=PluginInfoResponse)
async def get_plugin_info() -> PluginInfoResponse:
    """
    Get plugin system information.

    **Returns:**
    - Plugin system metadata
    - Supported plugin types
    - Current statistics
    """
    manager = get_plugin_manager()

    # Get enabled plugin count
    enabled_plugins = len(manager.list_plugins(status=PluginStatus.ENABLED))

    # Get total plugin count
    total_plugins = manager.registry.count()

    # Get supported plugin types
    plugin_types = [pt.value for pt in PluginType]

    return PluginInfoResponse(
        name="BRAiN Plugin System",
        version="1.0.0",
        plugin_types=plugin_types,
        total_plugins=total_plugins,
        enabled_plugins=enabled_plugins,
    )


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
