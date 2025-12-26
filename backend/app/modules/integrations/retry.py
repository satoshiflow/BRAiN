"""
Retry handler with exponential backoff and jitter.

Provides configurable retry logic for failed API requests, with support for
exponential/linear/fixed backoff strategies and random jitter to prevent
thundering herd problems.
"""

from __future__ import annotations

import asyncio
import random
from typing import Optional, Callable, TypeVar, ParamSpec, Any
from loguru import logger

from .schemas import RetryConfig, RetryStrategy
from .exceptions import RetryExhaustedError, TimeoutError as IntegrationTimeoutError

P = ParamSpec("P")
R = TypeVar("R")


class RetryHandler:
    """
    Retry handler with configurable backoff strategies.

    Implements exponential, linear, and fixed backoff strategies with
    optional jitter to prevent synchronized retries across multiple clients.
    """

    def __init__(self, config: RetryConfig) -> None:
        """
        Initialize retry handler.

        Args:
            config: Retry configuration
        """
        self.config = config

        logger.debug(
            "RetryHandler initialized: max_retries={max}, strategy={strategy}, "
            "initial_delay={delay}s",
            max=config.max_retries,
            strategy=config.strategy,
            delay=config.initial_delay,
        )

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for the given attempt number.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.config.strategy == RetryStrategy.FIXED:
            delay = self.config.initial_delay

        elif self.config.strategy == RetryStrategy.LINEAR:
            delay = self.config.initial_delay * (attempt + 1) * self.config.backoff_multiplier

        elif self.config.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.config.initial_delay * (self.config.backoff_multiplier ** attempt)

        else:
            # Should not happen, but defensive programming
            delay = self.config.initial_delay

        # Cap at max_delay
        delay = min(delay, self.config.max_delay)

        # Add jitter if enabled
        if self.config.jitter:
            # Add random jitter: ±25% of delay
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

            # Ensure delay is positive
            delay = max(0.1, delay)

        return delay

    def _should_retry(
        self,
        exception: Exception,
        *,
        status_code: Optional[int] = None,
    ) -> bool:
        """
        Determine if request should be retried based on exception/status.

        Args:
            exception: Exception that occurred
            status_code: HTTP status code (if applicable)

        Returns:
            True if should retry, False otherwise
        """
        # Check if it's a timeout
        if isinstance(exception, (asyncio.TimeoutError, IntegrationTimeoutError)):
            return self.config.retry_on_timeout

        # Try to extract status code from exception if not provided
        if status_code is None:
            if hasattr(exception, "status_code"):
                status_code = exception.status_code
            elif hasattr(exception, "response") and hasattr(exception.response, "status_code"):
                status_code = exception.response.status_code

        # Check if status code should be retried
        if status_code and status_code in self.config.retry_status_codes:
            return True

        # Check for specific exceptions that should be retried
        exception_name = type(exception).__name__.lower()
        retryable_exceptions = [
            "timeout",
            "connectionerror",
            "connecttimeout",
            "readtimeout",
        ]

        for retryable in retryable_exceptions:
            if retryable in exception_name:
                return True

        return False

    async def call(
        self,
        func: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        """
        Execute function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            RetryExhaustedError: If all retry attempts exhausted
            Any exception raised by func if retries not applicable
        """
        last_exception: Optional[Exception] = None
        attempt = 0

        while attempt <= self.config.max_retries:
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success!
                if attempt > 0:
                    logger.info(
                        "Request succeeded after {attempt} retry/retries",
                        attempt=attempt,
                    )

                return result

            except Exception as exc:
                last_exception = exc

                # Check if we should retry
                should_retry = self._should_retry(exc)

                if not should_retry:
                    logger.debug(
                        "Exception not retryable: {exc}",
                        exc=type(exc).__name__,
                    )
                    raise

                # Check if we have retries left
                if attempt >= self.config.max_retries:
                    logger.error(
                        "All retry attempts exhausted ({max} retries)",
                        max=self.config.max_retries,
                    )
                    raise RetryExhaustedError(
                        f"Failed after {attempt} retry attempts",
                        attempts=attempt,
                        last_error=exc,
                    ) from exc

                # Calculate delay
                delay = self._calculate_delay(attempt)

                logger.warning(
                    "Request failed (attempt {attempt}/{max}), "
                    "retrying in {delay:.2f}s: {exc}",
                    attempt=attempt + 1,
                    max=self.config.max_retries + 1,
                    delay=delay,
                    exc=str(exc),
                )

                # Wait before retry
                await asyncio.sleep(delay)

                # Increment attempt counter
                attempt += 1

        # Should not reach here, but defensive programming
        if last_exception:
            raise RetryExhaustedError(
                f"Failed after {attempt} retry attempts",
                attempts=attempt,
                last_error=last_exception,
            ) from last_exception

        raise RetryExhaustedError(
            "Retry logic error: no exception but no success",
            attempts=attempt,
        )

    async def call_with_custom_retry(
        self,
        func: Callable[P, R],
        should_retry_func: Callable[[Exception], bool],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        """
        Execute function with custom retry predicate.

        Args:
            func: Async function to execute
            should_retry_func: Custom function to determine if should retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            RetryExhaustedError: If all retry attempts exhausted
            Any exception raised by func if retries not applicable
        """
        last_exception: Optional[Exception] = None
        attempt = 0

        while attempt <= self.config.max_retries:
            try:
                # Execute function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # Success!
                if attempt > 0:
                    logger.info(
                        "Request succeeded after {attempt} retry/retries",
                        attempt=attempt,
                    )

                return result

            except Exception as exc:
                last_exception = exc

                # Use custom retry predicate
                should_retry = should_retry_func(exc)

                if not should_retry:
                    logger.debug(
                        "Custom predicate: exception not retryable: {exc}",
                        exc=type(exc).__name__,
                    )
                    raise

                # Check if we have retries left
                if attempt >= self.config.max_retries:
                    logger.error(
                        "All retry attempts exhausted ({max} retries)",
                        max=self.config.max_retries,
                    )
                    raise RetryExhaustedError(
                        f"Failed after {attempt} retry attempts",
                        attempts=attempt,
                        last_error=exc,
                    ) from exc

                # Calculate delay
                delay = self._calculate_delay(attempt)

                logger.warning(
                    "Request failed (attempt {attempt}/{max}), "
                    "retrying in {delay:.2f}s: {exc}",
                    attempt=attempt + 1,
                    max=self.config.max_retries + 1,
                    delay=delay,
                    exc=str(exc),
                )

                # Wait before retry
                await asyncio.sleep(delay)

                # Increment attempt counter
                attempt += 1

        # Should not reach here, but defensive programming
        if last_exception:
            raise RetryExhaustedError(
                f"Failed after {attempt} retry attempts",
                attempts=attempt,
                last_error=last_exception,
            ) from last_exception

        raise RetryExhaustedError(
            "Retry logic error: no exception but no success",
            attempts=attempt,
        )


def create_retry_handler(
    *,
    max_retries: int = 3,
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    retry_status_codes: Optional[list[int]] = None,
    retry_on_timeout: bool = True,
) -> RetryHandler:
    """
    Create a retry handler with the given configuration.

    This is a convenience function for creating RetryHandler instances.

    Args:
        max_retries: Maximum number of retry attempts
        strategy: Backoff strategy
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        backoff_multiplier: Multiplier for backoff
        jitter: Whether to add random jitter
        retry_status_codes: HTTP status codes to retry
        retry_on_timeout: Whether to retry on timeout

    Returns:
        Configured RetryHandler instance
    """
    config = RetryConfig(
        max_retries=max_retries,
        strategy=strategy,
        initial_delay=initial_delay,
        max_delay=max_delay,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        retry_status_codes=retry_status_codes or [408, 429, 500, 502, 503, 504],
        retry_on_timeout=retry_on_timeout,
    )

    return RetryHandler(config)
