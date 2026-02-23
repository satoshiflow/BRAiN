"""
Task Queue System - Database Models

Advanced job queue with prioritization, scheduling, and EventStream integration.
Extends the existing mission queue with more robust features.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any

from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum, Integer, Float, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class TaskStatus(str, Enum):
    """Task lifecycle states"""
    PENDING = "pending"           # Waiting in queue
    SCHEDULED = "scheduled"       # Scheduled for future execution
    CLAIMED = "claimed"           # Claimed by a worker but not started
    RUNNING = "running"           # Currently executing
    COMPLETED = "completed"       # Successfully finished
    FAILED = "failed"             # Execution failed
    CANCELLED = "cancelled"       # Manually cancelled
    TIMEOUT = "timeout"           # Execution timed out
    RETRYING = "retrying"         # Failed but will retry


class TaskPriority(int, Enum):
    """Task priority levels (higher = more important)"""
    CRITICAL = 100     # System-critical, execute immediately
    HIGH = 75          # High priority
    NORMAL = 50        # Default priority
    LOW = 25           # Low priority, background tasks
    BACKGROUND = 10    # Very low, fill-in work


class TaskModel(Base):
    """
    Task database model.
    
    Represents a unit of work in the task queue.
    """
    __tablename__ = "tasks"
    
    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Task Type & Category
    task_type = Column(String(50), nullable=False, default="generic")
    category = Column(String(50), nullable=True)
    tags = Column(JSONB, nullable=False, default=list)
    
    # Status & Priority
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    priority = Column(Integer, nullable=False, default=TaskPriority.NORMAL.value)
    
    # Payload & Configuration
    payload = Column(JSONB, nullable=False, default=dict)
    config = Column(JSONB, nullable=False, default=dict)
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)  # For delayed execution
    deadline_at = Column(DateTime, nullable=True)   # Hard deadline
    
    # Execution Info
    claimed_by = Column(String(100), nullable=True, index=True)  # Agent that claimed
    claimed_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Retry Logic
    max_retries = Column(Integer, nullable=False, default=3)
    retry_count = Column(Integer, nullable=False, default=0)
    retry_delay_seconds = Column(Integer, nullable=False, default=60)
    
    # Results
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSONB, nullable=True)
    
    # Performance Metrics
    execution_time_ms = Column(Float, nullable=True)
    wait_time_ms = Column(Float, nullable=True)  # Time in queue before execution
    
    # Ownership
    created_by = Column(String(100), nullable=True)
    created_by_type = Column(String(50), nullable=True)  # user, agent, system
    
    # Dependencies
    depends_on = Column(JSONB, nullable=False, default=list)  # List of task_ids
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, task_id={self.task_id}, status={self.status}, priority={self.priority})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type,
            "category": self.category,
            "tags": self.tags,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "priority": self.priority,
            "payload": self.payload,
            "config": self.config,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "deadline_at": self.deadline_at.isoformat() if self.deadline_at else None,
            "claimed_by": self.claimed_by,
            "claimed_at": self.claimed_at.isoformat() if self.claimed_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "max_retries": self.max_retries,
            "retry_count": self.retry_count,
            "result": self.result,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "wait_time_ms": self.wait_time_ms,
            "created_by": self.created_by,
            "depends_on": self.depends_on,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Create indexes for common queries
Index('idx_tasks_status_priority_created', TaskModel.status, TaskModel.priority, TaskModel.created_at)
Index('idx_tasks_claimed_by', TaskModel.claimed_by)
Index('idx_tasks_scheduled_at', TaskModel.scheduled_at)
