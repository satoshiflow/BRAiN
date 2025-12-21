"""
Agent Tasks

Background tasks for agent operations:
- Agent heartbeat monitoring
- Agent health checks
- Agent metrics
- Agent cleanup

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
# Agent Monitoring Tasks
# ============================================================================

@task_with_retry(max_retries=2)
def check_agent_heartbeats(self) -> Dict[str, Any]:
    """
    Check agent heartbeats and detect inactive agents.

    Returns:
        Agent heartbeat status
    """
    logger.info("Checking agent heartbeats")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Get all agent heartbeat keys
        agent_keys = loop.run_until_complete(
            redis.keys("brain:agents:*:heartbeat")
        )

        active_agents = []
        inactive_agents = []
        heartbeat_timeout = 60  # 60 seconds

        for key in agent_keys:
            agent_id = key.split(":")[2]
            last_heartbeat = loop.run_until_complete(redis.get(key))

            if last_heartbeat:
                last_heartbeat_time = datetime.fromisoformat(last_heartbeat)
                age = (datetime.utcnow() - last_heartbeat_time).total_seconds()

                if age < heartbeat_timeout:
                    active_agents.append({
                        "agent_id": agent_id,
                        "last_heartbeat": last_heartbeat,
                        "age_seconds": round(age, 2),
                    })
                else:
                    inactive_agents.append({
                        "agent_id": agent_id,
                        "last_heartbeat": last_heartbeat,
                        "age_seconds": round(age, 2),
                    })

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "total_agents": len(agent_keys),
            "active_agents": len(active_agents),
            "inactive_agents": len(inactive_agents),
            "healthy": len(inactive_agents) == 0,
        }

        if inactive_agents:
            results["inactive_details"] = inactive_agents
            logger.warning(f"Found {len(inactive_agents)} inactive agents")

        return results

    except Exception as e:
        logger.error(f"Agent heartbeat check failed: {e}")
        raise


@task_with_retry(max_retries=2)
def cleanup_inactive_agents(self, inactive_threshold_minutes: int = 60) -> Dict[str, int]:
    """
    Clean up inactive agents that haven't sent heartbeat.

    Args:
        inactive_threshold_minutes: Inactivity threshold

    Returns:
        Cleanup statistics
    """
    logger.info(f"Cleaning up agents inactive for > {inactive_threshold_minutes} minutes")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        cutoff_time = datetime.utcnow() - timedelta(minutes=inactive_threshold_minutes)
        cleaned_count = 0

        # Get all agent heartbeat keys
        agent_keys = loop.run_until_complete(
            redis.keys("brain:agents:*:heartbeat")
        )

        for key in agent_keys:
            agent_id = key.split(":")[2]
            last_heartbeat = loop.run_until_complete(redis.get(key))

            if last_heartbeat:
                last_heartbeat_time = datetime.fromisoformat(last_heartbeat)

                if last_heartbeat_time < cutoff_time:
                    # Delete agent data
                    agent_data_key = f"brain:agents:{agent_id}"
                    loop.run_until_complete(redis.delete(agent_data_key))
                    loop.run_until_complete(redis.delete(key))
                    cleaned_count += 1
                    logger.info(f"Cleaned up inactive agent: {agent_id}")

        return {
            "cleaned": cleaned_count,
            "cutoff_time": cutoff_time.isoformat(),
        }

    except Exception as e:
        logger.error(f"Agent cleanup failed: {e}")
        raise


# ============================================================================
# Agent Health Check Tasks
# ============================================================================

@task_with_retry(max_retries=3)
def run_agent_health_check(self, agent_id: str) -> Dict[str, Any]:
    """
    Run health check for specific agent.

    Args:
        agent_id: Agent ID to check

    Returns:
        Agent health status
    """
    logger.info(f"Running health check for agent: {agent_id}")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Get agent data
        agent_data = loop.run_until_complete(
            redis.get(f"brain:agents:{agent_id}")
        )

        if not agent_data:
            return {
                "agent_id": agent_id,
                "healthy": False,
                "reason": "Agent not found",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Get agent heartbeat
        heartbeat = loop.run_until_complete(
            redis.get(f"brain:agents:{agent_id}:heartbeat")
        )

        if heartbeat:
            last_heartbeat_time = datetime.fromisoformat(heartbeat)
            age_seconds = (datetime.utcnow() - last_heartbeat_time).total_seconds()
            healthy = age_seconds < 60
        else:
            age_seconds = None
            healthy = False

        results = {
            "agent_id": agent_id,
            "healthy": healthy,
            "last_heartbeat": heartbeat,
            "heartbeat_age_seconds": round(age_seconds, 2) if age_seconds else None,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if not healthy:
            results["reason"] = "Heartbeat timeout" if heartbeat else "No heartbeat"

        return results

    except Exception as e:
        logger.error(f"Agent health check failed for {agent_id}: {e}")
        raise


@celery_app.task(bind=True)
def run_all_agents_health_check(self) -> Dict[str, Any]:
    """
    Run health check for all registered agents.

    Returns:
        All agents health status
    """
    logger.info("Running health check for all agents")

    try:
        from backend.app.core.redis_client import get_redis_client

        redis = get_redis_client()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Get all agent IDs
        agent_keys = loop.run_until_complete(
            redis.keys("brain:agents:*:heartbeat")
        )

        agent_ids = [key.split(":")[2] for key in agent_keys]

        # Queue health checks for each agent
        results = {
            "total_agents": len(agent_ids),
            "checks_queued": 0,
            "timestamp": datetime.utcnow().isoformat(),
        }

        for agent_id in agent_ids:
            run_agent_health_check.delay(agent_id)
            results["checks_queued"] += 1

        return results

    except Exception as e:
        logger.error(f"Failed to run health checks: {e}")
        raise


# ============================================================================
# Agent Metrics Tasks
# ============================================================================

@task_with_retry(max_retries=2)
def calculate_agent_metrics(self, agent_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Calculate agent performance metrics for date range.

    Args:
        agent_id: Agent ID
        start_date: Start date (ISO format)
        end_date: End date (ISO format)

    Returns:
        Agent metrics
    """
    logger.info(f"Calculating metrics for agent {agent_id}: {start_date} to {end_date}")

    try:
        from backend.app.core.audit import AuditAction, get_audit_logger

        audit_logger = get_audit_logger()

        # Run async operations
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Query agent-related audit logs
        start_time = datetime.fromisoformat(start_date)
        end_time = datetime.fromisoformat(end_date)

        audit_entries = loop.run_until_complete(
            audit_logger.query(
                resource_type="agent",
                resource_id=agent_id,
                start_time=start_time,
                end_time=end_time,
                limit=10000
            )
        )

        # Calculate metrics
        total_actions = len(audit_entries)
        tasks_completed = len([e for e in audit_entries if e.action == AuditAction.UPDATE and e.details.get("status") == "completed"])
        tasks_failed = len([e for e in audit_entries if e.action == AuditAction.UPDATE and e.details.get("status") == "failed"])

        # Calculate average task duration
        task_durations = []
        for entry in audit_entries:
            if entry.details and "duration_ms" in entry.details:
                task_durations.append(entry.details["duration_ms"])

        avg_duration = sum(task_durations) / len(task_durations) if task_durations else 0

        metrics = {
            "agent_id": agent_id,
            "period": {
                "start": start_date,
                "end": end_date,
            },
            "activity": {
                "total_actions": total_actions,
                "tasks_completed": tasks_completed,
                "tasks_failed": tasks_failed,
                "success_rate": round((tasks_completed / total_actions * 100) if total_actions > 0 else 0, 2),
            },
            "performance": {
                "avg_task_duration_ms": round(avg_duration, 2),
                "total_task_duration_ms": sum(task_durations),
            },
            "generated_at": datetime.utcnow().isoformat(),
        }

        logger.info(f"Agent metrics calculated for {agent_id}: {metrics['activity']}")
        return metrics

    except Exception as e:
        logger.error(f"Failed to calculate agent metrics: {e}")
        raise


