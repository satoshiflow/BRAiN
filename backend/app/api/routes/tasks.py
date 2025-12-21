"""
Task Management API

REST API endpoints for managing background tasks (Celery).

Endpoints:
- POST /api/tasks/execute - Execute task
- GET /api/tasks/{task_id} - Get task status
- DELETE /api/tasks/{task_id} - Cancel task
- GET /api/tasks/active - List active tasks
- GET /api/tasks/scheduled - List scheduled tasks
- GET /api/tasks/workers - Get worker stats
- POST /api/tasks/purge - Purge task results

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.app.core.celery_app import (
    TaskResult,
    celery_app,
    get_active_tasks,
    get_registered_tasks,
    get_reserved_tasks,
    get_scheduled_tasks,
    get_task_result,
    get_worker_stats,
    purge_queue,
    purge_task_results,
    revoke_all_tasks,
    revoke_task,
)
from backend.app.core.security import Principal, require_admin

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TaskExecuteRequest(BaseModel):
    """Task execution request."""

    task_name: str = Field(..., description="Fully qualified task name")
    args: List[Any] = Field(default=[], description="Positional arguments")
    kwargs: Dict[str, Any] = Field(default={}, description="Keyword arguments")
    queue: Optional[str] = Field(None, description="Queue name (default, system, missions, agents, maintenance)")
    countdown: Optional[int] = Field(None, description="Delay execution by N seconds")
    eta: Optional[datetime] = Field(None, description="Specific execution time")

    class Config:
        json_schema_extra = {
            "example": {
                "task_name": "backend.app.tasks.system_tasks.health_check",
                "args": [],
                "kwargs": {},
                "queue": "system",
            }
        }


class TaskExecuteResponse(BaseModel):
    """Task execution response."""

    task_id: str = Field(..., description="Task ID")
    task_name: str = Field(..., description="Task name")
    status: str = Field(..., description="Task status")
    queue: Optional[str] = Field(None, description="Queue name")
    eta: Optional[datetime] = Field(None, description="Scheduled execution time")


class TaskStatusResponse(BaseModel):
    """Task status response."""

    task_id: str = Field(..., description="Task ID")
    status: str = Field(..., description="Task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED)")
    ready: bool = Field(..., description="Whether task has completed")
    successful: Optional[bool] = Field(None, description="Whether task succeeded (if completed)")
    result: Optional[Any] = Field(None, description="Task result (if successful)")
    traceback: Optional[str] = Field(None, description="Error traceback (if failed)")
    info: Optional[Dict[str, Any]] = Field(None, description="Additional task info")


class TaskInfo(BaseModel):
    """Active task information."""

    worker: str = Field(..., description="Worker name")
    task_id: str = Field(..., description="Task ID")
    task_name: str = Field(..., description="Task name")
    args: List[Any] = Field(default=[], description="Task arguments")
    kwargs: Dict[str, Any] = Field(default={}, description="Task keyword arguments")
    time_start: Optional[float] = Field(None, description="Task start timestamp")


class ScheduledTaskInfo(BaseModel):
    """Scheduled task information."""

    worker: str = Field(..., description="Worker name")
    task_id: str = Field(..., description="Task ID")
    task_name: str = Field(..., description="Task name")
    eta: str = Field(..., description="Scheduled execution time")


class WorkerStatsResponse(BaseModel):
    """Worker statistics response."""

    workers: Dict[str, Any] = Field(..., description="Worker statistics by worker name")
    total_workers: int = Field(..., description="Total number of workers")


class RegisteredTasksResponse(BaseModel):
    """Registered tasks response."""

    tasks: List[str] = Field(..., description="List of registered task names")
    total: int = Field(..., description="Total number of registered tasks")


# ============================================================================
# Task Execution Endpoints
# ============================================================================

@router.post("/execute", response_model=TaskExecuteResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_task(
    request: TaskExecuteRequest,
    principal: Principal = Depends(require_admin)
) -> TaskExecuteResponse:
    """
    Execute a background task.

    **Permissions:** Admin only

    **Args:**
    - task_name: Fully qualified task name (e.g., "backend.app.tasks.system_tasks.health_check")
    - args: Positional arguments for task
    - kwargs: Keyword arguments for task
    - queue: Target queue (default, system, missions, agents, maintenance)
    - countdown: Delay execution by N seconds
    - eta: Schedule for specific time

    **Returns:**
    - Task ID and status

    **Example:**
    ```json
    {
        "task_name": "backend.app.tasks.system_tasks.health_check",
        "queue": "system"
    }
    ```
    """
    try:
        # Get task from registry
        task = celery_app.tasks.get(request.task_name)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task not found: {request.task_name}"
            )

        # Execute task
        apply_kwargs = {
            "args": request.args,
            "kwargs": request.kwargs,
        }

        if request.queue:
            apply_kwargs["queue"] = request.queue

        if request.countdown:
            apply_kwargs["countdown"] = request.countdown

        if request.eta:
            apply_kwargs["eta"] = request.eta

        result = task.apply_async(**apply_kwargs)

        return TaskExecuteResponse(
            task_id=result.id,
            task_name=request.task_name,
            status=result.state,
            queue=request.queue,
            eta=request.eta,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute task: {str(e)}"
        )


# ============================================================================
# Task Status Endpoints
# ============================================================================

@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    principal: Principal = Depends(require_admin)
) -> TaskStatusResponse:
    """
    Get task status and result.

    **Permissions:** Admin only

    **Args:**
    - task_id: Task ID

    **Returns:**
    - Task status, result (if completed), and metadata

    **Statuses:**
    - PENDING: Task waiting to be executed
    - STARTED: Task has been started
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed with exception
    - RETRY: Task is being retried
    - REVOKED: Task was cancelled
    """
    try:
        task_result = get_task_result(task_id)
        info = task_result.get_info()

        return TaskStatusResponse(
            task_id=info["task_id"],
            status=info["status"],
            ready=info["ready"],
            successful=info["successful"],
            result=info["result"],
            traceback=info["traceback"],
            info=info["info"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_task(
    task_id: str,
    terminate: bool = Query(False, description="Terminate if already running"),
    principal: Principal = Depends(require_admin)
):
    """
    Cancel (revoke) a task.

    **Permissions:** Admin only

    **Args:**
    - task_id: Task ID to cancel
    - terminate: If true, terminate task if already running (use with caution)

    **Returns:**
    - 204 No Content

    **Note:** Terminated tasks may leave resources in inconsistent state.
    """
    try:
        revoke_task(task_id, terminate=terminate)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


# ============================================================================
# Task Monitoring Endpoints
# ============================================================================

@router.get("/active/list", response_model=List[TaskInfo])
async def list_active_tasks(
    principal: Principal = Depends(require_admin)
) -> List[TaskInfo]:
    """
    List all active (running) tasks.

    **Permissions:** Admin only

    **Returns:**
    - List of currently executing tasks
    """
    try:
        active_tasks = get_active_tasks()
        return [TaskInfo(**task) for task in active_tasks]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list active tasks: {str(e)}"
        )


@router.get("/scheduled/list", response_model=List[ScheduledTaskInfo])
async def list_scheduled_tasks(
    principal: Principal = Depends(require_admin)
) -> List[ScheduledTaskInfo]:
    """
    List all scheduled (ETA/countdown) tasks.

    **Permissions:** Admin only

    **Returns:**
    - List of tasks scheduled for future execution
    """
    try:
        scheduled_tasks = get_scheduled_tasks()
        return [ScheduledTaskInfo(**task) for task in scheduled_tasks]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list scheduled tasks: {str(e)}"
        )


@router.get("/reserved/list", response_model=List[Dict[str, Any]])
async def list_reserved_tasks(
    principal: Principal = Depends(require_admin)
) -> List[Dict[str, Any]]:
    """
    List all reserved (queued) tasks.

    **Permissions:** Admin only

    **Returns:**
    - List of tasks in worker queues
    """
    try:
        return get_reserved_tasks()

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list reserved tasks: {str(e)}"
        )


@router.get("/workers/stats", response_model=WorkerStatsResponse)
async def get_workers_stats(
    principal: Principal = Depends(require_admin)
) -> WorkerStatsResponse:
    """
    Get worker statistics.

    **Permissions:** Admin only

    **Returns:**
    - Worker statistics including pool size, active tasks, etc.
    """
    try:
        stats = get_worker_stats()
        return WorkerStatsResponse(
            workers=stats,
            total_workers=len(stats)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get worker stats: {str(e)}"
        )


@router.get("/registered/list", response_model=RegisteredTasksResponse)
async def list_registered_tasks(
    principal: Principal = Depends(require_admin)
) -> RegisteredTasksResponse:
    """
    List all registered task names.

    **Permissions:** Admin only

    **Returns:**
    - List of all available task names
    """
    try:
        tasks = get_registered_tasks()
        return RegisteredTasksResponse(
            tasks=tasks,
            total=len(tasks)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list registered tasks: {str(e)}"
        )


# ============================================================================
# Task Control Endpoints
# ============================================================================

@router.post("/purge/results", status_code=status.HTTP_204_NO_CONTENT)
async def purge_results(
    task_ids: Optional[List[str]] = None,
    principal: Principal = Depends(require_admin)
):
    """
    Purge task results from backend.

    **Permissions:** Admin only

    **Args:**
    - task_ids: Specific task IDs to purge (omit to purge all)

    **Returns:**
    - 204 No Content
    """
    try:
        purge_task_results(task_ids)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge task results: {str(e)}"
        )


@router.post("/purge/queue", response_model=Dict[str, int])
async def purge_task_queue(
    queue_name: str = Query("default", description="Queue to purge"),
    principal: Principal = Depends(require_admin)
) -> Dict[str, int]:
    """
    Purge all tasks from a queue.

    **Permissions:** Admin only

    **Args:**
    - queue_name: Queue to purge (default, system, missions, agents, maintenance)

    **Returns:**
    - Number of tasks purged

    **Warning:** This cancels ALL tasks in the queue.
    """
    try:
        purged_count = purge_queue(queue_name)
        return {"purged": purged_count, "queue": queue_name}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to purge queue: {str(e)}"
        )


@router.post("/cancel/all", response_model=Dict[str, int])
async def cancel_all_tasks(
    terminate: bool = Query(False, description="Terminate running tasks"),
    principal: Principal = Depends(require_admin)
) -> Dict[str, int]:
    """
    Cancel all tasks.

    **Permissions:** Admin only

    **Args:**
    - terminate: If true, terminate running tasks (use with extreme caution)

    **Returns:**
    - Number of tasks cancelled

    **Warning:** This is a destructive operation. Use only in emergencies.
    """
    try:
        cancelled_count = revoke_all_tasks(terminate=terminate)
        return {"cancelled": cancelled_count}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel all tasks: {str(e)}"
        )


# ============================================================================
# System Info Endpoint
# ============================================================================

@router.get("/info")
async def get_task_system_info() -> Dict[str, Any]:
    """
    Get task system information.

    **Returns:**
    - Task system configuration and status
    """
    return {
        "name": "BRAiN Task System",
        "version": "1.0.0",
        "broker": celery_app.conf.broker_url,
        "backend": celery_app.conf.result_backend,
        "queues": [
            {"name": "default", "priority": 5},
            {"name": "system", "priority": 10},
            {"name": "missions", "priority": 8},
            {"name": "agents", "priority": 6},
            {"name": "maintenance", "priority": 3},
        ],
        "task_time_limit": celery_app.conf.task_time_limit,
        "task_soft_time_limit": celery_app.conf.task_soft_time_limit,
        "worker_max_tasks_per_child": celery_app.conf.worker_max_tasks_per_child,
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
