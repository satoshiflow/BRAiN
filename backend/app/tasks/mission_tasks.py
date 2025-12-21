"""
Mission Tasks

Background tasks for mission operations:
- Mission queue health monitoring
- Mission cleanup
- Mission metrics
- Mission notifications

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List

from loguru import logger

from backend.app.core.celery_app import celery_app, task_with_retry


# ============================================================================
# Mission Queue Tasks
# ============================================================================

@task_with_retry(max_retries=2)
def check_mission_queue_health(self) -> Dict[str, Any]:
    """
    Check mission queue health and alert on issues.

    Checks:
    - Queue depth
    - Stuck missions
    - Failed missions

    Returns:
        Queue health status
    """
    logger.info("Checking mission queue health")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Get queue size
        queue_size = loop.run_until_complete(
            redis.zcard("brain:missions:queue")
        )

        # Get stuck missions (in queue > 1 hour)
        one_hour_ago = datetime.utcnow().timestamp() - 3600
        stuck_missions = loop.run_until_complete(
            redis.zrangebyscore(
                "brain:missions:queue",
                "-inf",
                one_hour_ago,
                withscores=True
            )
        )

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "queue_size": queue_size,
            "stuck_missions": len(stuck_missions) if stuck_missions else 0,
            "healthy": True,
        }

        # Alert if queue too large
        if queue_size > 1000:
            results["healthy"] = False
            results["alert"] = f"Queue size exceeds threshold: {queue_size} > 1000"
            logger.warning(results["alert"])

        # Alert if stuck missions
        if stuck_missions:
            results["healthy"] = False
            results["alert"] = f"Found {len(stuck_missions)} stuck missions"
            logger.warning(results["alert"])

        return results

    except Exception as e:
        logger.error(f"Mission queue health check failed: {e}")
        raise


@task_with_retry(max_retries=3)
def cleanup_completed_missions(self, days_old: int = 30) -> Dict[str, int]:
    """
    Clean up completed missions older than specified days.

    Args:
        days_old: Age threshold for cleanup

    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up missions older than {days_old} days")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        cutoff_time = datetime.utcnow() - timedelta(days=days_old)
        cutoff_timestamp = cutoff_time.timestamp()

        # Get old completed mission IDs
        old_missions = loop.run_until_complete(
            redis.zrangebyscore(
                "brain:missions:completed",
                "-inf",
                cutoff_timestamp
            )
        )

        deleted_count = 0

        if old_missions:
            # Delete mission data
            for mission_id in old_missions:
                mission_key = f"brain:missions:{mission_id}"
                loop.run_until_complete(redis.delete(mission_key))
                deleted_count += 1

            # Remove from completed set
            loop.run_until_complete(
                redis.zremrangebyscore(
                    "brain:missions:completed",
                    "-inf",
                    cutoff_timestamp
                )
            )

        logger.info(f"Cleaned up {deleted_count} old missions")

        return {
            "deleted": deleted_count,
            "cutoff_date": cutoff_time.isoformat(),
        }

    except Exception as e:
        logger.error(f"Mission cleanup failed: {e}")
        raise


@task_with_retry(max_retries=2)
def process_mission_async(self, mission_id: str) -> Dict[str, Any]:
    """
    Process a mission asynchronously in background.

    Args:
        mission_id: Mission ID to process

    Returns:
        Mission execution results
    """
    logger.info(f"Processing mission asynchronously: {mission_id}")

    try:
        from backend.app.modules.missions.service import MissionService

        service = MissionService()

        # Run async mission processing
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            service.execute_mission(mission_id)
        )

        logger.info(f"Mission {mission_id} completed successfully")
        return result

    except Exception as e:
        logger.error(f"Mission {mission_id} processing failed: {e}")
        raise


# ============================================================================
# Mission Metrics Tasks
# ============================================================================

@task_with_retry(max_retries=2)
def calculate_mission_metrics(self, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Calculate mission execution metrics for date range.

    Args:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        Mission metrics
    """
    logger.info(f"Calculating mission metrics: {start_date} to {end_date}")

    try:
        from backend.app.core.audit import AuditAction, get_audit_logger

        audit_logger = get_audit_logger()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Query mission-related audit logs
        start_time = datetime.fromisoformat(start_date)
        end_time = datetime.fromisoformat(end_date)

        audit_entries = loop.run_until_complete(
            audit_logger.query(
                resource_type="mission",
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
        )

        # Calculate metrics
        total_missions = len([e for e in audit_entries if e.action == AuditAction.CREATE])
        completed_missions = len([e for e in audit_entries if e.action == AuditAction.UPDATE and e.details.get("status") == "completed"])
        failed_missions = len([e for e in audit_entries if e.action == AuditAction.UPDATE and e.details.get("status") == "failed"])

        # Calculate average execution time
        execution_times = []
        for entry in audit_entries:
            if entry.details and "execution_time_ms" in entry.details:
                execution_times.append(entry.details["execution_time_ms"])

        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0

        metrics = {
            "period": {
                "start": start_date,
                "end": end_date,
            },
            "missions": {
                "total": total_missions,
                "completed": completed_missions,
                "failed": failed_missions,
                "success_rate": round((completed_missions / total_missions * 100) if total_missions > 0 else 0, 2),
            },
            "performance": {
                "avg_execution_time_ms": round(avg_execution_time, 2),
                "total_execution_time_ms": sum(execution_times),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Mission metrics calculated: {metrics['missions']}")
        return metrics

    except Exception as e:
        logger.error(f"Failed to calculate mission metrics: {e}")
        raise


# ============================================================================
# Mission Notification Tasks
# ============================================================================

@task_with_retry(max_retries=3)
def send_mission_notification(
    self,
    mission_id: str,
    status: str,
    recipients: List[str],
    notification_type: str = "email"
) -> Dict[str, Any]:
    """
    Send mission status notification.

    Args:
        mission_id: Mission ID
        status: Mission status (completed, failed, etc.)
        recipients: List of recipient IDs or emails
        notification_type: Notification channel (email, webhook, etc.)

    Returns:
        Notification results
    """
    logger.info(f"Sending mission notification: {mission_id} - {status}")

    try:
        # Placeholder for notification logic
        # In production, integrate with email service, webhooks, etc.

        notification_data = {
            "mission_id": mission_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "recipients": recipients,
            "notification_type": notification_type,
        }

        # Simulate notification sending
        logger.info(f"Notification sent: {notification_data}")

        return {
            "sent": True,
            "recipients_count": len(recipients),
            "notification_type": notification_type,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Failed to send mission notification: {e}")
        raise


@celery_app.task(bind=True)
def send_mission_batch_notification(
    self,
    mission_ids: List[str],
    status: str,
    recipients: List[str]
) -> Dict[str, Any]:
    """
    Send batch notification for multiple missions.

    Args:
        mission_ids: List of mission IDs
        status: Mission status
        recipients: List of recipients

    Returns:
        Batch notification results
    """
    logger.info(f"Sending batch notification for {len(mission_ids)} missions")

    results = {
        "total": len(mission_ids),
        "sent": 0,
        "failed": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    for mission_id in mission_ids:
        try:
            send_mission_notification.delay(
                mission_id=mission_id,
                status=status,
                recipients=recipients
            )
            results["sent"] += 1
        except Exception as e:
            logger.error(f"Failed to queue notification for {mission_id}: {e}")
            results["failed"] += 1

    return results


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "check_mission_queue_health",
    "cleanup_completed_missions",
    "process_mission_async",
    "calculate_mission_metrics",
    "send_mission_notification",
    "send_mission_batch_notification",
]
