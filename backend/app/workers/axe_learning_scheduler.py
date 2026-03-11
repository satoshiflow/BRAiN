"""Background scheduler for AXE learning-candidate generation and retention cleanup."""

from __future__ import annotations

import asyncio
import logging
import os

from sqlalchemy import text

from app.core.db import get_session
from app.modules.axe_fusion.service import AXEFusionService

logger = logging.getLogger(__name__)


class AXELearningScheduler:
    """Periodic worker for AXE mapping analytics and retention."""

    def __init__(self, interval_seconds: int = 3600) -> None:
        self.interval_seconds = interval_seconds
        self.running = False
        self._failure_count = 0
        self._lock_key = int(os.getenv("AXE_LEARNING_LOCK_KEY", "742113908"))

    async def start(self) -> None:
        self.running = True
        logger.info("AXE learning scheduler started (interval=%ss)", self.interval_seconds)
        while self.running:
            try:
                await self._run_cycle()
                self._failure_count = 0
                sleep_for = self.interval_seconds
            except Exception as exc:
                logger.warning("AXE learning scheduler cycle failed: %s", exc)
                self._failure_count += 1
                sleep_for = min(self.interval_seconds * (2 ** self._failure_count), 3600)
            await asyncio.sleep(sleep_for)

    async def _run_cycle(self) -> None:
        window_days = int(os.getenv("AXE_LEARNING_WINDOW_DAYS", "7"))
        min_sample_size = int(os.getenv("AXE_LEARNING_MIN_SAMPLE_SIZE", "50"))

        async with get_session() as db:
            lock_row = (
                await db.execute(
                    text("SELECT pg_try_advisory_lock(:lock_key) AS lock_acquired"),
                    {"lock_key": self._lock_key},
                )
            ).first()
            lock_acquired = bool(lock_row and dict(lock_row._mapping).get("lock_acquired"))
            if not lock_acquired:
                logger.debug("AXE learning scheduler lock not acquired, skipping cycle")
                return

            service = AXEFusionService(db=db)
            try:
                generated = await service.generate_learning_candidates(
                    window_days=window_days,
                    min_sample_size=min_sample_size,
                )
                retention = await service.run_retention_cleanup()
                logger.info(
                    "AXE learning cycle complete (generated=%s retention=%s)",
                    generated,
                    retention,
                )
            finally:
                await db.execute(
                    text("SELECT pg_advisory_unlock(:lock_key)"),
                    {"lock_key": self._lock_key},
                )
                await db.commit()

    def stop(self) -> None:
        self.running = False
        logger.info("AXE learning scheduler stopped")


_axe_learning_scheduler: AXELearningScheduler | None = None


async def start_axe_learning_scheduler(interval_seconds: int = 3600) -> None:
    global _axe_learning_scheduler
    if _axe_learning_scheduler is None:
        _axe_learning_scheduler = AXELearningScheduler(interval_seconds=interval_seconds)
        await _axe_learning_scheduler.start()


def stop_axe_learning_scheduler() -> None:
    global _axe_learning_scheduler
    if _axe_learning_scheduler is not None:
        _axe_learning_scheduler.stop()
        _axe_learning_scheduler = None
