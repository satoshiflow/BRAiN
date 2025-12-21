"""
Celery Application Configuration

Provides distributed task queue using Celery with Redis broker.
Supports:
- Asynchronous task execution
- Scheduled tasks (Celery Beat)
- Task result storage
- Retry logic with exponential backoff
- Task monitoring and status tracking

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from celery import Celery
from celery.schedules import crontab
from kombu import Exchange, Queue

from backend.app.core.config import get_settings

settings = get_settings()


# ============================================================================
# Celery App Configuration
# ============================================================================

def make_celery() -> Celery:
    """Create and configure Celery application."""

    celery_app = Celery(
        "brain",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=[
            "backend.app.tasks.system_tasks",
            "backend.app.tasks.mission_tasks",
            "backend.app.tasks.agent_tasks",
            "backend.app.tasks.maintenance_tasks",
        ]
    )

    # Task Configuration
    celery_app.conf.update(
        # Result backend
        result_backend=settings.REDIS_URL,
        result_expires=3600,  # 1 hour
        result_persistent=True,

        # Task execution
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,

        # Task routing
        task_routes={
            "backend.app.tasks.system_tasks.*": {"queue": "system"},
            "backend.app.tasks.mission_tasks.*": {"queue": "missions"},
            "backend.app.tasks.agent_tasks.*": {"queue": "agents"},
            "backend.app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
        },

        # Task queues
        task_queues=(
            Queue("default", Exchange("default"), routing_key="default"),
            Queue("system", Exchange("system"), routing_key="system", priority=10),
            Queue("missions", Exchange("missions"), routing_key="missions", priority=8),
            Queue("agents", Exchange("agents"), routing_key="agents", priority=6),
            Queue("maintenance", Exchange("maintenance"), routing_key="maintenance", priority=3),
        ),

        # Worker configuration
        worker_prefetch_multiplier=4,
        worker_max_tasks_per_child=1000,
        worker_disable_rate_limits=False,

        # Task time limits
        task_soft_time_limit=300,  # 5 minutes
        task_time_limit=600,  # 10 minutes (hard limit)

        # Retry configuration
        task_acks_late=True,
        task_reject_on_worker_lost=True,

        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,

        # Beat schedule (scheduled tasks)
        beat_schedule={
            # System health check every 5 minutes
            "system-health-check": {
                "task": "backend.app.tasks.system_tasks.health_check",
                "schedule": 300.0,  # 5 minutes
                "options": {"queue": "system"},
            },

            # Cleanup old audit logs daily at 2 AM
            "cleanup-audit-logs": {
                "task": "backend.app.tasks.maintenance_tasks.cleanup_audit_logs",
                "schedule": crontab(hour=2, minute=0),
                "options": {"queue": "maintenance"},
            },

            # Cleanup old task results daily at 3 AM
            "cleanup-task-results": {
                "task": "backend.app.tasks.maintenance_tasks.cleanup_task_results",
                "schedule": crontab(hour=3, minute=0),
                "options": {"queue": "maintenance"},
            },

            # Mission queue health check every minute
            "mission-queue-health": {
                "task": "backend.app.tasks.mission_tasks.check_mission_queue_health",
                "schedule": 60.0,  # 1 minute
                "options": {"queue": "missions"},
            },

            # Agent heartbeat check every 30 seconds
            "agent-heartbeat": {
                "task": "backend.app.tasks.agent_tasks.check_agent_heartbeats",
                "schedule": 30.0,  # 30 seconds
                "options": {"queue": "agents"},
            },

            # Rotate encryption keys monthly (1st of month at 4 AM)
            "rotate-encryption-keys": {
                "task": "backend.app.tasks.maintenance_tasks.rotate_encryption_keys",
                "schedule": crontab(day_of_month=1, hour=4, minute=0),
                "options": {"queue": "maintenance"},
            },

            # Generate daily metrics report at midnight
            "daily-metrics-report": {
                "task": "backend.app.tasks.system_tasks.generate_daily_metrics",
                "schedule": crontab(hour=0, minute=0),
                "options": {"queue": "system"},
            },
        },
    )

    return celery_app


# Create Celery app instance
celery_app = make_celery()


# ============================================================================
# Task Decorators and Utilities
# ============================================================================

def task_with_retry(
    max_retries: int = 3,
    default_retry_delay: int = 60,
    autoretry_for: tuple = (Exception,),
    retry_backoff: bool = True,
    retry_backoff_max: int = 600,
    retry_jitter: bool = True,
    **kwargs
):
    """
    Decorator for tasks with automatic retry and exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        default_retry_delay: Base delay between retries (seconds)
        autoretry_for: Tuple of exception types to auto-retry
        retry_backoff: Enable exponential backoff
        retry_backoff_max: Maximum backoff delay (seconds)
        retry_jitter: Add random jitter to backoff
        **kwargs: Additional Celery task options

    Usage:
        @task_with_retry(max_retries=5)
        def my_task():
            # Task implementation
            pass
    """
    return celery_app.task(
        bind=True,
        max_retries=max_retries,
        default_retry_delay=default_retry_delay,
        autoretry_for=autoretry_for,
        retry_backoff=retry_backoff,
        retry_backoff_max=retry_backoff_max,
        retry_jitter=retry_jitter,
        **kwargs
    )


# ============================================================================
# Task Result Management
# ============================================================================

class TaskResult:
    """Task result wrapper with status tracking."""

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.result = celery_app.AsyncResult(task_id)

    @property
    def status(self) -> str:
        """Get task status (PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED)."""
        return self.result.state

    @property
    def ready(self) -> bool:
        """Check if task has completed."""
        return self.result.ready()

    @property
    def successful(self) -> bool:
        """Check if task completed successfully."""
        return self.result.successful()

    @property
    def failed(self) -> bool:
        """Check if task failed."""
        return self.result.failed()

    def get_result(self, timeout: Optional[float] = None) -> Any:
        """
        Get task result (blocks until ready).

        Args:
            timeout: Maximum time to wait (seconds)

        Returns:
            Task result value

        Raises:
            TimeoutError: If timeout exceeded
            Exception: If task raised an exception
        """
        return self.result.get(timeout=timeout)

    def get_info(self) -> Dict[str, Any]:
        """Get detailed task information."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "ready": self.ready,
            "successful": self.successful if self.ready else None,
            "result": self.result.result if self.ready and self.successful else None,
            "traceback": self.result.traceback if self.failed else None,
            "info": self.result.info,
        }

    def revoke(self, terminate: bool = False, signal: str = "SIGTERM"):
        """
        Revoke (cancel) task.

        Args:
            terminate: Terminate task if it's already running
            signal: Signal to send if terminating (SIGTERM, SIGKILL)
        """
        self.result.revoke(terminate=terminate, signal=signal)

    def forget(self):
        """Remove task result from backend."""
        self.result.forget()


