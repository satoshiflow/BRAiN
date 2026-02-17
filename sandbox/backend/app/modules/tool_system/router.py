"""
Tool System - API Routes

FastAPI endpoints for the Tool Accumulation System.
Auto-discovered by BRAIN's router loader.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger

from .schemas import (
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolListResponse,
    ToolRegisterRequest,
    ToolSearchRequest,
    ToolStatus,
    ToolSystemInfo,
    ToolSystemStats,
    ToolUpdateRequest,
)
from .service import get_tool_system_service

router = APIRouter(prefix="/api/tools", tags=["tools"])


# ============================================================================
# Info & Stats
# ============================================================================


@router.get("/info", response_model=ToolSystemInfo)
async def tool_system_info():
    """Get tool system module information."""
    service = get_tool_system_service()
    return await service.get_info()


@router.get("/stats", response_model=ToolSystemStats)
async def tool_system_stats():
    """Get tool system statistics."""
    service = get_tool_system_service()
    return await service.get_stats()


# ============================================================================
# Tool CRUD
# ============================================================================


@router.post("/register", response_model=ToolDefinition, status_code=status.HTTP_201_CREATED)
async def register_tool(request: ToolRegisterRequest):
    """
    Register a new tool. Automatically validates it.

    On success the tool enters VALIDATED status.
    On validation failure it enters REJECTED status.
    """
    service = get_tool_system_service()
    tool = await service.register_tool(request)
    return tool


@router.get("/list", response_model=ToolListResponse)
async def list_tools(tool_status: Optional[ToolStatus] = Query(None, alias="status")):
    """List all tools, optionally filtered by status."""
    service = get_tool_system_service()
    return await service.list_tools(status=tool_status)


@router.get("/{tool_id}", response_model=ToolDefinition)
async def get_tool(tool_id: str):
    """Get a tool by ID."""
    service = get_tool_system_service()
    tool = await service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Tool '{tool_id}' not found")
    return tool


@router.put("/{tool_id}", response_model=ToolDefinition)
async def update_tool(tool_id: str, request: ToolUpdateRequest):
    """Update a tool's metadata."""
    service = get_tool_system_service()
    tool = await service.update_tool(tool_id, request)
    if not tool:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Tool '{tool_id}' not found")
    return tool


@router.delete("/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tool(tool_id: str):
    """Delete a tool."""
    service = get_tool_system_service()
    if not await service.delete_tool(tool_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Tool '{tool_id}' not found")


# ============================================================================
# Lifecycle
# ============================================================================


@router.post("/{tool_id}/activate", response_model=ToolDefinition)
async def activate_tool(tool_id: str):
    """
    Activate a validated tool, making it available for execution.

    Only tools in VALIDATED status can be activated.
    """
    service = get_tool_system_service()
    tool = await service.activate_tool(tool_id)
    if not tool:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot activate tool '{tool_id}' (not found or not in VALIDATED status)",
        )
    return tool


# ============================================================================
# Execution
# ============================================================================


@router.post("/execute", response_model=ToolExecutionResult)
async def execute_tool(request: ToolExecutionRequest):
    """
    Execute a tool within its security sandbox.

    The tool must be in ACTIVE status. Results are accumulated
    for learning (parameters, failures, timing).
    """
    service = get_tool_system_service()
    result = await service.execute_tool(request)
    if not result.success:
        logger.warning("Tool execution failed: %s - %s", request.tool_id, result.error)
    return result


# ============================================================================
# Search & Discovery
# ============================================================================


@router.post("/search", response_model=ToolListResponse)
async def search_tools(request: ToolSearchRequest):
    """
    Search tools by query, tags, capability, status, or minimum KARMA score.
    """
    service = get_tool_system_service()
    return await service.search_tools(request)


# ============================================================================
# Accumulation
# ============================================================================


@router.get("/{tool_id}/recommendations")
async def get_recommendations(tool_id: str):
    """
    Get usage recommendations based on accumulated knowledge.

    Returns learned defaults, failure patterns, and synergies.
    """
    service = get_tool_system_service()
    recs = await service.get_recommendations(tool_id)
    if "error" in recs:
        raise HTTPException(status.HTTP_404_NOT_FOUND, recs["error"])
    return recs


@router.post("/maintenance")
async def run_maintenance():
    """
    Run accumulation maintenance.

    Auto-suspends tools with very low retention scores,
    auto-deprecates idle tools, and reports warnings.
    """
    service = get_tool_system_service()
    return await service.run_maintenance()


@router.post("/cooccurrence")
async def record_cooccurrence(tool_ids: list[str]):
    """
    Record that multiple tools were used together.

    Used for synergy detection.
    """
    service = get_tool_system_service()
    await service.record_cooccurrence(tool_ids)
    return {"recorded": True, "tool_ids": tool_ids}
