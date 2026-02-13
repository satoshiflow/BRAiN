"""
Circuit breaker implementation for API resilience.

Implements the circuit breaker pattern with three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Too many failures, requests blocked
- HALF_OPEN: Testing if service recovered

This prevents cascading failures and gives failing services time to recover.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Callable, Any, TypeVar, ParamSpec
from functools import wraps
from loguru import logger

from .schemas import CircuitBreakerConfig, CircuitBreakerState, CircuitState
from .exceptions import CircuitBreakerOpenError

P = ParamSpec("P")
R = TypeVar("R")


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    The circuit breaker monitors failures and "opens" (blocks requests) when
    a failure threshold is exceeded. After a recovery timeout, it enters
    "half-open" state to test if the service recovered.
    """

    def __init__(
        self,
        config: CircuitBreakerConfig,
        *,
        name: str = "default",
    ) -> None:
        """
        Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
            name: Identifier for this circuit breaker (for logging)
        """
        self.config = config
        self.name = name
        self.state = CircuitBreakerState()

        logger.debug(
            "CircuitBreaker '{name}' initialized: "
            "failure_threshold={fail}, recovery_timeout={timeout}s",
            name=name,
            fail=config.failure_threshold,
            timeout=config.recovery_timeout,
        )

    def _should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.state.next_retry_at is None:
            return False

        now = datetime.now(timezone.utc)
        return now >= self.state.next_retry_at

    def _can_execute(self) -> bool:
        """Check if request can be executed based on circuit state."""
        if self.state.state == CircuitState.CLOSED:
            return True

        if self.state.state == CircuitState.HALF_OPEN:
            # Allow requests in half-open state (testing recovery)
            return True

        if self.state.state == CircuitState.OPEN:
            # Check if recovery timeout elapsed
            if self._should_attempt_recovery():
                # Transition to half-open
                self._transition_to_half_open()
                return True

            # Still in open state, block request
            return False

        return False

    def _transition_to_half_open(self) -> None:
        """Transition from OPEN to HALF_OPEN state."""
        self.state.state = CircuitState.HALF_OPEN
        self.state.success_count = 0
        logger.info(
            "CircuitBreaker '{name}' → HALF_OPEN (testing recovery)",
            name=self.name,
        )

    def _transition_to_open(self) -> None:
        """Transition to OPEN state (circuit opened, blocking requests)."""
        self.state.state = CircuitState.OPEN
        self.state.next_retry_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.config.recovery_timeout
        )

        logger.warning(
            "CircuitBreaker '{name}' → OPEN (failures={count}, "
            "next_retry={retry})",
            name=self.name,
            count=self.state.failure_count,
            retry=self.state.next_retry_at.isoformat(),
        )

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state (circuit closed, normal operation)."""
        self.state.reset()
        logger.info(
            "CircuitBreaker '{name}' → CLOSED (recovered)",
            name=self.name,
        )

    def record_success(self) -> None:
        """Record a successful request."""
        if self.state.state == CircuitState.HALF_OPEN:
            self.state.record_success()

            # Check if we have enough successes to close the circuit
            if self.state.success_count >= self.config.success_threshold:
                self._transition_to_closed()

        elif self.state.state == CircuitState.CLOSED:
            # Reset failure count on success
            if self.state.failure_count > 0:
                logger.debug(
                    "CircuitBreaker '{name}' resetting failure count "
                    "(was {count})",
                    name=self.name,
                    count=self.state.failure_count,
                )
                self.state.failure_count = 0

    def record_failure(
        self,
        *,
        status_code: Optional[int] = None,
        is_timeout: bool = False,
    ) -> None:
        """
        Record a failed request.

        Args:
            status_code: HTTP status code (if applicable)
            is_timeout: Whether failure was due to timeout
        """
        # Check if this failure should count
        should_count = False

        if is_timeout and self.config.count_timeouts_as_failures:
            should_count = True
        elif status_code and status_code in self.config.failure_status_codes:
            should_count = True

        if not should_count:
            logger.debug(
                "CircuitBreaker '{name}' ignoring failure "
                "(status={status}, timeout={timeout})",
                name=self.name,
                status=status_code,
                timeout=is_timeout,
            )
            return

        self.state.record_failure()

        logger.warning(
            "CircuitBreaker '{name}' recorded failure "
            "(count={count}/{threshold}, status={status}, timeout={timeout})",
            name=self.name,
            count=self.state.failure_count,
            threshold=self.config.failure_threshold,
            status=status_code,
            timeout=is_timeout,
        )

        # Check if we should open the circuit
        if self.state.state == CircuitState.HALF_OPEN:
            # Any failure in half-open state reopens the circuit
            self._transition_to_open()

        elif self.state.state == CircuitState.CLOSED:
            # Check if failure threshold exceeded
            if self.state.failure_count >= self.config.failure_threshold:
                self._transition_to_open()

    async def call(
        self,
        func: Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute (can be async or sync)
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Any exception raised by func
        """
        # Check if we can execute
        if not self._can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN",
                failure_count=self.state.failure_count,
                next_retry_at=self.state.next_retry_at.timestamp()
                if self.state.next_retry_at
                else None,
            )

        try:
            # Execute function (handle both async and sync)
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            self.record_success()

            return result

        except Exception as exc:
            # Determine if this is a failure we should count
            status_code = None
            is_timeout = False

            # Try to extract status code from exception
            if hasattr(exc, "status_code"):
                status_code = exc.status_code
            elif hasattr(exc, "response") and hasattr(exc.response, "status_code"):
                status_code = exc.response.status_code

            # Check if timeout
            if "timeout" in type(exc).__name__.lower():
                is_timeout = True

            # Record failure
            self.record_failure(status_code=status_code, is_timeout=is_timeout)

            # Re-raise exception
            raise

    def __call__(
        self,
        func: Callable[P, R],
    ) -> Callable[P, R]:
        """
        Decorator for wrapping functions with circuit breaker.

        Usage:
            @circuit_breaker
            async def call_api():
                ...
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            return await self.call(func, *args, **kwargs)

        return wrapper

    def reset(self) -> None:
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(
            "CircuitBreaker '{name}' manually reset",
            name=self.name,
        )
        self._transition_to_closed()

    @property
    def is_open(self) -> bool:
        """Check if circuit is currently open."""
        return self.state.state == CircuitState.OPEN

    @property
    def is_closed(self) -> bool:
        """Check if circuit is currently closed."""
        return self.state.state == CircuitState.CLOSED

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is currently half-open."""
        return self.state.state == CircuitState.HALF_OPEN

    @property
    def current_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state.state


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.

    Allows different circuit breakers for different services or endpoints.
    """

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig,
    ) -> CircuitBreaker:
        """
        Get existing circuit breaker or create a new one.

        Args:
            name: Unique identifier for the circuit breaker
            config: Circuit breaker configuration

        Returns:
            Circuit breaker instance
        """
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(config, name=name)
            logger.debug("Created new circuit breaker: {name}", name=name)

        return self._breakers[name]

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get circuit breaker by name.

        Args:
            name: Circuit breaker identifier

        Returns:
            Circuit breaker instance or None if not found
        """
        return self._breakers.get(name)

    def remove(self, name: str) -> bool:
        """
        Remove circuit breaker.

        Args:
            name: Circuit breaker identifier

        Returns:
            True if removed, False if not found
        """
        if name in self._breakers:
            del self._breakers[name]
            logger.debug("Removed circuit breaker: {name}", name=name)
            return True
        return False

    def reset_all(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("Reset all circuit breakers")

    def clear(self) -> None:
        """Remove all circuit breakers."""
        self._breakers.clear()
        logger.debug("Cleared all circuit breakers")


# Global registry instance
_registry = CircuitBreakerRegistry()


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry."""
    return _registry
