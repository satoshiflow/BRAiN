"""
NeuroRail Telemetry Service.

Provides metrics collection and aggregation with:
- Prometheus metrics export
- Redis storage for real-time snapshots
- PostgreSQL snapshots for historical analysis
"""

from __future__ import annotations
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.redis_client import get_redis
from backend.app.core.metrics import (
    record_neurorail_attempt,
    record_neurorail_budget_violation,
    record_neurorail_reflex,
    update_neurorail_gauges,
    record_neurorail_ttfs,
)
from backend.app.modules.neurorail.telemetry.schemas import (
    ExecutionMetrics,
    AggregatedMetrics,
    RealtimeSnapshot,
)


class TelemetryService:
    """
    Service for collecting and aggregating NeuroRail execution metrics.

    Responsibilities:
    - Record execution metrics to Redis (hot data)
    - Emit Prometheus metrics
    - Periodic snapshots to PostgreSQL (historical data)
    - Provide real-time aggregations
    """

    # Redis key prefixes
    KEY_PREFIX_METRICS = "neurorail:metrics:"
    KEY_PREFIX_SNAPSHOT = "neurorail:snapshot:current"

    def __init__(self):
        self.redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get Redis client (lazy initialization)."""
        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    # ========================================================================
    # Metrics Collection
    # ========================================================================

    async def record_execution(
        self,
        metrics: ExecutionMetrics
    ) -> None:
        """
        Record execution metrics.

        Args:
            metrics: Execution metrics to record
        """
        # 1. Store in Redis (24h TTL)
        await self._store_metrics_redis(metrics)

        # 2. Emit Prometheus metrics
        self._emit_prometheus_metrics(metrics)

        logger.debug(
            f"Telemetry recorded: {metrics.entity_type} {metrics.entity_id} "
            f"(duration: {metrics.duration_ms}ms, success: {metrics.success})"
        )

    async def _store_metrics_redis(self, metrics: ExecutionMetrics) -> None:
        """Store metrics in Redis with 24h TTL."""
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_METRICS}{metrics.entity_id}"

        # Serialize to JSON
        data = metrics.model_dump()
        data["started_at"] = metrics.started_at.isoformat()
        if metrics.completed_at:
            data["completed_at"] = metrics.completed_at.isoformat()

        await redis_client.hset(key, mapping={
            "metrics": json.dumps(data)
        })
        await redis_client.expire(key, 24 * 60 * 60)  # 24h TTL

    def _emit_prometheus_metrics(self, metrics: ExecutionMetrics) -> None:
        """Emit metrics to Prometheus."""
        if not metrics.completed_at:
            return  # Only emit completed metrics

        # Determine status
        if metrics.success:
            status = "success"
        elif metrics.error_category == "ethical":
            status = "failed_ethical"
        elif metrics.error_category == "mechanical":
            status = "failed_mechanical"
        elif "timeout" in (metrics.error_type or "").lower():
            status = "failed_timeout"
        else:
            status = "failed_mechanical"

        # Record attempt
        record_neurorail_attempt(
            entity_type=metrics.entity_type,
            status=status,
            duration_ms=metrics.duration_ms or 0.0,
            error_category=metrics.error_category,
            error_code=metrics.error_type
        )

    # ========================================================================
    # Metrics Retrieval
    # ========================================================================

    async def get_execution_metrics(
        self,
        entity_id: str
    ) -> Optional[ExecutionMetrics]:
        """
        Get execution metrics for an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            Execution metrics or None if not found
        """
        redis_client = await self._get_redis()
        key = f"{self.KEY_PREFIX_METRICS}{entity_id}"

        data = await redis_client.hget(key, "metrics")
        if not data:
            return None

        metrics_dict = json.loads(data)
        metrics_dict["started_at"] = datetime.fromisoformat(metrics_dict["started_at"])
        if metrics_dict.get("completed_at"):
            metrics_dict["completed_at"] = datetime.fromisoformat(metrics_dict["completed_at"])

        return ExecutionMetrics(**metrics_dict)

    # ========================================================================
    # Real-Time Snapshot
    # ========================================================================

    async def update_snapshot(
        self,
        active_missions: int,
        active_jobs: int,
        active_attempts: int,
        pending_missions: int = 0,
        pending_jobs: int = 0
    ) -> RealtimeSnapshot:
        """
        Update real-time system snapshot.

        Args:
            active_missions: Number of active missions
            active_jobs: Number of active jobs
            active_attempts: Number of active attempts
            pending_missions: Number of pending missions
            pending_jobs: Number of pending jobs

        Returns:
            Updated snapshot
        """
        # Update Prometheus gauges
        update_neurorail_gauges(active_missions, active_jobs, active_attempts)

        # Create snapshot
        snapshot = RealtimeSnapshot(
            active_missions=active_missions,
            active_jobs=active_jobs,
            active_attempts=active_attempts,
            pending_missions=pending_missions,
            pending_jobs=pending_jobs,
        )

        # Store in Redis
        redis_client = await self._get_redis()
        await redis_client.hset(
            self.KEY_PREFIX_SNAPSHOT,
            mapping={
                "data": json.dumps(snapshot.model_dump()),
                "updated_at": datetime.utcnow().isoformat()
            }
        )

        return snapshot

    async def get_snapshot(self) -> Optional[RealtimeSnapshot]:
        """
        Get current real-time snapshot.

        Returns:
            Current snapshot or None if not available
        """
        redis_client = await self._get_redis()
        data = await redis_client.hget(self.KEY_PREFIX_SNAPSHOT, "data")

        if not data:
            return None

        snapshot_dict = json.loads(data)
        snapshot_dict["timestamp"] = datetime.fromisoformat(snapshot_dict["timestamp"])

        return RealtimeSnapshot(**snapshot_dict)

    # ========================================================================
    # PostgreSQL Snapshots (Historical Data)
    # ========================================================================

    async def create_snapshot(
        self,
        metrics: ExecutionMetrics,
        db: AsyncSession
    ) -> None:
        """
        Create a metrics snapshot in PostgreSQL for historical analysis.

        Args:
            metrics: Metrics to snapshot
            db: Database session
        """
        query = text("""
            INSERT INTO neurorail_metrics_snapshots
                (snapshot_id, timestamp, entity_id, entity_type, metrics, created_at)
            VALUES
                (:snapshot_id, :timestamp, :entity_id, :entity_type, :metrics, NOW())
        """)

        # Serialize metrics
        metrics_dict = metrics.model_dump()
        metrics_dict["started_at"] = metrics.started_at.isoformat()
        if metrics.completed_at:
            metrics_dict["completed_at"] = metrics.completed_at.isoformat()

        snapshot_id = f"snap_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        await db.execute(query, {
            "snapshot_id": snapshot_id,
            "timestamp": datetime.utcnow(),
            "entity_id": metrics.entity_id,
            "entity_type": metrics.entity_type,
            "metrics": json.dumps(metrics_dict),
        })
        await db.commit()

    # ========================================================================
    # Special Metrics
    # ========================================================================

    def record_budget_violation(self, resource_type: str) -> None:
        """
        Record a budget violation (Phase 2).

        Args:
            resource_type: time, tokens, memory, etc.
        """
        record_neurorail_budget_violation(resource_type)

    def record_reflex_action(self, reflex_type: str, action: str) -> None:
        """
        Record a reflex system action (Phase 2).

        Args:
            reflex_type: cooldown, suspend, throttle, etc.
            action: cancel, pause, alert, etc.
        """
        record_neurorail_reflex(reflex_type, action)

    def record_ttfs(self, job_type: str, ttfs_ms: float) -> None:
        """
        Record Time to First Signal (TTFS).

        Args:
            job_type: llm_call, tool_execution, etc.
            ttfs_ms: Time to first signal in milliseconds
        """
        record_neurorail_ttfs(job_type, ttfs_ms)


# Singleton instance
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service() -> TelemetryService:
    """Get singleton telemetry service instance."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService()
    return _telemetry_service
