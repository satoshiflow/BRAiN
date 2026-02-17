"""
Budget Retry Handler (Phase 2 Enforcement).

Implements retry logic with exponential backoff, jitter, and retriability classification.
Integrates with immune system and Prometheus metrics.
"""

import asyncio
import random
import time
from typing import Callable, Any, Optional, Dict, Type
from loguru import logger

from app.modules.governor.manifest.schemas import Budget
from app.modules.neurorail.errors import (
    BudgetRetryExhaustedError,
    NeuroRailErrorCode,
    ERROR_METADATA,
    should_alert_immune,
)


class RetryHandler:
    """
    Handles retry logic with exponential backoff and jitter.

    Features:
    - Exponential backoff: delay = base_delay * (2 ** attempt)
    - Jitter: randomness to prevent thundering herd
    - Retriability classification from error codes
    - max_retries enforcement from budget
    - Immune system integration
    - Prometheus metrics tracking

    Usage:
        handler = RetryHandler()

        async def my_task():
            # Potentially failing task
            if random.random() < 0.5:
                raise ValueError("Random failure")
            return "success"

        budget = Budget(max_retries=3)

        try:
            result = await handler.execute_with_retry(
                task=my_task,
                budget=budget,
                context={"job_id": "j_123"}
            )
        except BudgetRetryExhaustedError as e:
            logger.error(f"Retries exhausted: {e}")
    """

    def __init__(
        self,
        base_delay_ms: float = 1000.0,
        max_delay_ms: float = 60000.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry handler.

        Args:
            base_delay_ms: Base delay in milliseconds (default: 1000ms = 1s)
            max_delay_ms: Maximum delay cap (default: 60000ms = 60s)
            exponential_base: Exponential base for backoff (default: 2.0)
            jitter: Whether to add random jitter (default: True)
        """
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.exponential_base = exponential_base
        self.jitter = jitter

        self.retry_count = 0
        self.success_after_retry_count = 0
        self.exhausted_count = 0

    def _compute_delay(self, attempt: int) -> float:
        """
        Compute retry delay with exponential backoff and jitter.

        Formula:
            delay = min(base_delay * (exponential_base ** attempt), max_delay)
            if jitter: delay = delay * random(0.5, 1.5)

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff
        delay_ms = self.base_delay_ms * (self.exponential_base ** attempt)

        # Cap at max_delay
        delay_ms = min(delay_ms, self.max_delay_ms)

        # Add jitter (±50%)
        if self.jitter:
            jitter_factor = random.uniform(0.5, 1.5)
            delay_ms *= jitter_factor

        return delay_ms / 1000.0  # Convert to seconds

    def _is_retriable(self, exception: Exception) -> bool:
        """
        Check if exception is retriable based on error code metadata.

        Args:
            exception: Exception to check

        Returns:
            True if retriable, False otherwise
        """
        # Check if exception has error_code attribute
        if hasattr(exception, "error_code"):
            error_code = exception.error_code
            metadata = ERROR_METADATA.get(error_code, {})
            return metadata.get("retriable", False)

        # Default retriability for common exceptions
        retriable_exceptions = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )

        return isinstance(exception, retriable_exceptions)

    async def execute_with_retry(
        self,
        task: Callable[[], Any],
        budget: Budget,
        context: Optional[Dict[str, Any]] = None,
        retriable_exceptions: Optional[tuple] = None,
    ) -> Any:
        """
        Execute task with retry logic.

        Args:
            task: Async callable to execute
            budget: Budget with max_retries
            context: Optional context (job_id, attempt_id, etc.)
            retriable_exceptions: Optional tuple of retriable exception types

        Returns:
            Task result

        Raises:
            BudgetRetryExhaustedError: If max_retries exhausted
            Exception: If non-retriable exception occurs
        """
        context = context or {}
        max_retries = budget.max_retries or 3  # Default: 3 retries

        last_exception: Optional[Exception] = None
        retry_history = []

        for attempt in range(max_retries + 1):  # 0 = initial attempt, 1-N = retries
            try:
                start_time = time.time()

                # Execute task
                result = await task()

                elapsed_ms = (time.time() - start_time) * 1000

                # Log success
                if attempt > 0:
                    logger.info(
                        f"Task succeeded after {attempt} retries: {elapsed_ms:.2f}ms",
                        extra={
                            "context": context,
                            "attempt": attempt,
                            "retry_history": retry_history,
                        }
                    )
                    self.success_after_retry_count += 1
                else:
                    logger.debug(
                        f"Task succeeded on first attempt: {elapsed_ms:.2f}ms",
                        extra={"context": context}
                    )

                return result

            except Exception as e:
                elapsed_ms = (time.time() - start_time) * 1000
                last_exception = e

                # Check if retriable
                is_retriable = self._is_retriable(e)

                # If retriable_exceptions provided, check against it
                if retriable_exceptions and isinstance(e, retriable_exceptions):
                    is_retriable = True

                # Record retry history
                retry_history.append({
                    "attempt": attempt,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "retriable": is_retriable,
                    "elapsed_ms": elapsed_ms,
                })

                # If not retriable, raise immediately
                if not is_retriable:
                    logger.error(
                        f"Non-retriable error on attempt {attempt}: {e}",
                        extra={
                            "context": context,
                            "attempt": attempt,
                            "error_type": type(e).__name__,
                        }
                    )
                    raise

                # If max retries reached, raise BudgetRetryExhaustedError
                if attempt >= max_retries:
                    self.retry_count += attempt
                    self.exhausted_count += 1

                    logger.error(
                        f"Retry budget exhausted after {attempt} retries: {e}",
                        extra={
                            "context": context,
                            "max_retries": max_retries,
                            "retry_history": retry_history,
                        }
                    )

                    # Check immune alert
                    immune_alert = should_alert_immune(NeuroRailErrorCode.BUDGET_RETRY_EXHAUSTED)

                    # Raise BudgetRetryExhaustedError
                    raise BudgetRetryExhaustedError(
                        message=f"Retry budget exhausted after {attempt} retries: {e}",
                        error_code=NeuroRailErrorCode.BUDGET_RETRY_EXHAUSTED,
                        context={
                            **context,
                            "max_retries": max_retries,
                            "attempts": attempt,
                            "retry_history": retry_history,
                            "last_error": str(e),
                            "last_error_type": type(e).__name__,
                            "immune_alert": immune_alert,
                        },
                    ) from e

                # Compute delay and retry
                delay_sec = self._compute_delay(attempt)

                logger.warning(
                    f"Retrying after {delay_sec:.2f}s (attempt {attempt + 1}/{max_retries}): {e}",
                    extra={
                        "context": context,
                        "attempt": attempt,
                        "delay_sec": delay_sec,
                        "error_type": type(e).__name__,
                    }
                )

                self.retry_count += 1

                # Wait before retry
                await asyncio.sleep(delay_sec)

        # Should never reach here (handled by max_retries check above)
        # But just in case, raise last exception
        if last_exception:
            raise last_exception

    def get_metrics(self) -> Dict[str, int]:
        """
        Get retry handler metrics.

        Returns:
            Dictionary with retry_count, success_after_retry_count, exhausted_count
        """
        return {
            "retry_count": self.retry_count,
            "success_after_retry_count": self.success_after_retry_count,
            "exhausted_count": self.exhausted_count,
        }

    def reset_metrics(self):
        """Reset metrics counters."""
        self.retry_count = 0
        self.success_after_retry_count = 0
        self.exhausted_count = 0


# Singleton instance
_retry_handler: Optional[RetryHandler] = None


def get_retry_handler() -> RetryHandler:
    """Get singleton RetryHandler instance."""
    global _retry_handler
    if _retry_handler is None:
        _retry_handler = RetryHandler()
    return _retry_handler
