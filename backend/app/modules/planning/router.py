"""
Planning Module - API Routes

FastAPI endpoints for Advanced Planning Engine.
"""

from typing import Dict, List, Optional
import time

from fastapi import APIRouter, HTTPException, Query, status, Depends
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import require_auth, require_role, Principal, SystemRole as UserRole
from app.core.database import get_db

from .schemas import (
    DecompositionRequest,
    DecompositionResult,
    ExecuteNextResponse,
    ExecutionPlan,
    PlanningInfo,
    PlanningStats,
    PlanStatus,
)
from .service import get_planning_service
from app.modules.memory.service import get_memory_service
from app.modules.memory.schemas import MemoryLayer, MemoryStoreRequest, MemoryType
from app.modules.learning.service import get_learning_service
from app.modules.learning.schemas import MetricEntry, MetricType

# EventStream integration (non-blocking)
try:
    from mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
    global _event_stream
    _event_stream = stream


async def _emit_planning_event_safe(event_type: str, payload: dict) -> None:
    if _event_stream is None or Event is None:
        return
    try:
        event = Event(type=event_type, source="planning_service", target=None, payload=payload)
        await _event_stream.publish(event)
    except Exception as exc:
        logger.error("[Planning] event publish failed: %s", exc)


async def _persist_execution_feedback(
    *,
    plan: ExecutionPlan,
    node_id: str,
    db: AsyncSession,
) -> None:
    """Store execution outcomes into memory + learning (best-effort)."""
    node = next((n for n in plan.nodes if n.node_id == node_id), None)
    if not node:
        return

    agent_id = plan.agent_id or node.agent_id or "planning-system"
    duration_ms = float(node.duration_ms or 0.0)

    # Memory loop closure (episodic mission outcome)
    try:
        memory_service = get_memory_service()
        await memory_service.store_memory(
            MemoryStoreRequest(
                content=f"Plan node executed: {node.name}",
                memory_type=MemoryType.MISSION_OUTCOME,
                layer=MemoryLayer.EPISODIC,
                agent_id=agent_id,
                mission_id=plan.mission_id,
                importance=65.0,
                tags=["planning", "execution", node.action or "unknown"],
                metadata={
                    "plan_id": plan.plan_id,
                    "node_id": node.node_id,
                    "status": node.status.value,
                    "duration_ms": duration_ms,
                },
            )
        )
    except Exception as exc:
        logger.error("[Planning] memory feedback failed: %s", exc)

    # Learning loop closure (latency metric)
    try:
        learning_service = get_learning_service()
        await learning_service.record_metric(
            db,
            MetricEntry(
                agent_id=agent_id,
                metric_type=MetricType.LATENCY,
                value=duration_ms,
                unit="ms",
                tags={"source": "planning", "node_action": node.action or "unknown"},
                context={"plan_id": plan.plan_id, "node_id": node.node_id},
            ),
        )
    except Exception as exc:
        logger.error("[Planning] learning feedback failed: %s", exc)

router = APIRouter(
    prefix="/api/planning",
    tags=["planning"],
    dependencies=[Depends(require_auth)]
)


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

    plan = get_planning_service().get_plan(plan_id)
    if plan:
        await _emit_planning_event_safe(
            "planning.node.completed",
            {
                "plan_id": plan_id,
                "node_id": node_id,
                "status": node.status.value,
                "plan_status": plan.status.value,
            },
        )
    return node


@router.post("/plans/{plan_id}/execute-next", response_model=ExecuteNextResponse)
async def execute_next(
    plan_id: str,
    feedback: bool = Query(True, description="Persist memory + learning feedback"),
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
    db: AsyncSession = Depends(get_db),
):
    """Execute exactly one ready node and optionally persist feedback."""
    svc = get_planning_service()
    node = svc.execute_next_node(plan_id)
    plan = svc.get_plan(plan_id)

    if not plan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Plan '{plan_id}' not found")

    if not node:
        raise HTTPException(status.HTTP_409_CONFLICT, "No ready nodes available for execution")

    if feedback:
        await _persist_execution_feedback(plan=plan, node_id=node.node_id, db=db)

    ready_nodes = svc.get_ready_nodes(plan_id)

    await _emit_planning_event_safe(
        "planning.node.executed",
        {
            "plan_id": plan_id,
            "node_id": node.node_id,
            "principal_id": principal.principal_id,
            "plan_status": plan.status.value,
            "ready_nodes_after": len(ready_nodes),
            "feedback": feedback,
            "timestamp": time.time(),
        },
    )

    return ExecuteNextResponse(
        plan_id=plan_id,
        executed_node_id=node.node_id,
        executed_node_status=node.status,
        plan_status=plan.status,
        completed_nodes=plan.completed_nodes,
        total_nodes=plan.total_nodes,
        next_ready_node_ids=[n.node_id for n in ready_nodes],
    )


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
