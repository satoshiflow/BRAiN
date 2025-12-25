"""
Odoo Connector API Routes

Basic endpoints for testing Odoo connectivity.
Sprint IV: AXE × Odoo Integration - Phase 1
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.app.modules.odoo_connector import (
    OdooModuleInfo,
    OdooModuleListResponse,
    OdooModuleState,
    OdooStatusResponse,
    get_odoo_service,
)

router = APIRouter(prefix="/api/odoo", tags=["odoo-connector"])


@router.get("/status", response_model=OdooStatusResponse)
async def get_odoo_status():
    """
    Test Odoo connection and get server status.

    Returns:
        OdooStatusResponse with connection details
    """
    try:
        service = get_odoo_service()
        status = await service.test_connection()
        return status

    except Exception as e:
        logger.error(f"Failed to check Odoo status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check Odoo status: {str(e)}",
        )


@router.get("/modules", response_model=OdooModuleListResponse)
async def list_odoo_modules(
    state: Optional[OdooModuleState] = Query(
        None, description="Filter by module state"
    ),
    name: Optional[str] = Query(None, description="Filter by module name (partial)"),
):
    """
    List Odoo modules with optional filters.

    Args:
        state: Filter by module state (installed, uninstalled, etc.)
        name: Filter by module name (partial match)

    Returns:
        OdooModuleListResponse with modules list
    """
    try:
        service = get_odoo_service()
        modules = await service.list_modules(state=state, name_filter=name)

        # Build filters dict
        filters = {}
        if state:
            filters["state"] = state.value
        if name:
            filters["name"] = name

        return OdooModuleListResponse(
            modules=modules,
            total_count=len(modules),
            filters_applied=filters,
        )

    except Exception as e:
        logger.error(f"Failed to list Odoo modules: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list modules: {str(e)}",
        )


@router.get("/modules/{module_name}", response_model=OdooModuleInfo)
async def get_odoo_module_info(module_name: str):
    """
    Get detailed information about a specific Odoo module.

    Args:
        module_name: Technical module name

    Returns:
        OdooModuleInfo with module details

    Raises:
        HTTPException: 404 if module not found
    """
    try:
        service = get_odoo_service()
        module_info = await service.get_module_info(module_name)

        if not module_info:
            raise HTTPException(
                status_code=404,
                detail=f"Module '{module_name}' not found in Odoo",
            )

        return module_info

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Failed to get module info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get module info: {str(e)}",
        )
