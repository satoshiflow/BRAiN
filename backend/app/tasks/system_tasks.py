"""
System Tasks

Background tasks for system-level operations:
- Health checks
- Metrics generation
- System monitoring
- Resource cleanup

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict

from loguru import logger

from backend.app.core.celery_app import celery_app, task_with_retry


# ============================================================================
# Health Check Tasks
# ============================================================================

@task_with_retry(max_retries=1)
def health_check(self) -> Dict[str, Any]:
    """
    Perform system health check.

    Checks:
    - Redis connectivity
    - Database connectivity
    - Disk space
    - Memory usage

    Returns:
        Health check results
    """
    logger.info("Running system health check")

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
        "healthy": True,
    }

    # Check Redis
    try:
        from backend.app.core.redis_client import get_redis_client
        redis = get_redis_client()

        # Run async ping
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create new event loop for background task
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(redis.ping())

        results["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful",
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        results["checks"]["redis"] = {
            "status": "unhealthy",
            "message": str(e),
        }
        results["healthy"] = False

    # Check disk space
    try:
        import shutil

        disk_usage = shutil.disk_usage("/")
        free_gb = disk_usage.free / (1024 ** 3)
        total_gb = disk_usage.total / (1024 ** 3)
        percent_free = (disk_usage.free / disk_usage.total) * 100

        results["checks"]["disk"] = {
            "status": "healthy" if percent_free > 10 else "warning",
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "percent_free": round(percent_free, 2),
        }

        if percent_free < 10:
            results["healthy"] = False
    except Exception as e:
        logger.error(f"Disk check failed: {e}")
        results["checks"]["disk"] = {
            "status": "error",
            "message": str(e),
        }

    # Check memory
    try:
        import psutil

        memory = psutil.virtual_memory()
        results["checks"]["memory"] = {
            "status": "healthy" if memory.percent < 90 else "warning",
            "used_gb": round(memory.used / (1024 ** 3), 2),
            "total_gb": round(memory.total / (1024 ** 3), 2),
            "percent_used": round(memory.percent, 2),
        }

        if memory.percent >= 90:
            results["healthy"] = False
    except Exception as e:
        logger.error(f"Memory check failed: {e}")
        results["checks"]["memory"] = {
            "status": "error",
            "message": str(e),
        }

    logger.info(f"Health check completed: {'healthy' if results['healthy'] else 'unhealthy'}")
    return results


@task_with_retry(max_retries=2)
def generate_daily_metrics(self) -> Dict[str, Any]:
    """
    Generate daily system metrics report.

    Metrics:
    - Total API requests
    - Average response time
    - Error rate
    - Active users
    - Task execution stats

    Returns:
        Daily metrics report
    """
    logger.info("Generating daily metrics report")

    yesterday = datetime.utcnow() - timedelta(days=1)
    report = {
        "date": yesterday.date().isoformat(),
        "generated_at": datetime.utcnow().isoformat(),
        "metrics": {},
    }

    try:
        from backend.app.core.redis_client import get_redis_client
        from backend.app.core.audit import AuditAction, get_audit_logger

        redis = get_redis_client()
        audit_logger = get_audit_logger()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Query audit logs for yesterday
        start_time = datetime.combine(yesterday.date(), datetime.min.time())
        end_time = datetime.combine(yesterday.date(), datetime.max.time())

        audit_entries = loop.run_until_complete(
            audit_logger.query(
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
        )

        # Calculate metrics
        total_requests = len([e for e in audit_entries if e.action == AuditAction.API_REQUEST])
        total_errors = len([e for e in audit_entries if "error" in (e.details or {})])
        unique_users = len(set(e.user_id for e in audit_entries if e.user_id))

        # Calculate average response time
        response_times = [
            e.details.get("duration_ms", 0)
            for e in audit_entries
            if e.action == AuditAction.API_REQUEST and e.details
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        report["metrics"] = {
            "api_requests": {
                "total": total_requests,
                "avg_response_time_ms": round(avg_response_time, 2),
            },
            "errors": {
                "total": total_errors,
                "error_rate": round((total_errors / total_requests * 100) if total_requests > 0 else 0, 2),
            },
            "users": {
                "unique_active": unique_users,
            },
        }

        logger.info(f"Daily metrics report generated: {report['metrics']}")
        return report

    except Exception as e:
        logger.error(f"Failed to generate daily metrics: {e}")
        raise


# ============================================================================
# Monitoring Tasks
# ============================================================================

@task_with_retry(max_retries=2)
def monitor_task_queue(self) -> Dict[str, Any]:
    """
    Monitor Celery task queue health.

    Checks:
    - Queue lengths
    - Worker availability
    - Stuck tasks

    Returns:
        Queue monitoring results
    """
    logger.info("Monitoring task queue")

    from backend.app.core.celery_app import (
        get_active_tasks,
        get_reserved_tasks,
        get_scheduled_tasks,
        get_worker_stats,
    )

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "active_tasks": len(get_active_tasks()),
        "reserved_tasks": len(get_reserved_tasks()),
        "scheduled_tasks": len(get_scheduled_tasks()),
        "workers": get_worker_stats(),
        "healthy": True,
    }

    # Check for stuck tasks (running > 30 minutes)
    active_tasks = get_active_tasks()
    stuck_tasks = []

    for task in active_tasks:
        if task.get("time_start"):
            start_time = datetime.fromisoformat(task["time_start"])
            duration = (datetime.utcnow() - start_time).total_seconds()

            if duration > 1800:  # 30 minutes
                stuck_tasks.append({
                    "task_id": task["task_id"],
                    "task_name": task["task_name"],
                    "duration_minutes": round(duration / 60, 2),
                })

    if stuck_tasks:
        results["stuck_tasks"] = stuck_tasks
        results["healthy"] = False
        logger.warning(f"Found {len(stuck_tasks)} stuck tasks")

    # Check worker availability
    if not results["workers"]:
        results["healthy"] = False
        logger.error("No active Celery workers found")

    return results


# ============================================================================
# Diagnostic Tasks
# ============================================================================

@celery_app.task(bind=True)
def test_task(self, wait_seconds: int = 5) -> Dict[str, Any]:
    """
    Test task for diagnostics.

    Args:
        wait_seconds: Seconds to wait before completing

    Returns:
        Test results
    """
    import time

    logger.info(f"Test task started: {self.request.id}")

    start = time.time()
    time.sleep(wait_seconds)
    duration = time.time() - start

    result = {
        "task_id": self.request.id,
        "task_name": self.name,
        "wait_seconds": wait_seconds,
        "actual_duration": round(duration, 2),
        "timestamp": datetime.utcnow().isoformat(),
    }

    logger.info(f"Test task completed: {result}")
    return result


@celery_app.task(bind=True)
def test_retry_task(self, max_retries: int = 3) -> Dict[str, Any]:
    """
    Test task that always fails to test retry logic.

    Args:
        max_retries: Maximum retries

    Raises:
        Exception: Always raises to test retry
    """
    logger.warning(f"Test retry task attempt {self.request.retries + 1}/{max_retries}")

    if self.request.retries < max_retries - 1:
        raise Exception(f"Intentional failure (retry {self.request.retries + 1}/{max_retries})")

    return {
        "task_id": self.request.id,
        "total_retries": self.request.retries,
        "timestamp": datetime.utcnow().isoformat(),
        "message": "Task succeeded after retries",
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "health_check",
    "generate_daily_metrics",
    "monitor_task_queue",
    "test_task",
    "test_retry_task",
]
