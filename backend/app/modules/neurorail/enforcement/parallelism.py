"""
Budget Parallelism Limiter (Phase 2 Enforcement).

Limits concurrent execution using semaphores.
Integrates with immune system and Prometheus metrics.
"""

import asyncio
from typing import Callable, Any, Optional, Dict
from contextlib import asynccontextmanager
from loguru import logger

from backend.app.modules.governor.manifest.schemas import Budget
from backend.app.modules.neurorail.errors import (
    BudgetParallelismExceededError,
    NeuroRailErrorCode,
    should_alert_immune,
)


class ParallelismLimiter:
    """
    Limits parallel execution using semaphores.

    Features:
    - Per-job parallelism limits (max_parallel_attempts)
    - Global parallelism limits (max_global_parallel)
    - Semaphore-based concurrency control
    - Queue tracking for blocked executions
    - Immune system integration
    - Prometheus metrics tracking

    Usage:
        limiter = ParallelismLimiter(max_global_parallel=10)

        async def my_task():
            await asyncio.sleep(1)
            return "done"

        budget = Budget(max_parallel_attempts=2)

        try:
            result = await limiter.execute_with_limit(
                task=my_task,
                budget=budget,
                job_id="j_123",
                context={"attempt_id": "a_456"}
            )
        except BudgetParallelismExceededError as e:
            logger.error(f"Parallelism limit exceeded: {e}")
    """

    def __init__(self, max_global_parallel: int = 100):
        """
        Initialize parallelism limiter.

        Args:
            max_global_parallel: Global limit for all parallel executions (default: 100)
        """
        self.max_global_parallel = max_global_parallel
        self.global_semaphore = asyncio.Semaphore(max_global_parallel)

        # Per-job semaphores (lazy initialization)
        self.job_semaphores: Dict[str, asyncio.Semaphore] = {}

        # Metrics
        self.global_active_count = 0
        self.global_peak_count = 0
        self.global_rejected_count = 0
        self.job_active_counts: Dict[str, int] = {}
        self.job_rejected_counts: Dict[str, int] = {}

    def _get_job_semaphore(self, job_id: str, max_parallel: int) -> asyncio.Semaphore:
        """
        Get or create semaphore for job_id.

        Args:
            job_id: Job identifier
            max_parallel: Maximum parallel executions for this job

        Returns:
            Asyncio semaphore
        """
        if job_id not in self.job_semaphores:
            self.job_semaphores[job_id] = asyncio.Semaphore(max_parallel)
        return self.job_semaphores[job_id]

    @asynccontextmanager
    async def acquire_slot(
        self,
        job_id: str,
        budget: Budget,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Acquire execution slot (context manager).

        Args:
            job_id: Job identifier
            budget: Budget with max_parallel_attempts
            context: Optional context

        Yields:
            None (slot acquired)

        Raises:
            BudgetParallelismExceededError: If limits exceeded
        """
        context = context or {}
        max_parallel_attempts = budget.max_parallel_attempts or 5  # Default: 5

        job_semaphore = self._get_job_semaphore(job_id, max_parallel_attempts)

        # Try to acquire global semaphore (non-blocking check)
        if self.global_semaphore.locked() and self.global_semaphore._value == 0:
            self.global_rejected_count += 1

            logger.warning(
                f"Global parallelism limit reached: {self.max_global_parallel}",
                extra={
                    "context": context,
                    "job_id": job_id,
                    "max_global_parallel": self.max_global_parallel,
                }
            )

            # Check immune alert
            immune_alert = should_alert_immune(NeuroRailErrorCode.BUDGET_PARALLELISM_EXCEEDED)

            raise BudgetParallelismExceededError(
                message=f"Global parallelism limit exceeded: {self.max_global_parallel}",
                error_code=NeuroRailErrorCode.BUDGET_PARALLELISM_EXCEEDED,
                context={
                    **context,
                    "job_id": job_id,
                    "max_global_parallel": self.max_global_parallel,
                    "limit_type": "global",
                    "immune_alert": immune_alert,
                },
            )

        # Try to acquire job-specific semaphore (non-blocking check)
        if job_semaphore.locked() and job_semaphore._value == 0:
            self.job_rejected_counts[job_id] = self.job_rejected_counts.get(job_id, 0) + 1

            logger.warning(
                f"Job parallelism limit reached for {job_id}: {max_parallel_attempts}",
                extra={
                    "context": context,
                    "job_id": job_id,
                    "max_parallel_attempts": max_parallel_attempts,
                }
            )

            # Check immune alert
            immune_alert = should_alert_immune(NeuroRailErrorCode.BUDGET_PARALLELISM_EXCEEDED)

            raise BudgetParallelismExceededError(
                message=f"Job parallelism limit exceeded for {job_id}: {max_parallel_attempts}",
                error_code=NeuroRailErrorCode.BUDGET_PARALLELISM_EXCEEDED,
                context={
                    **context,
                    "job_id": job_id,
                    "max_parallel_attempts": max_parallel_attempts,
                    "limit_type": "job",
                    "immune_alert": immune_alert,
                },
            )

        # Acquire both semaphores
        async with self.global_semaphore:
            async with job_semaphore:
                # Update metrics
                self.global_active_count += 1
                self.global_peak_count = max(self.global_peak_count, self.global_active_count)
                self.job_active_counts[job_id] = self.job_active_counts.get(job_id, 0) + 1

                logger.debug(
                    f"Acquired execution slot: global={self.global_active_count}/{self.max_global_parallel}, "
                    f"job={self.job_active_counts[job_id]}/{max_parallel_attempts}",
                    extra={"context": context, "job_id": job_id}
                )

                try:
                    yield

                finally:
                    # Release metrics
                    self.global_active_count -= 1
                    self.job_active_counts[job_id] -= 1

                    logger.debug(
                        f"Released execution slot: global={self.global_active_count}/{self.max_global_parallel}",
                        extra={"context": context, "job_id": job_id}
                    )

    async def execute_with_limit(
        self,
        task: Callable[[], Any],
        budget: Budget,
        job_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute task with parallelism limits.

        Args:
            task: Async callable to execute
            budget: Budget with max_parallel_attempts
            job_id: Job identifier
            context: Optional context

        Returns:
            Task result

        Raises:
            BudgetParallelismExceededError: If limits exceeded
        """
        async with self.acquire_slot(job_id, budget, context):
            return await task()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get parallelism limiter metrics.

        Returns:
            Dictionary with active counts, peak, rejected counts
        """
        return {
            "global_active_count": self.global_active_count,
            "global_peak_count": self.global_peak_count,
            "global_rejected_count": self.global_rejected_count,
            "max_global_parallel": self.max_global_parallel,
            "job_active_counts": dict(self.job_active_counts),
            "job_rejected_counts": dict(self.job_rejected_counts),
        }

    def reset_metrics(self):
        """Reset metrics counters (preserves peak count)."""
        self.global_rejected_count = 0
        self.job_rejected_counts.clear()
        # Note: active counts and peak count are not reset (reflect current state)


# Singleton instance
_parallelism_limiter: Optional[ParallelismLimiter] = None


def get_parallelism_limiter() -> ParallelismLimiter:
    """Get singleton ParallelismLimiter instance."""
    global _parallelism_limiter
    if _parallelism_limiter is None:
        _parallelism_limiter = ParallelismLimiter()
    return _parallelism_limiter
