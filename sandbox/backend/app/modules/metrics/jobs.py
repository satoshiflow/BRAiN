from datetime import datetime, timedelta
import json
import time
from typing import Optional

import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.core.redis_client import get_redis

# Optional metrics import
try:
    from app.core.metrics import inc_counter
except ImportError:
    # Stub function if metrics module not available
    def inc_counter(metric_name: str, tags: dict = None):
        """Stub function - metrics module not available"""
        pass

# EventStream integration (Sprint 4)
try:
    from mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None
    import warnings
    warnings.warn(
        "[MetricsService] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )

# Module-level EventStream (functional architecture pattern)
_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
    """
    Set the EventStream instance (called at startup).

    Sprint 4 EventStream Integration.
    """
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """
    Emit metrics event with error handling (non-blocking).

    Charter v1.0 Compliance:
    - Event publishing MUST NOT block business logic
    - Failures are logged but NOT raised
    - Graceful degradation when EventStream unavailable
    """
    global _event_stream

    if _event_stream is None or Event is None:
        logger.debug("[MetricsService] EventStream not available, skipping event: %s", event_type)
        return

    try:
        # Create and publish event
        event = Event(
            type=event_type,
            source="metrics_service",
            target=None,
            payload=payload,
        )

        await _event_stream.publish(event)

        logger.debug(
            "[MetricsService] Event published: %s",
            event_type,
        )

    except Exception as e:
        logger.error(
            "[MetricsService] Event publishing failed: %s (event_type=%s)",
            e,
            event_type,
            exc_info=True,
        )
        # DO NOT raise - business logic must continue


async def aggregate_mission_metrics():
    """
    Aggregate mission metrics from Redis streams.

    Sprint 4 EventStream Integration:
    - metrics.aggregation_started: Job started
    - metrics.aggregation_completed: Job completed successfully
    - metrics.aggregation_failed: Job failed with error
    """
    job_id = "aggregate_mission_metrics"
    start_time = time.time()

    # EVENT: metrics.aggregation_started
    await _emit_event_safe(
        event_type="metrics.aggregation_started",
        payload={
            "job_id": job_id,
            "started_at": start_time,
        }
    )

    try:
        client: redis.Redis = get_redis()
        entries = client.xrevrange("brain.events.missions", count=500)

        entries_processed = 0

        for _id, fields in entries:
            try:
                data = json.loads(fields[b"data"].decode("utf-8"))
                status = data.get("status")
                inc_counter("mission_status_total", {"status": status})
                entries_processed += 1
            except Exception:
                continue

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # EVENT: metrics.aggregation_completed
        await _emit_event_safe(
            event_type="metrics.aggregation_completed",
            payload={
                "job_id": job_id,
                "entries_processed": entries_processed,
                "duration_ms": duration_ms,
                "completed_at": time.time(),
            }
        )

    except Exception as e:
        # EVENT: metrics.aggregation_failed
        await _emit_event_safe(
            event_type="metrics.aggregation_failed",
            payload={
                "job_id": job_id,
                "error_message": str(e),
                "error_type": type(e).__name__,
                "failed_at": time.time(),
            }
        )
        # Re-raise so scheduler knows job failed
        raise


def register_jobs(scheduler: AsyncIOScheduler):
    """Register periodic jobs with scheduler."""
    scheduler.add_job(
        aggregate_mission_metrics,
        "interval",
        seconds=30,
        id="aggregate_mission_metrics",
    )
