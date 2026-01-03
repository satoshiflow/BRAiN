"""
Approval Cleanup Worker - Sprint 11

Background worker for approval maintenance tasks:
1. Cleanup expired approval references in Redis tenant indices
2. Emit statistics for monitoring
3. Audit log cleanup events

Redis TTL handles automatic deletion of approval keys,
but tenant index sets need manual cleanup.

Runs periodically (default: every 5 minutes).
"""

import asyncio
from typing import Optional
from datetime import datetime
from loguru import logger

from app.modules.ir_governance.redis_approval_store import RedisApprovalStore
from app.modules.ir_governance.approvals import ApprovalsService


class ApprovalCleanupWorker:
    """
    Background worker for approval cleanup.

    Tasks:
    - Cleanup expired approval references in tenant indices
    - Emit cleanup statistics
    - Log cleanup events for audit

    Interval: 5 minutes (configurable)
    """

    DEFAULT_INTERVAL_SECONDS = 300  # 5 minutes

    def __init__(
        self,
        approvals_service: ApprovalsService,
        interval_seconds: Optional[int] = None
    ):
        """
        Initialize cleanup worker.

        Args:
            approvals_service: Approvals service with RedisApprovalStore
            interval_seconds: Cleanup interval in seconds (default: 300)
        """
        self.approvals_service = approvals_service
        self.interval_seconds = interval_seconds or self.DEFAULT_INTERVAL_SECONDS
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.stats = {
            "runs": 0,
            "total_cleaned": 0,
            "last_run": None,
            "last_cleaned": 0,
            "last_duration_ms": 0,
        }

    async def start(self):
        """Start cleanup worker background task."""
        if self.running:
            logger.warning("[ApprovalCleanupWorker] Already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info(
            f"[ApprovalCleanupWorker] Started (interval={self.interval_seconds}s)"
        )

    async def stop(self):
        """Stop cleanup worker gracefully."""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("[ApprovalCleanupWorker] Stopped")

    async def _run_loop(self):
        """Main worker loop."""
        while self.running:
            try:
                await self._run_cleanup()
            except Exception as e:
                logger.error(f"[ApprovalCleanupWorker] Cleanup failed: {e}")

            # Sleep until next run
            await asyncio.sleep(self.interval_seconds)

    async def _run_cleanup(self):
        """Run cleanup cycle."""
        start_time = datetime.utcnow()
        start_ms = asyncio.get_event_loop().time() * 1000

        # Check if store is Redis-based
        store = self.approvals_service.store
        if not isinstance(store, RedisApprovalStore):
            # In-memory store doesn't need cleanup worker
            # (uses cleanup_expired() method instead)
            logger.debug(
                "[ApprovalCleanupWorker] Skipping cleanup (not using RedisApprovalStore)"
            )
            return

        # Run cleanup
        cleaned = await store.cleanup_expired_indices()

        # Calculate duration
        end_ms = asyncio.get_event_loop().time() * 1000
        duration_ms = int(end_ms - start_ms)

        # Update stats
        self.stats["runs"] += 1
        self.stats["total_cleaned"] += cleaned
        self.stats["last_run"] = start_time.isoformat()
        self.stats["last_cleaned"] = cleaned
        self.stats["last_duration_ms"] = duration_ms

        # Log cleanup event
        if cleaned > 0:
            logger.info(
                f"[ApprovalCleanupWorker] ir.approval_cleanup_completed: "
                f"cleaned={cleaned}, duration={duration_ms}ms, "
                f"total_cleaned={self.stats['total_cleaned']}, runs={self.stats['runs']}"
            )
        else:
            logger.debug(
                f"[ApprovalCleanupWorker] Cleanup completed: "
                f"cleaned=0, duration={duration_ms}ms"
            )

    def get_stats(self) -> dict:
        """
        Get cleanup worker statistics.

        Returns:
            Dict with cleanup stats
        """
        return {
            **self.stats,
            "running": self.running,
            "interval_seconds": self.interval_seconds,
        }

    async def health_check(self) -> dict:
        """
        Health check for cleanup worker.

        Returns:
            Dict with health status
        """
        # Check if worker is running
        if not self.running:
            return {
                "healthy": False,
                "status": "stopped",
                "message": "Cleanup worker is not running",
            }

        # Check Redis health (if using RedisApprovalStore)
        store = self.approvals_service.store
        if isinstance(store, RedisApprovalStore):
            redis_healthy = await store.health_check()
            if not redis_healthy:
                return {
                    "healthy": False,
                    "status": "redis_unhealthy",
                    "message": "Redis connection is unhealthy",
                    "stats": self.get_stats(),
                }

        # Check if cleanup is running regularly
        last_run = self.stats.get("last_run")
        if last_run:
            last_run_dt = datetime.fromisoformat(last_run)
            time_since_last_run = (datetime.utcnow() - last_run_dt).total_seconds()

            # If last run was more than 2x interval ago, something is wrong
            if time_since_last_run > self.interval_seconds * 2:
                return {
                    "healthy": False,
                    "status": "stale",
                    "message": f"No cleanup in {int(time_since_last_run)}s (expected {self.interval_seconds}s)",
                    "stats": self.get_stats(),
                }

        return {
            "healthy": True,
            "status": "running",
            "message": "Cleanup worker is healthy",
            "stats": self.get_stats(),
        }


# Singleton
_cleanup_worker: Optional[ApprovalCleanupWorker] = None


def get_cleanup_worker() -> Optional[ApprovalCleanupWorker]:
    """Get singleton cleanup worker (may be None if not started)."""
    global _cleanup_worker
    return _cleanup_worker


async def start_cleanup_worker(
    approvals_service: ApprovalsService,
    interval_seconds: Optional[int] = None
) -> ApprovalCleanupWorker:
    """
    Start cleanup worker singleton.

    Args:
        approvals_service: Approvals service
        interval_seconds: Cleanup interval (default: 300s = 5min)

    Returns:
        ApprovalCleanupWorker instance
    """
    global _cleanup_worker

    if _cleanup_worker is not None and _cleanup_worker.running:
        logger.warning("[ApprovalCleanupWorker] Already running")
        return _cleanup_worker

    _cleanup_worker = ApprovalCleanupWorker(approvals_service, interval_seconds)
    await _cleanup_worker.start()
    return _cleanup_worker


async def stop_cleanup_worker():
    """Stop cleanup worker singleton."""
    global _cleanup_worker

    if _cleanup_worker:
        await _cleanup_worker.stop()
        _cleanup_worker = None
