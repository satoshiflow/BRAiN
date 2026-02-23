"""
Task Queue System - Pydantic Schemas

Validation schemas for task queue management.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class TaskStatus(str, Enum):
    """Task lifecycle states"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    RETRYING = "retrying"


class TaskPriority(int, Enum):
    """Task priority levels"""
    CRITICAL = 100
    HIGH = 75
    NORMAL = 50
    LOW = 25
    BACKGROUND = 10


# ============================================================================
# CRUD Schemas
# ============================================================================

class TaskCreate(BaseModel):
    """Schema for creating a new task"""
    task_id: Optional[str] = Field(default=None, max_length=100, description="Optional custom task ID")
    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    description: Optional[str] = Field(default=None, description="Task description")
    task_type: str = Field(default="generic", description="Task type category")
    category: Optional[str] = Field(default=None, description="Optional category")
    tags: List[str] = Field(default_factory=list, description="Task tags")
    priority: TaskPriority = Field(default=TaskPriority.NORMAL, description="Task priority")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task payload/data")
    config: Dict[str, Any] = Field(default_factory=dict, description="Task configuration")
    scheduled_at: Optional[datetime] = Field(default=None, description="Schedule for future execution")
    deadline_at: Optional[datetime] = Field(default=None, description="Hard deadline")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_delay_seconds: int = Field(default=60, ge=1, le=3600, description="Delay between retries")
    depends_on: List[str] = Field(default_factory=list, description="Task IDs this task depends on")


class TaskUpdate(BaseModel):
    """Schema for updating a task"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    priority: Optional[TaskPriority] = Field(default=None)
    status: Optional[TaskStatus] = Field(default=None)
    max_retries: Optional[int] = Field(default=None, ge=0, le=10)
    scheduled_at: Optional[datetime] = Field(default=None)
    deadline_at: Optional[datetime] = Field(default=None)


class TaskClaim(BaseModel):
    """Schema for claiming a task"""
    agent_id: str = Field(..., description="ID of agent claiming the task")


class TaskComplete(BaseModel):
    """Schema for completing a task"""
    result: Dict[str, Any] = Field(default_factory=dict, description="Task result data")
    execution_time_ms: Optional[float] = Field(default=None, ge=0)


class TaskFail(BaseModel):
    """Schema for failing a task"""
    error_message: str = Field(..., description="Error message")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed error info")
    retry: bool = Field(default=True, description="Whether to retry this task")


class TaskResponse(BaseModel):
    """Schema for task response"""
    id: UUID = Field(..., description="Task UUID")
    task_id: str = Field(..., description="Task identifier")
    name: str = Field(...)
    description: Optional[str] = Field(default=None)
    task_type: str = Field(...)
    category: Optional[str] = Field(default=None)
    tags: List[str] = Field(default_factory=list)
    status: TaskStatus = Field(...)
    priority: int = Field(...)
    payload: Dict[str, Any] = Field(default_factory=dict)
    config: Dict[str, Any] = Field(default_factory=dict)
    scheduled_at: Optional[datetime] = Field(default=None)
    deadline_at: Optional[datetime] = Field(default=None)
    claimed_by: Optional[str] = Field(default=None)
    claimed_at: Optional[datetime] = Field(default=None)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    max_retries: int = Field(...)
    retry_count: int = Field(...)
    result: Optional[Dict[str, Any]] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    execution_time_ms: Optional[float] = Field(default=None)
    wait_time_ms: Optional[float] = Field(default=None)
    created_by: Optional[str] = Field(default=None)
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    
    class Config:
        from_attributes = True


class TaskListResponse(BaseModel):
    """Schema for listing tasks"""
    items: List[TaskResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of tasks")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Count by status")


class TaskStats(BaseModel):
    """Schema for task statistics"""
    total_tasks: int = Field(...)
    pending_count: int = Field(...)
    running_count: int = Field(...)
    completed_count: int = Field(...)
    failed_count: int = Field(...)
    avg_execution_time_ms: Optional[float] = Field(default=None)
    avg_wait_time_ms: Optional[float] = Field(default=None)
    throughput_per_minute: Optional[float] = Field(default=None)


# ============================================================================
# Queue Operations
# ============================================================================

class TaskClaimResponse(BaseModel):
    """Response when claiming a task"""
    success: bool = Field(...)
    task: Optional[TaskResponse] = Field(default=None)
    message: Optional[str] = Field(default=None)


class QueueStats(BaseModel):
    """Queue statistics"""
    queue_length: int = Field(..., description="Number of pending tasks")
    by_priority: Dict[int, int] = Field(default_factory=dict, description="Pending tasks by priority")
    oldest_pending: Optional[datetime] = Field(default=None, description="Oldest pending task timestamp")
    estimated_wait_seconds: Optional[int] = Field(default=None, description="Estimated wait time for new normal priority task")


# ============================================================================
# Event Schemas
# ============================================================================

class TaskEvent(BaseModel):
    """Base schema for task events"""
    event_type: str = Field(..., description="Event type")
    task_id: str = Field(..., description="Task identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)


class TaskCreatedEvent(TaskEvent):
    """Event: Task created"""
    event_type: str = "task.created"
    data: Dict[str, Any] = Field(default_factory=dict)


class TaskScheduledEvent(TaskEvent):
    """Event: Task scheduled for future execution"""
    event_type: str = "task.scheduled"
    scheduled_at: datetime = Field(...)


class TaskClaimedEvent(TaskEvent):
    """Event: Task claimed by agent"""
    event_type: str = "task.claimed"
    agent_id: str = Field(...)


class TaskStartedEvent(TaskEvent):
    """Event: Task execution started"""
    event_type: str = "task.started"
    agent_id: str = Field(...)


class TaskCompletedEvent(TaskEvent):
    """Event: Task completed successfully"""
    event_type: str = "task.completed"
    execution_time_ms: float = Field(...)
    result_summary: Optional[str] = Field(default=None)


class TaskFailedEvent(TaskEvent):
    """Event: Task failed"""
    event_type: str = "task.failed"
    error_message: str = Field(...)
    will_retry: bool = Field(default=False)


class TaskCancelledEvent(TaskEvent):
    """Event: Task cancelled"""
    event_type: str = "task.cancelled"
    cancelled_by: str = Field(...)


class TaskRetryingEvent(TaskEvent):
    """Event: Task retrying after failure"""
    event_type: str = "task.retrying"
    retry_count: int = Field(...)
    max_retries: int = Field(...)
