"""
Task Queue System - API Router

FastAPI endpoints for task queue management.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import require_role, get_current_principal, Principal, require_auth, SystemRole as UserRole
from app.core.rate_limit import limiter, RateLimits
from app.modules.skill_engine.service import get_skill_engine_service
from app.modules.module_lifecycle.service import get_module_lifecycle_service

from .schemas import (
    TaskCreate, TaskUpdate, TaskClaim, TaskComplete, TaskFail,
    TaskResponse, TaskListResponse, TaskStats, QueueStats, TaskStatus,
    TaskClaimResponse, TaskLeaseCreateResponse
)
from .service import get_task_queue_service, TaskQueueService
from .models import TaskModel, TaskStatus as TaskModelStatus


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def task_to_response(task: TaskModel) -> TaskResponse:
    """Convert TaskModel to TaskResponse"""
    return TaskResponse.model_validate(task)


def _to_model_status(status: Optional[TaskStatus]) -> Optional[TaskModelStatus]:
    if status is None:
        return None
    return TaskModelStatus(status.value)


async def _ensure_task_queue_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "task_queue")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"task_queue is {item.lifecycle_status}; writes are blocked",
        )


# ============================================================================
# Task CRUD
# ============================================================================

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SERVICE)),
):
    """
    Create a new task in the queue.
    
    Tasks can be scheduled for immediate or future execution.
    """
    service = get_task_queue_service()
    await _ensure_task_queue_writable(db)

    try:
        task = await service.create_task(
            db=db,
            task_data=task_data,
            created_by=principal.principal_id,
            created_by_type=principal.principal_type
        )
        return task_to_response(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.post("/skill-runs/{run_id}/lease", response_model=TaskLeaseCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_skill_run_lease(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SERVICE)),
):
    await _ensure_task_queue_writable(db)
    run = await get_skill_engine_service().get_run(db, run_id, principal.tenant_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Skill run {run_id} not found",
        )

    try:
        task = await get_task_queue_service().create_task_lease_for_skill_run(db, run, principal)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    return TaskLeaseCreateResponse(skill_run_id=run.id, task=task_to_response(task))


@router.get("", response_model=TaskListResponse, dependencies=[Depends(require_auth)])
async def list_tasks(
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    task_type: Optional[str] = Query(None, description="Filter by task type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """List tasks with optional filtering"""
    service = get_task_queue_service()
    tasks = await service.get_tasks(
        db,
        status=_to_model_status(status),
        task_type=task_type,
        limit=limit,
        offset=offset,
    )
    
    # Count by status
    by_status = {}
    for task in tasks:
        s = task.status.value if hasattr(task.status, 'value') else str(task.status)
        by_status[s] = by_status.get(s, 0) + 1
    
    return TaskListResponse(
        items=[task_to_response(t) for t in tasks],
        total=len(tasks),
        by_status=by_status
    )


@router.get("/{task_id}", response_model=TaskResponse, dependencies=[Depends(require_auth)])
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get task by ID"""
    service = get_task_queue_service()
    task = await service.get_task(db, task_id)
    
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    return task_to_response(task)


