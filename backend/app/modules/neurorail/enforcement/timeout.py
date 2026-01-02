"""
Budget Timeout Enforcer (Phase 2 Enforcement).

Enforces timeout budgets using asyncio.wait_for() with grace period handling.
Integrates with immune system and Prometheus metrics.
"""

import asyncio
import time
from typing import Callable, Any, Optional, Dict
from loguru import logger

from backend.app.modules.governor.manifest.schemas import Budget
from backend.app.modules.neurorail.errors import (
    BudgetTimeoutExceededError,
    NeuroRailErrorCode,
    should_alert_immune,
)


class TimeoutEnforcer:
    """
    Enforces timeout budgets for execution.

    Features:
    - Hard timeout enforcement using asyncio.wait_for()
    - Grace period for cleanup (default: 5s)
    - Immune system integration
    - Prometheus metrics tracking

    Usage:
        enforcer = TimeoutEnforcer()

        async def my_task():
            await asyncio.sleep(10)
            return "done"

        budget = Budget(timeout_ms=5000, grace_period_ms=2000)

        try:
            result = await enforcer.enforce(
                task=my_task,
                budget=budget,
                context={"job_id": "j_123"}
            )
        except BudgetTimeoutExceededError as e:
            logger.error(f"Timeout exceeded: {e}")
    """

    def __init__(self):
        """Initialize timeout enforcer."""
        self.timeout_count = 0
        self.grace_period_invoked_count = 0

    async def enforce(
        self,
        task: Callable[[], Any],
        budget: Budget,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Enforce timeout budget on task execution.

        Args:
            task: Async callable to execute
            budget: Budget with timeout_ms and grace_period_ms
            context: Optional context (job_id, attempt_id, etc.)

        Returns:
            Task result

        Raises:
            BudgetTimeoutExceededError: If timeout exceeded
        """
        context = context or {}
        timeout_ms = budget.timeout_ms or 30000  # Default: 30s
        grace_period_ms = budget.grace_period_ms or 5000  # Default: 5s

        timeout_sec = timeout_ms / 1000.0
        grace_sec = grace_period_ms / 1000.0

        start_time = time.time()

        try:
            # Enforce hard timeout
            result = await asyncio.wait_for(task(), timeout=timeout_sec)

            elapsed_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Task completed within budget: {elapsed_ms:.2f}ms / {timeout_ms}ms",
                extra={"context": context}
            )

            return result

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000

            # Increment metrics
            self.timeout_count += 1

            # Log timeout
            logger.error(
                f"Budget timeout exceeded: {elapsed_ms:.2f}ms > {timeout_ms}ms",
                extra={
                    "context": context,
                    "timeout_ms": timeout_ms,
                    "elapsed_ms": elapsed_ms,
                    "grace_period_ms": grace_period_ms,
                }
            )

            # Check if immune alert required
            immune_alert = should_alert_immune(NeuroRailErrorCode.BUDGET_TIMEOUT_EXCEEDED)

            # Raise BudgetTimeoutExceededError
            raise BudgetTimeoutExceededError(
                message=f"Execution exceeded timeout budget: {elapsed_ms:.2f}ms > {timeout_ms}ms",
                error_code=NeuroRailErrorCode.BUDGET_TIMEOUT_EXCEEDED,
                context={
                    **context,
                    "timeout_ms": timeout_ms,
                    "elapsed_ms": elapsed_ms,
                    "grace_period_ms": grace_period_ms,
                    "immune_alert": immune_alert,
                },
            )

    async def enforce_with_grace_period(
        self,
        task: Callable[[], Any],
        budget: Budget,
        cleanup_handler: Optional[Callable[[], Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Enforce timeout with grace period for cleanup.

        If task exceeds timeout, cleanup_handler is invoked with grace period.
        If cleanup also times out, raise BudgetTimeoutExceededError.

        Args:
            task: Async callable to execute
            budget: Budget with timeout_ms and grace_period_ms
            cleanup_handler: Optional cleanup callable (invoked on timeout)
            context: Optional context

        Returns:
            Task result

        Raises:
            BudgetTimeoutExceededError: If timeout or grace period exceeded
        """
        context = context or {}
        timeout_ms = budget.timeout_ms or 30000
        grace_period_ms = budget.grace_period_ms or 5000

        timeout_sec = timeout_ms / 1000.0
        grace_sec = grace_period_ms / 1000.0

        start_time = time.time()

        try:
            # Enforce hard timeout
            result = await asyncio.wait_for(task(), timeout=timeout_sec)

            elapsed_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Task completed within budget: {elapsed_ms:.2f}ms / {timeout_ms}ms",
                extra={"context": context}
            )

            return result

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000

            # Increment grace period metric
            self.grace_period_invoked_count += 1

            logger.warning(
                f"Task timeout - invoking grace period cleanup: {elapsed_ms:.2f}ms > {timeout_ms}ms",
                extra={
                    "context": context,
                    "timeout_ms": timeout_ms,
                    "elapsed_ms": elapsed_ms,
                    "grace_period_ms": grace_period_ms,
                }
            )

            # Invoke cleanup handler with grace period
            if cleanup_handler:
                try:
                    await asyncio.wait_for(cleanup_handler(), timeout=grace_sec)

                    logger.info(
                        f"Cleanup completed within grace period: {grace_period_ms}ms",
                        extra={"context": context}
                    )

                except asyncio.TimeoutError:
                    grace_elapsed_ms = (time.time() - start_time - timeout_sec) * 1000

                    logger.error(
                        f"Grace period exceeded during cleanup: {grace_elapsed_ms:.2f}ms > {grace_period_ms}ms",
                        extra={
                            "context": context,
                            "grace_period_ms": grace_period_ms,
                            "grace_elapsed_ms": grace_elapsed_ms,
                        }
                    )

            # Increment timeout metric
            self.timeout_count += 1

            # Check immune alert
            immune_alert = should_alert_immune(NeuroRailErrorCode.BUDGET_TIMEOUT_EXCEEDED)

            # Raise BudgetTimeoutExceededError
            raise BudgetTimeoutExceededError(
                message=f"Execution exceeded timeout budget: {elapsed_ms:.2f}ms > {timeout_ms}ms",
                error_code=NeuroRailErrorCode.BUDGET_TIMEOUT_EXCEEDED,
                context={
                    **context,
                    "timeout_ms": timeout_ms,
                    "elapsed_ms": elapsed_ms,
                    "grace_period_ms": grace_period_ms,
                    "grace_period_invoked": True,
                    "immune_alert": immune_alert,
                },
            )

    def get_metrics(self) -> Dict[str, int]:
        """
        Get enforcer metrics.

        Returns:
            Dictionary with timeout_count and grace_period_invoked_count
        """
        return {
            "timeout_count": self.timeout_count,
            "grace_period_invoked_count": self.grace_period_invoked_count,
        }

    def reset_metrics(self):
        """Reset metrics counters."""
        self.timeout_count = 0
        self.grace_period_invoked_count = 0


# Singleton instance
_timeout_enforcer: Optional[TimeoutEnforcer] = None


def get_timeout_enforcer() -> TimeoutEnforcer:
    """Get singleton TimeoutEnforcer instance."""
    global _timeout_enforcer
    if _timeout_enforcer is None:
        _timeout_enforcer = TimeoutEnforcer()
    return _timeout_enforcer
