"""
Snapshot Scheduler - Automatic Periodic Snapshots.

Provides automatic snapshot creation based on:
- Time-based triggers (e.g., every N minutes)
- Event-based triggers (e.g., every N events)
- Hybrid triggers (both time and event count)

Design:
- Background async task
- Configurable via environment variables
- Automatic retention policy enforcement
- Graceful shutdown support
- Error resilience (continues on failures)

Configuration (Environment Variables):
    SNAPSHOT_ENABLED: Enable automatic snapshots (default: True)
    SNAPSHOT_INTERVAL_MINUTES: Time between snapshots (default: 60)
    SNAPSHOT_EVENT_THRESHOLD: Create snapshot every N events (default: 1000)
    SNAPSHOT_RETENTION_COUNT: Number of snapshots to keep (default: 10)

Usage:
    # Start scheduler as background task
    scheduler = SnapshotScheduler()
    await scheduler.start()

    # ... application runs ...

    # Stop scheduler gracefully
    await scheduler.stop()

Integration with FastAPI:
    # In app lifecycle
    @app.on_event("startup")
    async def startup():
        scheduler = get_snapshot_scheduler()
        await scheduler.start()

    @app.on_event("shutdown")
    async def shutdown():
        scheduler = get_snapshot_scheduler()
        await scheduler.stop()
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from backend.app.modules.credits.event_sourcing.base_journal import BaseEventJournal
from backend.app.modules.credits.event_sourcing.projections import ProjectionManager
from backend.app.modules.credits.event_sourcing.snapshot_manager import SnapshotManager


class SnapshotSchedulerConfig:
    """Configuration for SnapshotScheduler."""

    def __init__(self):
        """Load configuration from environment variables."""
        self.enabled = os.getenv("SNAPSHOT_ENABLED", "true").lower() == "true"
        self.interval_minutes = int(os.getenv("SNAPSHOT_INTERVAL_MINUTES", "60"))
        self.event_threshold = int(os.getenv("SNAPSHOT_EVENT_THRESHOLD", "1000"))
        self.retention_count = int(os.getenv("SNAPSHOT_RETENTION_COUNT", "10"))
        self.check_interval_seconds = int(
            os.getenv("SNAPSHOT_CHECK_INTERVAL_SECONDS", "60")
        )

    def __repr__(self) -> str:
        return (
            f"SnapshotSchedulerConfig("
            f"enabled={self.enabled}, "
            f"interval_minutes={self.interval_minutes}, "
            f"event_threshold={self.event_threshold}, "
            f"retention_count={self.retention_count})"
        )


class SnapshotScheduler:
    """
    Automatic snapshot scheduler with time and event-based triggers.

    Features:
    - Time-based snapshots (every N minutes)
    - Event-based snapshots (every N events)
    - Automatic retention policy (keep last N snapshots)
    - Background async task
    - Graceful shutdown
    - Error resilience

    Example:
        >>> scheduler = SnapshotScheduler()
        >>> await scheduler.start()  # Starts background task
        >>> # ... application runs ...
        >>> await scheduler.stop()  # Graceful shutdown
    """

    def __init__(
        self,
        journal: Optional[BaseEventJournal] = None,
        projection_manager: Optional[ProjectionManager] = None,
        snapshot_manager: Optional[SnapshotManager] = None,
        config: Optional[SnapshotSchedulerConfig] = None,
    ):
        """
        Initialize SnapshotScheduler.

        Args:
            journal: BaseEventJournal (optional, uses singleton if not provided)
            projection_manager: ProjectionManager (optional, uses singleton)
            snapshot_manager: SnapshotManager (optional, uses singleton)
            config: SnapshotSchedulerConfig (optional, uses env vars)
        """
        self.journal = journal
        self.projection_manager = projection_manager
        self.snapshot_manager = snapshot_manager
        self.config = config or SnapshotSchedulerConfig()

        # Scheduler state
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_snapshot_time: Optional[datetime] = None
        self._last_snapshot_event_count: int = 0
        self._current_event_count: int = 0

        # Metrics
        self._total_snapshots_created = 0
        self._total_snapshots_failed = 0
        self._last_error: Optional[str] = None

    async def start(self):
        """
        Start the snapshot scheduler background task.

        Raises:
            RuntimeError: If scheduler is already running
        """
        if self._running:
            raise RuntimeError("Snapshot scheduler is already running")

        if not self.config.enabled:
            logger.info("Snapshot scheduler disabled (SNAPSHOT_ENABLED=false)")
            return

        logger.info(
            "Starting snapshot scheduler",
            config=str(self.config),
        )

        # Initialize components if not provided
        if self.journal is None:
            from backend.app.modules.credits.event_sourcing.event_journal import (
                get_event_journal,
            )

            self.journal = await get_event_journal()

        if self.projection_manager is None:
            from backend.app.modules.credits.event_sourcing.projections import (
                get_projection_manager,
            )

            self.projection_manager = get_projection_manager()

        if self.snapshot_manager is None:
            from backend.app.modules.credits.event_sourcing.snapshot_manager import (
                get_snapshot_manager,
            )

            self.snapshot_manager = await get_snapshot_manager()

        # Start background task
        self._running = True
        self._task = asyncio.create_task(self._run_loop())

        logger.info(
            "Snapshot scheduler started",
            interval_minutes=self.config.interval_minutes,
            event_threshold=self.config.event_threshold,
        )

    async def stop(self):
        """
        Stop the snapshot scheduler gracefully.

        Waits for current snapshot operation to complete.
        """
        if not self._running:
            logger.warning("Snapshot scheduler is not running")
            return

        logger.info("Stopping snapshot scheduler...")

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info(
            "Snapshot scheduler stopped",
            total_snapshots_created=self._total_snapshots_created,
            total_snapshots_failed=self._total_snapshots_failed,
        )

    async def _run_loop(self):
        """
        Main scheduler loop.

        Checks snapshot triggers periodically and creates snapshots when needed.
        """
        logger.info("Snapshot scheduler loop started")

        while self._running:
            try:
                # Sleep for check interval
                await asyncio.sleep(self.config.check_interval_seconds)

                # Check if we should create a snapshot
                should_snapshot, reason = await self._should_create_snapshot()

                if should_snapshot:
                    logger.info(f"Snapshot trigger: {reason}")
                    await self._create_snapshot()

            except asyncio.CancelledError:
                logger.info("Snapshot scheduler loop cancelled")
                break

            except Exception as e:
                logger.error(
                    f"Error in snapshot scheduler loop: {e}",
                    exc_info=True,
                )
                self._total_snapshots_failed += 1
                self._last_error = str(e)

                # Continue running despite errors
                await asyncio.sleep(60)  # Wait 1 minute before retrying

        logger.info("Snapshot scheduler loop exited")

    async def _should_create_snapshot(self) -> tuple[bool, Optional[str]]:
        """
        Check if snapshot should be created based on triggers.

        Returns:
            (should_create, reason) tuple
        """
        # Count events in journal
        event_count = 0
        async for _ in self.journal.read_events():
            event_count += 1

        self._current_event_count = event_count

        # Check time-based trigger
        time_trigger = False
        if self.config.interval_minutes > 0:
            if self._last_snapshot_time is None:
                # No snapshots yet, create first one
                time_trigger = True
            else:
                time_since_last = datetime.utcnow() - self._last_snapshot_time
                if time_since_last >= timedelta(minutes=self.config.interval_minutes):
                    time_trigger = True

        # Check event-based trigger
        event_trigger = False
        if self.config.event_threshold > 0:
            events_since_last = event_count - self._last_snapshot_event_count
            if events_since_last >= self.config.event_threshold:
                event_trigger = True

        # Determine trigger reason
        if time_trigger and event_trigger:
            return True, f"Time ({self.config.interval_minutes}min) AND Event ({self.config.event_threshold} events)"
        elif time_trigger:
            return True, f"Time trigger ({self.config.interval_minutes} minutes elapsed)"
        elif event_trigger:
            events_since = event_count - self._last_snapshot_event_count
            return True, f"Event trigger ({events_since} events since last snapshot)"

        return False, None

    async def _create_snapshot(self):
        """
        Create a snapshot and enforce retention policy.

        Updates scheduler state on success.
        """
        try:
            logger.info("Creating automatic snapshot...")

            # Create snapshot
            snapshot = await self.snapshot_manager.create_snapshot(
                projection_manager=self.projection_manager,
                sequence_number=self._current_event_count,
                event_count=self._current_event_count,
            )

            # Update state
            self._last_snapshot_time = datetime.utcnow()
            self._last_snapshot_event_count = self._current_event_count
            self._total_snapshots_created += 1

            logger.info(
                f"Automatic snapshot created successfully",
                snapshot_id=snapshot.snapshot_id,
                sequence_number=snapshot.sequence_number,
                size_mb=snapshot.size_bytes / 1024 / 1024 if snapshot.size_bytes else 0,
            )

            # Enforce retention policy
            await self._enforce_retention_policy()

        except Exception as e:
            logger.error(
                f"Failed to create automatic snapshot: {e}",
                exc_info=True,
            )
            self._total_snapshots_failed += 1
            self._last_error = str(e)
            raise

    async def _enforce_retention_policy(self):
        """
        Delete old snapshots to enforce retention policy.

        Keeps only the N most recent snapshots (configured via retention_count).
        """
        try:
            # Get all snapshots
            snapshots = await self.snapshot_manager.list_snapshots()

            if len(snapshots) <= self.config.retention_count:
                # Within retention limit
                return

            # Sort by created_at descending
            sorted_snapshots = sorted(
                snapshots,
                key=lambda s: s.created_at,
                reverse=True,
            )

            # Delete snapshots beyond retention count
            snapshots_to_delete = sorted_snapshots[self.config.retention_count :]

            for snapshot in snapshots_to_delete:
                try:
                    await self.snapshot_manager.delete_snapshot(snapshot.snapshot_id)
                    logger.info(
                        f"Deleted old snapshot (retention policy)",
                        snapshot_id=snapshot.snapshot_id,
                        age_days=(datetime.utcnow() - snapshot.created_at).days,
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to delete old snapshot {snapshot.snapshot_id}: {e}"
                    )

        except Exception as e:
            logger.error(
                f"Failed to enforce retention policy: {e}",
                exc_info=True,
            )

    def get_status(self) -> dict:
        """
        Get scheduler status and metrics.

        Returns:
            Dict with scheduler status:
            - running: Whether scheduler is running
            - enabled: Whether scheduler is enabled
            - config: Scheduler configuration
            - last_snapshot_time: Timestamp of last snapshot
            - current_event_count: Current event count in journal
            - total_snapshots_created: Total snapshots created
            - total_snapshots_failed: Total snapshot failures
            - last_error: Last error message (if any)
        """
        return {
            "running": self._running,
            "enabled": self.config.enabled,
            "config": {
                "interval_minutes": self.config.interval_minutes,
                "event_threshold": self.config.event_threshold,
                "retention_count": self.config.retention_count,
                "check_interval_seconds": self.config.check_interval_seconds,
            },
            "last_snapshot_time": (
                self._last_snapshot_time.isoformat()
                if self._last_snapshot_time
                else None
            ),
            "last_snapshot_event_count": self._last_snapshot_event_count,
            "current_event_count": self._current_event_count,
            "total_snapshots_created": self._total_snapshots_created,
            "total_snapshots_failed": self._total_snapshots_failed,
            "last_error": self._last_error,
        }


# === Singleton Pattern ===

_snapshot_scheduler_instance: Optional[SnapshotScheduler] = None


def get_snapshot_scheduler() -> SnapshotScheduler:
    """
    Get singleton SnapshotScheduler instance.

    Note: Does not start the scheduler automatically.
    Call scheduler.start() explicitly during application startup.

    Returns:
        SnapshotScheduler instance
    """
    global _snapshot_scheduler_instance

    if _snapshot_scheduler_instance is None:
        _snapshot_scheduler_instance = SnapshotScheduler()

    return _snapshot_scheduler_instance


async def start_snapshot_scheduler() -> SnapshotScheduler:
    """
    Convenience function to get and start snapshot scheduler.

    Returns:
        Started SnapshotScheduler instance

    Example:
        # In FastAPI startup
        @app.on_event("startup")
        async def startup():
            await start_snapshot_scheduler()
    """
    scheduler = get_snapshot_scheduler()
    await scheduler.start()
    return scheduler


async def stop_snapshot_scheduler():
    """
    Convenience function to stop snapshot scheduler.

    Example:
        # In FastAPI shutdown
        @app.on_event("shutdown")
        async def shutdown():
            await stop_snapshot_scheduler()
    """
    scheduler = get_snapshot_scheduler()
    await scheduler.stop()
