"""
Task Queue System - Service Layer

Business logic for task queue management with prioritization and EventStream.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TaskModel, TaskStatus, TaskPriority
from .schemas import (
    TaskCreate, TaskUpdate, TaskClaim, TaskComplete, TaskFail,
    TaskResponse, TaskStats, QueueStats
)


class TaskQueueService:
    """
    Task queue management service with EventStream integration.
    
    Features:
    - Priority-based task scheduling
    - Claim/complete/fail workflow
    - Automatic retry with backoff
    - Scheduled/delayed task execution
    - Dependency management
    """
    
    def __init__(self, event_stream=None):
        """Initialize task queue service"""
        self.event_stream = event_stream
        logger.info("📋 Task Queue Service initialized")
    
    async def _publish_event(self, event_type: str, task_id: str, data: Dict[str, Any] = None):
        """Publish event to EventStream if available"""
        if self.event_stream is None:
            return
        
        try:
            await self.event_stream.publish({
                "type": event_type,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data or {}
            })
        except Exception as e:
            logger.warning(f"Failed to publish event {event_type}: {e}")
    
    # ========================================================================
    # Task Creation
    # ========================================================================
    
    async def create_task(
        self,
        db: AsyncSession,
        task_data: TaskCreate,
        created_by: Optional[str] = None,
        created_by_type: Optional[str] = None
    ) -> TaskModel:
        """
        Create a new task in the queue.
        
        Args:
            db: Database session
            task_data: Task creation data
            created_by: ID of creator (user, agent, etc.)
            created_by_type: Type of creator
            
        Returns:
            Created task model
        """
        # Generate task_id if not provided
        task_id = task_data.task_id or f"task-{uuid4().hex[:12]}"
        
        # Check for duplicate task_id
        result = await db.execute(
            select(TaskModel).where(TaskModel.task_id == task_id)
        )
        if result.scalar_one_or_none():
            raise ValueError(f"Task with ID '{task_id}' already exists")
        
        # Determine initial status based on scheduling
        initial_status = TaskStatus.PENDING
        if task_data.scheduled_at and task_data.scheduled_at > datetime.now(timezone.utc):
            initial_status = TaskStatus.SCHEDULED
        
        task = TaskModel(
            task_id=task_id,
            name=task_data.name,
            description=task_data.description,
            task_type=task_data.task_type,
            category=task_data.category,
            tags=task_data.tags,
            status=initial_status,
            priority=task_data.priority.value,
            payload=task_data.payload,
            config=task_data.config,
            scheduled_at=task_data.scheduled_at,
            deadline_at=task_data.deadline_at,
            max_retries=task_data.max_retries,
            retry_delay_seconds=task_data.retry_delay_seconds,
            depends_on=task_data.depends_on,
            created_by=created_by,
            created_by_type=created_by_type,
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        
        event_type = "task.scheduled" if initial_status == TaskStatus.SCHEDULED else "task.created"
        logger.info(f"➕ Task created: {task_id} ({task_data.name}) - Priority: {task_data.priority.name}")
        await self._publish_event(event_type, task_id, {
            "name": task_data.name,
            "type": task_data.task_type,
            "priority": task_data.priority.value,
            "scheduled": task_data.scheduled_at is not None
        })
        
        return task
    
    # ========================================================================
    # Task Claiming (Worker pulls task)
    # ========================================================================
    
    async def claim_next_task(
        self,
        db: AsyncSession,
        agent_id: str,
        task_types: Optional[List[str]] = None,
        min_priority: Optional[int] = None
    ) -> Optional[TaskModel]:
        """
        Claim the next available task for execution.
        
        Implements priority-based FIFO with task type filtering.
        
        Args:
            db: Database session
            agent_id: ID of agent claiming the task
            task_types: Optional filter for specific task types
            min_priority: Optional minimum priority threshold
            
        Returns:
            Claimed task or None if no tasks available
        """
        now = datetime.now(timezone.utc)
        
        # Build query for available tasks
        query = select(TaskModel).where(
            or_(
                and_(
                    TaskModel.status == TaskStatus.PENDING,
                    TaskModel.scheduled_at.is_(None)
                ),
                and_(
                    TaskModel.status == TaskStatus.SCHEDULED,
                    TaskModel.scheduled_at <= now
                )
            )
        )
        
        # Filter by task types if specified
        if task_types:
            query = query.where(TaskModel.task_type.in_(task_types))
        
        # Filter by minimum priority
        if min_priority is not None:
            query = query.where(TaskModel.priority >= min_priority)
        
        # Order by priority desc, then created_at asc (FIFO within same priority)
        query = query.order_by(desc(TaskModel.priority), asc(TaskModel.created_at))
        
        # Get the highest priority task
        result = await db.execute(query.limit(1))
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        # Check dependencies
        if task.depends_on:
            # Check if all dependencies are completed
            deps_result = await db.execute(
                select(TaskModel.status).where(TaskModel.task_id.in_(task.depends_on))
            )
            dep_statuses = {row[0] for row in deps_result.all()}
            
            # If any dependency is not completed, skip this task
            if dep_statuses and dep_statuses != {TaskStatus.COMPLETED}:
                logger.debug(f"Task {task.task_id} has incomplete dependencies, skipping")
                return None
        
        # Claim the task
        task.status = TaskStatus.CLAIMED
        task.claimed_by = agent_id
        task.claimed_at = now
        
        # Calculate wait time
        if task.created_at:
            task.wait_time_ms = (now - task.created_at).total_seconds() * 1000
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"🔒 Task {task.task_id} claimed by {agent_id}")
        await self._publish_event("task.claimed", task.task_id, {
            "agent_id": agent_id,
            "priority": task.priority
        })
        
        return task
    
    async def start_task(
        self,
        db: AsyncSession,
        task_id: str,
        agent_id: str
    ) -> Optional[TaskModel]:
        """
        Mark a claimed task as running.
        
        Args:
            db: Database session
            task_id: Task identifier
            agent_id: Agent starting the task
            
        Returns:
            Updated task or None if not found
        """
        result = await db.execute(
            select(TaskModel).where(TaskModel.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        if task.claimed_by != agent_id:
            raise ValueError(f"Task {task_id} was claimed by {task.claimed_by}, not {agent_id}")
        
        if task.status != TaskStatus.CLAIMED:
            raise ValueError(f"Task {task_id} is not in CLAIMED state")
        
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"▶️ Task {task_id} started by {agent_id}")
        await self._publish_event("task.started", task_id, {
            "agent_id": agent_id,
            "wait_time_ms": task.wait_time_ms
        })
        
        return task
    
    # ========================================================================
    # Task Completion / Failure
    # ========================================================================
    
    async def complete_task(
        self,
        db: AsyncSession,
        task_id: str,
        agent_id: str,
        complete_data: TaskComplete
    ) -> Optional[TaskModel]:
        """
        Mark a task as completed.
        
        Args:
            db: Database session
            task_id: Task identifier
            agent_id: Agent completing the task
            complete_data: Completion data including result
            
        Returns:
            Updated task or None if not found
        """
        result = await db.execute(
            select(TaskModel).where(TaskModel.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        if task.claimed_by != agent_id:
            raise ValueError(f"Task {task_id} was claimed by {task.claimed_by}, not {agent_id}")
        
        now = datetime.now(timezone.utc)
        task.status = TaskStatus.COMPLETED
        task.completed_at = now
        task.result = complete_data.result
        
        if complete_data.execution_time_ms:
            task.execution_time_ms = complete_data.execution_time_ms
        elif task.started_at:
            task.execution_time_ms = (now - task.started_at).total_seconds() * 1000
        
        await db.commit()
        await db.refresh(task)
        
        logger.info(f"✅ Task {task_id} completed by {agent_id}")
        await self._publish_event("task.completed", task_id, {
            "agent_id": agent_id,
            "execution_time_ms": task.execution_time_ms,
            "wait_time_ms": task.wait_time_ms
        })
        
        return task
    
    async def fail_task(
        self,
        db: AsyncSession,
        task_id: str,
        agent_id: str,
        fail_data: TaskFail
    ) -> Optional[TaskModel]:
        """
        Mark a task as failed with optional retry.
        
        Args:
            db: Database session
            task_id: Task identifier
            agent_id: Agent that failed the task
            fail_data: Failure data including error details
            
        Returns:
            Updated task or None if not found
        """
        result = await db.execute(
            select(TaskModel).where(TaskModel.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return None
        
        task.error_message = fail_data.error_message
        task.error_details = fail_data.error_details
        task.retry_count += 1
        
        # Check if we should retry
        if fail_data.retry and task.retry_count < task.max_retries:
            # Schedule retry
            task.status = TaskStatus.RETRYING
            task.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=task.retry_delay_seconds)
            task.claimed_by = None
            task.claimed_at = None
            task.started_at = None
            
            await db.commit()
            await db.refresh(task)
            
            logger.warning(f"🔄 Task {task_id} failed, retrying ({task.retry_count}/{task.max_retries})")
            await self._publish_event("task.retrying", task_id, {
                "agent_id": agent_id,
                "error": fail_data.error_message[:100],
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "retry_at": task.scheduled_at.isoformat()
            })
        else:
            # No more retries
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now(timezone.utc)
            
            if task.started_at:
                task.execution_time_ms = (task.completed_at - task.started_at).total_seconds() * 1000
            
            await db.commit()
            await db.refresh(task)
            
            logger.error(f"❌ Task {task_id} failed permanently after {task.retry_count} retries")
            await self._publish_event("task.failed", task_id, {
                "agent_id": agent_id,
                "error": fail_data.error_message[:200],
                "retry_count": task.retry_count,
                "final": True
            })
        
        return task
    
    async def cancel_task(
        self,
        db: AsyncSession,
        task_id: str,
        cancelled_by: str
    ) -> bool:
        """
        Cancel a pending or scheduled task.
        
        Args:
            db: Database session
            task_id: Task identifier
            cancelled_by: User/agent cancelling the task
            
        Returns:
            True if cancelled, False if not found or not cancellable
        """
        result = await db.execute(
            select(TaskModel).where(TaskModel.task_id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            return False
        
        # Can only cancel pending, scheduled, or claimed tasks
        if task.status not in (TaskStatus.PENDING, TaskStatus.SCHEDULED, TaskStatus.CLAIMED):
            raise ValueError(f"Cannot cancel task in {task.status.value} state")
        
        task.status = TaskStatus.CANCELLED
        task.completed_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        logger.info(f"🚫 Task {task_id} cancelled by {cancelled_by}")
        await self._publish_event("task.cancelled", task_id, {
            "cancelled_by": cancelled_by,
            "previous_status": task.status.value
        })
        
        return True
    
    # ========================================================================
    # Queries
    # ========================================================================
    
    async def get_tasks(
        self,
        db: AsyncSession,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TaskModel]:
        """Get tasks with optional filtering"""
        query = select(TaskModel)
        
        if status:
            query = query.where(TaskModel.status == status)
        if task_type:
            query = query.where(TaskModel.task_type == task_type)
        
        query = query.order_by(desc(TaskModel.priority), asc(TaskModel.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    async def get_task(self, db: AsyncSession, task_id: str) -> Optional[TaskModel]:
        """Get task by task_id"""
        result = await db.execute(
            select(TaskModel).where(TaskModel.task_id == task_id)
        )
        return result.scalar_one_or_none()
    
    async def get_stats(self, db: AsyncSession) -> TaskStats:
        """Get task statistics"""
        # Count by status
        result = await db.execute(
            select(TaskModel.status, func.count(TaskModel.id))
            .group_by(TaskModel.status)
        )
        status_counts = {row[0].value: row[1] for row in result.all()}
        
        # Total counts
        result = await db.execute(select(func.count(TaskModel.id)))
        total = result.scalar() or 0
        
        # Execution times
        result = await db.execute(
            select(
                func.avg(TaskModel.execution_time_ms),
                func.avg(TaskModel.wait_time_ms)
            ).where(TaskModel.status == TaskStatus.COMPLETED)
        )
        avg_times = result.one()
        
        return TaskStats(
            total_tasks=total,
            pending_count=status_counts.get("pending", 0),
            running_count=status_counts.get("running", 0),
            completed_count=status_counts.get("completed", 0),
            failed_count=status_counts.get("failed", 0),
            avg_execution_time_ms=avg_times[0],
            avg_wait_time_ms=avg_times[1],
            throughput_per_minute=None  # TODO: Calculate from recent completions
        )
    
    async def get_queue_stats(self, db: AsyncSession) -> QueueStats:
        """Get queue statistics"""
        # Pending/scheduled count
        result = await db.execute(
            select(func.count(TaskModel.id)).where(
                TaskModel.status.in_([TaskStatus.PENDING, TaskStatus.SCHEDULED])
            )
        )
        queue_length = result.scalar() or 0
        
        # By priority
        result = await db.execute(
            select(TaskModel.priority, func.count(TaskModel.id))
            .where(TaskModel.status.in_([TaskStatus.PENDING, TaskStatus.SCHEDULED]))
            .group_by(TaskModel.priority)
        )
        by_priority = {row[0]: row[1] for row in result.all()}
        
        # Oldest pending
        result = await db.execute(
            select(TaskModel.created_at).where(
                TaskModel.status.in_([TaskStatus.PENDING, TaskStatus.SCHEDULED])
            ).order_by(asc(TaskModel.created_at)).limit(1)
        )
        oldest = result.scalar_one_or_none()
        
        return QueueStats(
            queue_length=queue_length,
            by_priority=by_priority,
            oldest_pending=oldest,
            estimated_wait_seconds=None  # TODO: Calculate based on worker throughput
        )
    
    # ========================================================================
    # Background Jobs
    # ========================================================================
    
    async def process_scheduled_tasks(self, db: AsyncSession) -> List[TaskModel]:
        """
        Move scheduled tasks whose time has come to PENDING status.
        
        Returns:
            List of tasks that were activated
        """
        now = datetime.now(timezone.utc)
        
        result = await db.execute(
            select(TaskModel).where(
                and_(
                    TaskModel.status == TaskStatus.SCHEDULED,
                    TaskModel.scheduled_at <= now
                )
            )
        )
        tasks = result.scalars().all()
        
        activated = []
        for task in tasks:
            task.status = TaskStatus.PENDING
            task.scheduled_at = None
            activated.append(task)
        
        if activated:
            await db.commit()
            logger.info(f"⏰ Activated {len(activated)} scheduled tasks")
        
        return list(activated)


# Singleton instance
_task_queue_service: Optional[TaskQueueService] = None


def get_task_queue_service(event_stream=None) -> TaskQueueService:
    """Get or create the task queue service singleton"""
    global _task_queue_service
    if _task_queue_service is None:
        _task_queue_service = TaskQueueService(event_stream=event_stream)
    return _task_queue_service