@router.patch("/{task_id}", response_model=TaskResponse, dependencies=[Depends(require_auth)])
async def update_task(
    task_id: str,
    update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SERVICE)),
):
    """
    Update task properties.
    
    Only allowed for pending/scheduled tasks.
    """
    service = get_task_queue_service()
    
    # Get task first to check status
    task = await service.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    # Only allow updates to pending/scheduled tasks
    if task.status not in (TaskModelStatus.PENDING, TaskModelStatus.SCHEDULED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update task in {task.status.value} state"
        )
    
    task = await service.update_task(db, task_id, update)
    return task_to_response(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Delete a task (admin only)"""
    service = get_task_queue_service()
    success = await service.delete_task(db, task_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )


# ============================================================================
# Worker Operations
# ============================================================================

@router.post("/claim", response_model=TaskClaimResponse)
@limiter.limit(RateLimits.TASKS_CLAIM)
async def claim_task(
    request: Request,
    claim: TaskClaim,
    task_types: Optional[List[str]] = Query(None, description="Filter by task types"),
    min_priority: Optional[int] = Query(None, ge=10, le=100, description="Minimum priority"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.AGENT, UserRole.SERVICE, UserRole.OPERATOR, UserRole.ADMIN)),
):
    """
    Claim the next available task for execution.
    
    Workers poll this endpoint to get work. Implements priority-based FIFO.
    Rate limited to prevent flooding.
    """
    service = get_task_queue_service()
    
    if principal.agent_id and principal.agent_id != claim.agent_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent identity mismatch")

    task = await service.claim_next_task(
        db=db,
        agent_id=claim.agent_id,
        task_types=task_types,
        min_priority=min_priority
    )
    
    if not task:
        return TaskClaimResponse(
            success=False,
            message="No tasks available"
        )
    
    return TaskClaimResponse(
        success=True,
        task=task_to_response(task)
    )


@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: str,
    claim: TaskClaim,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.AGENT, UserRole.SERVICE, UserRole.OPERATOR, UserRole.ADMIN)),
):
    """
    Mark a claimed task as running.
    
    Called by worker after receiving task via claim endpoint.
    """
    service = get_task_queue_service()
    
    try:
        if principal.agent_id and principal.agent_id != claim.agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent identity mismatch")
        task = await service.start_task(db, task_id, claim.agent_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return task_to_response(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    claim: TaskClaim,
    complete_data: TaskComplete,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.AGENT, UserRole.SERVICE, UserRole.OPERATOR, UserRole.ADMIN)),
):
    """
    Mark a task as completed.
    
    Called by worker after successful execution.
    """
    service = get_task_queue_service()
    
    try:
        if principal.agent_id and principal.agent_id != claim.agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent identity mismatch")
        task = await service.complete_task(db, task_id, claim.agent_id, complete_data)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return task_to_response(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{task_id}/fail", response_model=TaskResponse)
async def fail_task(
    task_id: str,
    claim: TaskClaim,
    fail_data: TaskFail,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.AGENT, UserRole.SERVICE, UserRole.OPERATOR, UserRole.ADMIN)),
):
    """
    Mark a task as failed.
    
    Task may be retried based on retry configuration.
    """
    service = get_task_queue_service()
    
    try:
        if principal.agent_id and principal.agent_id != claim.agent_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Agent identity mismatch")
        task = await service.fail_task(db, task_id, claim.agent_id, fail_data)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return task_to_response(task)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Task Control
# ============================================================================

@router.post("/{task_id}/cancel", dependencies=[Depends(require_auth)])
async def cancel_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN, UserRole.SERVICE)),
):
    """Cancel a pending/scheduled task"""
    service = get_task_queue_service()
    
    try:
        success = await service.cancel_task(db, task_id, principal.principal_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )
        return {"success": True, "message": f"Task {task_id} cancelled"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ============================================================================
# Statistics
# ============================================================================

@router.get("/stats/summary", response_model=TaskStats, dependencies=[Depends(require_auth)])
async def get_task_stats(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get task statistics summary"""
    service = get_task_queue_service()
    stats = await service.get_stats(db)
    return stats


@router.get("/queue/stats", response_model=QueueStats, dependencies=[Depends(require_auth)])
async def get_queue_stats(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get queue statistics (pending/scheduled tasks)"""
    service = get_task_queue_service()
    stats = await service.get_queue_stats(db)
    return stats


# ============================================================================
# Background Jobs
# ============================================================================

@router.post("/admin/process-scheduled", dependencies=[Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN))])
async def process_scheduled_tasks(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Manually trigger processing of scheduled tasks.
    
    Normally run by background worker, but can be triggered manually.
    """
    service = get_task_queue_service()
    activated = await service.process_scheduled_tasks(db)
    
    return {
        "processed": True,
        "activated_count": len(activated),
        "activated_task_ids": [t.task_id for t in activated]
    }
