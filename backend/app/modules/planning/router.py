"""
Planning Module - API Routes

FastAPI endpoints for Advanced Planning Engine.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from .schemas import (
    DecompositionRequest,
    DecompositionResult,
    ExecutionPlan,
    PlanningInfo,
    PlanningStats,
    PlanStatus,
)
from .service import get_planning_service

router = APIRouter(prefix="/api/planning", tags=["planning"])


# ============================================================================
# Info & Stats
# ============================================================================


@router.get("/info", response_model=PlanningInfo)
async def planning_info():
    return PlanningInfo()


@router.get("/stats", response_model=PlanningStats)
async def planning_stats():
    return get_planning_service().get_stats()


# ============================================================================
# Plan Creation
# ============================================================================


@router.post("/decompose", response_model=DecompositionResult, status_code=status.HTTP_201_CREATED)
async def decompose_task(request: DecompositionRequest):
    """Decompose a task into an execution plan."""
    return get_planning_service().decompose_task(request)


@router.post("/plans", response_model=ExecutionPlan, status_code=status.HTTP_201_CREATED)
async def create_plan(plan: ExecutionPlan):
    """Create a plan from pre-built nodes."""
    return get_planning_service().create_plan(plan)


# ============================================================================
# Plan Queries
# ============================================================================


@router.get("/plans", response_model=List[ExecutionPlan])
async def list_plans(plan_status: Optional[PlanStatus] = Query(None)):
    return get_planning_service().list_plans(plan_status)


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    plan = get_planning_service().get_plan(plan_id)
    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan '{plan_id}' not found")
    return plan


# ============================================================================
# Plan Lifecycle
# ============================================================================


@router.post("/plans/{plan_id}/validate")
async def validate_plan(plan_id: str):
    """Validate plan's dependency graph."""
    errors = get_planning_service().validate_plan(plan_id)
    return {"valid": len(errors) == 0, "errors": errors}


@router.post("/plans/{plan_id}/start")
async def start_plan(plan_id: str):
    plan = get_planning_service().start_plan(plan_id)
    if not plan:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Plan not found or not in startable state")
    return plan


@router.get("/plans/{plan_id}/ready-nodes")
async def get_ready_nodes(plan_id: str):
    nodes = get_planning_service().get_ready_nodes(plan_id)
    return nodes


@router.post("/plans/{plan_id}/nodes/{node_id}/start")
async def start_node(plan_id: str, node_id: str):
    node = get_planning_service().start_node(plan_id, node_id)
    if not node:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan or node not found")
    return node


@router.post("/plans/{plan_id}/nodes/{node_id}/complete")
async def complete_node(plan_id: str, node_id: str, result: Dict):
    node = get_planning_service().complete_node(plan_id, node_id, result)
    if not node:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan or node not found")
    return node


@router.post("/plans/{plan_id}/nodes/{node_id}/fail")
async def fail_node(plan_id: str, node_id: str, error: str = Query(...)):
    svc = get_planning_service()
    action = await svc.fail_node(plan_id, node_id, error)
    if not action:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan or node not found")
    return {
        "recovery_strategy": action.strategy.value,
        "success": action.success,
        "message": action.message,
        "next_status": action.next_status.value,
        "retry_after_ms": action.retry_after_ms,
    }


# ============================================================================
# Analysis
# ============================================================================


@router.get("/plans/{plan_id}/critical-path")
async def critical_path(plan_id: str):
    result = get_planning_service().get_critical_path(plan_id)
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan '{plan_id}' not found")
    return result


@router.get("/plans/{plan_id}/parallel-groups")
async def parallel_groups(plan_id: str):
    groups = get_planning_service().get_parallel_groups(plan_id)
    if groups is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan '{plan_id}' not found")
    return {"groups": groups}


@router.get("/plans/{plan_id}/resources")
async def resource_utilization(plan_id: str):
    return get_planning_service().get_resource_utilization(plan_id)