# ============================================================================
# Agent Task Execution
# ============================================================================

@task_with_retry(max_retries=3)
def execute_agent_task_async(self, agent_id: str, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute agent task asynchronously.

    Args:
        agent_id: Agent ID
        task_data: Task parameters

    Returns:
        Task execution results
    """
    logger.info(f"Executing async task for agent {agent_id}")

    try:
        # Placeholder for agent task execution
        # In production, integrate with agent execution framework

        result = {
            "agent_id": agent_id,
            "task_data": task_data,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat(),
        }

        logger.info(f"Agent task completed: {agent_id}")
        return result

    except Exception as e:
        logger.error(f"Agent task execution failed: {e}")
        raise


@celery_app.task(bind=True)
def execute_agent_batch_tasks(self, agent_id: str, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Execute batch of tasks for agent.

    Args:
        agent_id: Agent ID
        tasks: List of task data

    Returns:
        Batch execution results
    """
    logger.info(f"Executing {len(tasks)} batch tasks for agent {agent_id}")

    results = {
        "agent_id": agent_id,
        "total": len(tasks),
        "queued": 0,
        "failed": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }

    for task_data in tasks:
        try:
            execute_agent_task_async.delay(agent_id=agent_id, task_data=task_data)
            results["queued"] += 1
        except Exception as e:
            logger.error(f"Failed to queue task for agent {agent_id}: {e}")
            results["failed"] += 1

    return results


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "check_agent_heartbeats",
    "cleanup_inactive_agents",
    "run_agent_health_check",
    "run_all_agents_health_check",
    "calculate_agent_metrics",
    "execute_agent_task_async",
    "execute_agent_batch_tasks",
]
