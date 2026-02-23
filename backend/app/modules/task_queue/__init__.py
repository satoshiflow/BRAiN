"""
Task Queue System

Advanced job queue with prioritization, scheduling, and EventStream integration.

Features:
- Priority-based task scheduling
- Claim/complete/fail workflow
- Automatic retry with backoff
- Scheduled/delayed execution
- Dependency management
"""

from .models import TaskModel, TaskStatus, TaskPriority
from .schemas import (
    TaskCreate, TaskUpdate, TaskClaim, TaskComplete, TaskFail,
    TaskResponse, TaskListResponse, TaskStats, QueueStats
)
from .service import TaskQueueService, get_task_queue_service
from .router import router

__all__ = [
    "TaskModel",
    "TaskStatus",
    "TaskPriority",
    "TaskCreate",
    "TaskUpdate",
    "TaskClaim",
    "TaskComplete",
    "TaskFail",
    "TaskResponse",
    "TaskListResponse",
    "TaskStats",
    "QueueStats",
    "TaskQueueService",
    "get_task_queue_service",
    "router",
]