def get_task_result(task_id: str) -> TaskResult:
    """Get task result by ID."""
    return TaskResult(task_id)


def purge_task_results(task_ids: Optional[list[str]] = None):
    """
    Purge task results from backend.

    Args:
        task_ids: Specific task IDs to purge (None = purge all)
    """
    if task_ids:
        for task_id in task_ids:
            result = celery_app.AsyncResult(task_id)
            result.forget()
    else:
        # Purge all results
        celery_app.backend.cleanup()


# ============================================================================
# Task Monitoring
# ============================================================================

def get_active_tasks() -> list[Dict[str, Any]]:
    """Get all active tasks across workers."""
    inspect = celery_app.control.inspect()
    active = inspect.active()

    if not active:
        return []

    tasks = []
    for worker, worker_tasks in active.items():
        for task in worker_tasks:
            tasks.append({
                "worker": worker,
                "task_id": task["id"],
                "task_name": task["name"],
                "args": task["args"],
                "kwargs": task["kwargs"],
                "time_start": task.get("time_start"),
            })

    return tasks


def get_scheduled_tasks() -> list[Dict[str, Any]]:
    """Get all scheduled (ETA/countdown) tasks."""
    inspect = celery_app.control.inspect()
    scheduled = inspect.scheduled()

    if not scheduled:
        return []

    tasks = []
    for worker, worker_tasks in scheduled.items():
        for task in worker_tasks:
            tasks.append({
                "worker": worker,
                "task_id": task["request"]["id"],
                "task_name": task["request"]["name"],
                "eta": task["eta"],
            })

    return tasks


def get_reserved_tasks() -> list[Dict[str, Any]]:
    """Get all reserved (queued) tasks."""
    inspect = celery_app.control.inspect()
    reserved = inspect.reserved()

    if not reserved:
        return []

    tasks = []
    for worker, worker_tasks in reserved.items():
        for task in worker_tasks:
            tasks.append({
                "worker": worker,
                "task_id": task["id"],
                "task_name": task["name"],
            })

    return tasks


def get_worker_stats() -> Dict[str, Any]:
    """Get worker statistics."""
    inspect = celery_app.control.inspect()
    stats = inspect.stats()

    if not stats:
        return {}

    return stats


def get_registered_tasks() -> list[str]:
    """Get all registered task names."""
    inspect = celery_app.control.inspect()
    registered = inspect.registered()

    if not registered:
        return []

    # Flatten task lists from all workers
    tasks = set()
    for worker_tasks in registered.values():
        tasks.update(worker_tasks)

    return sorted(list(tasks))


# ============================================================================
# Task Control
# ============================================================================

def revoke_task(task_id: str, terminate: bool = False, signal: str = "SIGTERM"):
    """
    Revoke (cancel) a task.

    Args:
        task_id: Task ID to revoke
        terminate: Terminate if already running
        signal: Signal to send if terminating
    """
    celery_app.control.revoke(task_id, terminate=terminate, signal=signal)


def revoke_all_tasks(terminate: bool = False):
    """Revoke all tasks."""
    inspect = celery_app.control.inspect()
    active = inspect.active() or {}
    scheduled = inspect.scheduled() or {}
    reserved = inspect.reserved() or {}

    # Collect all task IDs
    task_ids = set()

    for worker_tasks in active.values():
        for task in worker_tasks:
            task_ids.add(task["id"])

    for worker_tasks in scheduled.values():
        for task in worker_tasks:
            task_ids.add(task["request"]["id"])

    for worker_tasks in reserved.values():
        for task in worker_tasks:
            task_ids.add(task["id"])

    # Revoke all tasks
    for task_id in task_ids:
        celery_app.control.revoke(task_id, terminate=terminate)

    return len(task_ids)


def purge_queue(queue_name: str = "default") -> int:
    """
    Purge all tasks from a queue.

    Args:
        queue_name: Queue to purge

    Returns:
        Number of tasks purged
    """
    return celery_app.control.purge()


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "celery_app",
    "task_with_retry",
    "TaskResult",
    "get_task_result",
    "purge_task_results",
    "get_active_tasks",
    "get_scheduled_tasks",
    "get_reserved_tasks",
    "get_worker_stats",
    "get_registered_tasks",
    "revoke_task",
    "revoke_all_tasks",
    "purge_queue",
]
