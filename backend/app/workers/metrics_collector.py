"""
Metrics collection background worker for cluster system.

This worker periodically collects metrics for all active clusters
and stores them in the cluster_metrics table for auto-scaling decisions.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from app.modules.cluster_system.service import ClusterService
from app.modules.cluster_system.models import Cluster, ClusterStatus, ClusterAgent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.db import get_session

logger = logging.getLogger(__name__)


class MetricsCollectorWorker:
    """Background worker that collects metrics for all active clusters."""

    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval  # seconds
        self.running = False
        self.service = None

    async def start(self):
        """Start the metrics collection loop."""
        self.running = True
        logger.info(f"📊 Metrics Collector started (interval: {self.collection_interval}s)")

        while self.running:
            try:
                await self._collect_all_metrics()
            except Exception as e:
                logger.error(f"❌ Error in metrics collection loop: {e}", exc_info=True)

            await asyncio.sleep(self.collection_interval)

    async def _collect_all_metrics(self):
        """Collect metrics for all active clusters."""
        from sqlalchemy.exc import ProgrammingError

        try:
            async with get_session() as db:
                self.service = ClusterService(db)

                # Get all active clusters
                try:
                    result = await db.execute(
                        select(Cluster).where(Cluster.status == ClusterStatus.ACTIVE)
                    )
                    clusters = result.scalars().all()
                except ProgrammingError as e:
                    if "relation \"clusters\" does not exist" in str(e):
                        logger.warning("⚠️  Cluster table not found. Migration may be missing. Skipping metrics collection.")
                        return
                    raise

                if clusters:
                    logger.debug(f"📊 Collecting metrics for {len(clusters)} active clusters")

                for cluster in clusters:
                    try:
                        metrics = await self._collect_cluster_metrics(db, cluster)
                        await self.service.record_metrics(cluster.id, metrics)
                        logger.debug(f"✅ Recorded metrics for cluster {cluster.id}")
                    except Exception as e:
                        logger.error(f"❌ Error collecting metrics for cluster {cluster.id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"❌ Error in metrics collection loop: {e}", exc_info=True)

    async def _collect_cluster_metrics(self, db: AsyncSession, cluster: Cluster) -> Dict[str, Any]:
        """
        Collect current metrics for a cluster.

        Metrics collected:
        - CPU usage (simulated based on load)
        - Memory usage (simulated)
        - Task queue length (simulated)
        - Agent counts by status
        - Performance metrics
        """
        # Get agent counts by status
        result = await db.execute(
            select(
                ClusterAgent.status,
                func.count(ClusterAgent.id).label("count")
            ).where(
                ClusterAgent.cluster_id == cluster.id
            ).group_by(ClusterAgent.status)
        )

        status_counts = {row.status: row.count for row in result}

        active_agents = status_counts.get("active", 0)
        idle_agents = status_counts.get("idle", 0)
        busy_agents = status_counts.get("busy", 0)
        failed_agents = status_counts.get("failed", 0) + status_counts.get("spawn_failed", 0)

        # Calculate derived metrics
        total_agents = active_agents + idle_agents + busy_agents

        # Simulate load-based metrics (in production, these would come from real monitoring)
        # For now, use cluster load_percentage if available
        load = cluster.load_percentage or 0.0

        # CPU usage: correlates with load (0-100%)
        cpu_usage = min(load * 1.2, 100.0)

        # Memory usage: assume ~70% baseline + load factor
        memory_usage = min(70.0 + (load * 0.3), 100.0)

        # Task queue length: simulated based on load
        # High load = more tasks queued
        if load > 80:
            queue_length = int((load - 80) * 2)  # 0-40 tasks
        elif load > 50:
            queue_length = int((load - 50) / 5)  # 0-6 tasks
        else:
            queue_length = 0

        # Queue wait time: increases with queue length
        queue_wait_time = queue_length * 2.5 if queue_length > 0 else 0.0  # seconds

        # Tasks per minute: estimate based on active agents and load
        tasks_per_minute = active_agents * (load / 100.0) * 10 if active_agents > 0 else 0.0

        # Average response time: increases with load
        avg_response_time = 100 + (load * 5)  # 100-600ms

        # Error rate: increases slightly with high load
        error_rate = min(load / 20, 5.0) if load > 80 else 0.0  # 0-5%

        metrics = {
            "timestamp": datetime.utcnow(),
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "tasks_per_minute": tasks_per_minute,
            "avg_response_time": avg_response_time,
            "error_rate": error_rate,
            "active_agents": active_agents,
            "idle_agents": idle_agents,
            "busy_agents": busy_agents,
            "failed_agents": failed_agents,
            "queue_length": queue_length,
            "queue_wait_time": queue_wait_time
        }

        return metrics

    def stop(self):
        """Stop the metrics collection loop."""
        self.running = False
        logger.info("🛑 Metrics Collector stopped")


# Singleton instance
_metrics_collector = None


async def start_metrics_collector(collection_interval: int = 30):
    """Start the global metrics collector worker."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollectorWorker(collection_interval)
        await _metrics_collector.start()


def stop_metrics_collector():
    """Stop the global metrics collector worker."""
    global _metrics_collector
    if _metrics_collector:
        _metrics_collector.stop()
        _metrics_collector = None
