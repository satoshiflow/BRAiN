"""
Maintenance Tasks

Background tasks for system maintenance:
- Audit log cleanup
- Task result cleanup
- Cache cleanup
- Encryption key rotation
- Database maintenance

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
# Cleanup Tasks
# ============================================================================

@task_with_retry(max_retries=2)
def cleanup_audit_logs(self, retention_days: int = 90) -> Dict[str, int]:
    """
    Clean up audit logs older than retention period.

    Args:
        retention_days: Retention period in days (default: 90)

    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up audit logs older than {retention_days} days")

    try:
        from backend.app.core.audit import get_audit_logger

        audit_logger = get_audit_logger()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Cleanup old audit logs
        deleted_count = loop.run_until_complete(
            audit_logger.cleanup_old_logs(days=retention_days)
        )

        logger.info(f"Cleaned up {deleted_count} audit log entries")

        return {
            "deleted": deleted_count,
            "retention_days": retention_days,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Audit log cleanup failed: {e}")
        raise


@task_with_retry(max_retries=2)
def cleanup_task_results(self, days_old: int = 7) -> Dict[str, int]:
    """
    Clean up Celery task results older than specified days.

    Args:
        days_old: Age threshold for cleanup

    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up task results older than {days_old} days")

    try:
        from backend.app.core.celery_app import celery_app
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        cutoff_time = datetime.utcnow() - timedelta(days=days_old)
        cutoff_timestamp = cutoff_time.timestamp()

        # Get all task result keys
        task_keys = loop.run_until_complete(
            redis.keys("celery-task-meta-*")
        )

        deleted_count = 0

        for key in task_keys:
            # Get task result
            task_data = loop.run_until_complete(redis.get(key))

            if task_data:
                import json
                try:
                    task_info = json.loads(task_data)
                    # Check if task is old enough
                    if "date_done" in task_info:
                        done_time = datetime.fromisoformat(task_info["date_done"].replace("Z", "+00:00"))
                        if done_time.timestamp() < cutoff_timestamp:
                            loop.run_until_complete(redis.delete(key))
                            deleted_count += 1
                except (json.JSONDecodeError, ValueError):
                    # Delete invalid task data
                    loop.run_until_complete(redis.delete(key))
                    deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} task results")

        return {
            "deleted": deleted_count,
            "cutoff_date": cutoff_time.isoformat(),
        }

    except Exception as e:
        logger.error(f"Task result cleanup failed: {e}")
        raise


@task_with_retry(max_retries=2)
def cleanup_expired_cache(self) -> Dict[str, int]:
    """
    Clean up expired cache entries.

    Returns:
        Cleanup statistics
    """
    logger.info("Cleaning up expired cache entries")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Get all cache keys
        cache_keys = loop.run_until_complete(
            redis.keys("brain:cache:*")
        )

        deleted_count = 0

        for key in cache_keys:
            # Check TTL
            ttl = loop.run_until_complete(redis.ttl(key))

            # Delete if expired (TTL = -1) or no TTL set (TTL = -2)
            if ttl < 0:
                loop.run_until_complete(redis.delete(key))
                deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} expired cache entries")

        return {
            "deleted": deleted_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        raise


# ============================================================================
# Security Maintenance Tasks
# ============================================================================

@task_with_retry(max_retries=1)
def rotate_encryption_keys(self) -> Dict[str, Any]:
    """
    Rotate encryption keys monthly.

    Returns:
        Key rotation results
    """
    logger.info("Rotating encryption keys")

    try:
        from backend.app.core.encryption import get_encryptor

        encryptor = get_encryptor()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Rotate keys
        rotation_result = loop.run_until_complete(
            encryptor.rotate_key()
        )

        logger.info(f"Encryption keys rotated: {rotation_result}")

        return {
            "rotated": True,
            "old_key_id": rotation_result.get("old_key_id"),
            "new_key_id": rotation_result.get("new_key_id"),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Key rotation failed: {e}")
        raise


@task_with_retry(max_retries=2)
def cleanup_expired_api_keys(self) -> Dict[str, int]:
    """
    Clean up expired API keys.

    Returns:
        Cleanup statistics
    """
    logger.info("Cleaning up expired API keys")

    try:
        from backend.app.core.api_keys import get_api_key_manager

        api_key_manager = get_api_key_manager()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Cleanup expired keys
        deleted_count = loop.run_until_complete(
            api_key_manager.cleanup_expired_keys()
        )

        logger.info(f"Cleaned up {deleted_count} expired API keys")

        return {
            "deleted": deleted_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"API key cleanup failed: {e}")
        raise


@task_with_retry(max_retries=2)
def cleanup_revoked_tokens(self) -> Dict[str, int]:
    """
    Clean up old revoked JWT tokens.

    Returns:
        Cleanup statistics
    """
    logger.info("Cleaning up revoked tokens")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Get all revoked token keys
        token_keys = loop.run_until_complete(
            redis.keys("brain:revoked_tokens:*")
        )

        deleted_count = 0

        for key in token_keys:
            # Check TTL (should auto-expire, but cleanup orphans)
            ttl = loop.run_until_complete(redis.ttl(key))

            if ttl < 0:
                loop.run_until_complete(redis.delete(key))
                deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} revoked tokens")

        return {
            "deleted": deleted_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Revoked token cleanup failed: {e}")
        raise


# ============================================================================
# Database Maintenance Tasks
# ============================================================================

@task_with_retry(max_retries=1)
def vacuum_database(self) -> Dict[str, Any]:
    """
    Run VACUUM on PostgreSQL database to reclaim space.

    Returns:
        Vacuum results
    """
    logger.info("Running database VACUUM")

    try:
        from backend.app.core.database import get_db_engine
        from sqlalchemy import text

        engine = get_db_engine()

        # VACUUM cannot run inside a transaction
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            conn.execute(text("VACUUM ANALYZE"))

        logger.info("Database VACUUM completed")

        return {
            "completed": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Database VACUUM failed: {e}")
        raise


@task_with_retry(max_retries=2)
def analyze_database_tables(self) -> Dict[str, Any]:
    """
    Run ANALYZE on database tables to update statistics.

    Returns:
        Analysis results
    """
    logger.info("Running database ANALYZE")

    try:
        from backend.app.core.database import get_db_engine
        from sqlalchemy import text

        engine = get_db_engine()

        with engine.connect() as conn:
            conn.execute(text("ANALYZE"))

        logger.info("Database ANALYZE completed")

        return {
            "completed": True,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Database ANALYZE failed: {e}")
        raise


# ============================================================================
# System Optimization Tasks
# ============================================================================

@task_with_retry(max_retries=2)
def optimize_redis_memory(self) -> Dict[str, Any]:
    """
    Optimize Redis memory usage.

    Returns:
        Optimization results
    """
    logger.info("Optimizing Redis memory")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Get memory info before
        info_before = loop.run_until_complete(redis.info("memory"))
        memory_before = info_before.get("used_memory_human", "unknown")

        # Run Redis memory optimization
        # Delete keys with no TTL (potential memory leaks)
        all_keys = loop.run_until_complete(redis.keys("*"))
        deleted_count = 0

        for key in all_keys:
            ttl = loop.run_until_complete(redis.ttl(key))
            # Delete keys with no expiration that look like temporary data
            if ttl == -1 and any(pattern in key for pattern in ["temp:", "session:", "lock:"]):
                loop.run_until_complete(redis.delete(key))
                deleted_count += 1

        # Get memory info after
        info_after = loop.run_until_complete(redis.info("memory"))
        memory_after = info_after.get("used_memory_human", "unknown")

        logger.info(f"Redis memory optimization completed: {memory_before} -> {memory_after}")

        return {
            "memory_before": memory_before,
            "memory_after": memory_after,
            "keys_deleted": deleted_count,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Redis memory optimization failed: {e}")
        raise


@celery_app.task(bind=True)
def full_system_maintenance(self) -> Dict[str, Any]:
    """
    Run comprehensive system maintenance (all tasks).

    Returns:
        Maintenance results
    """
    logger.info("Running full system maintenance")

    results = {
        "started_at": datetime.utcnow().isoformat(),
        "tasks": {},
    }

    # Queue all maintenance tasks
    tasks = [
        ("cleanup_audit_logs", cleanup_audit_logs.delay()),
        ("cleanup_task_results", cleanup_task_results.delay()),
        ("cleanup_expired_cache", cleanup_expired_cache.delay()),
        ("cleanup_expired_api_keys", cleanup_expired_api_keys.delay()),
        ("cleanup_revoked_tokens", cleanup_revoked_tokens.delay()),
        ("optimize_redis_memory", optimize_redis_memory.delay()),
        ("analyze_database_tables", analyze_database_tables.delay()),
    ]

    for task_name, task_result in tasks:
        results["tasks"][task_name] = {
            "task_id": task_result.id,
            "status": "queued",
        }

    results["completed_at"] = datetime.utcnow().isoformat()
    logger.info(f"Full system maintenance queued: {len(tasks)} tasks")

    return results


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "cleanup_audit_logs",
    "cleanup_task_results",
    "cleanup_expired_cache",
    "rotate_encryption_keys",
    "cleanup_expired_api_keys",
    "cleanup_revoked_tokens",
    "vacuum_database",
    "analyze_database_tables",
    "optimize_redis_memory",
    "full_system_maintenance",
]
