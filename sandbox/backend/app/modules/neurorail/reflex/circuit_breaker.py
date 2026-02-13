"""
Circuit Breaker (Phase 2 Reflex).

Implements circuit breaker pattern to prevent cascading failures.
States: CLOSED → OPEN → HALF_OPEN → CLOSED

Integrates with immune system and Prometheus metrics.
"""

import time
from typing import Callable, Any, Optional, Dict
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger

from app.modules.neurorail.errors import (
    ReflexCircuitOpenError,
    NeuroRailErrorCode,
    should_alert_immune,
)


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Circuit is open, requests are rejected
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    """Number of failures before opening circuit."""

    recovery_timeout: float = 60.0
    """Seconds to wait before transitioning to HALF_OPEN."""

    success_threshold: int = 2
    """Number of successes in HALF_OPEN before closing circuit."""

    half_open_max_calls: int = 3
    """Maximum calls allowed in HALF_OPEN state."""


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker."""
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change_time: float = field(default_factory=time.time)
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    open_count: int = 0
    half_open_calls: int = 0


class CircuitBreaker:
    """
    Circuit breaker for preventing cascading failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Circuit is open, requests are rejected immediately
    - HALF_OPEN: Testing if service recovered (limited requests)

    Transitions:
    - CLOSED → OPEN: When failure_threshold exceeded
    - OPEN → HALF_OPEN: After recovery_timeout
    - HALF_OPEN → CLOSED: After success_threshold successes
    - HALF_OPEN → OPEN: On any failure

    Features:
    - Failure threshold detection
    - Automatic recovery probing
    - Success threshold for recovery
    - Immune system integration
    - Prometheus metrics tracking

    Usage:
        breaker = CircuitBreaker(
            circuit_id="external_api",
            config=CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0)
        )

        async def risky_operation():
            # Call external service
            return await external_api.call()

        try:
            result = await breaker.call(risky_operation)
        except ReflexCircuitOpenError:
            logger.error("Circuit is open, request rejected")
    """

    def __init__(
        self,
        circuit_id: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        """
        Initialize circuit breaker.

        Args:
            circuit_id: Unique identifier for this circuit
            config: Circuit breaker configuration
        """
        self.circuit_id = circuit_id
        self.config = config or CircuitBreakerConfig()
        self.metrics = CircuitBreakerMetrics()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self.metrics.state

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset to HALF_OPEN."""
        if self.metrics.state != CircuitState.OPEN:
            return False

        if self.metrics.last_failure_time is None:
            return False

        elapsed = time.time() - self.metrics.last_failure_time
        return elapsed >= self.config.recovery_timeout

    def _transition_to(self, new_state: CircuitState, reason: str):
        """
        Transition circuit to new state.

        Args:
            new_state: Target state
            reason: Reason for transition
        """
        old_state = self.metrics.state

        if old_state == new_state:
            return

        logger.info(
            f"Circuit {self.circuit_id} transitioning: {old_state} → {new_state}",
            extra={
                "circuit_id": self.circuit_id,
                "from_state": old_state,
                "to_state": new_state,
                "reason": reason,
            }
        )

        self.metrics.state = new_state
        self.metrics.last_state_change_time = time.time()

        # Reset counters on state change
        if new_state == CircuitState.HALF_OPEN:
            self.metrics.half_open_calls = 0
            self.metrics.success_count = 0
        elif new_state == CircuitState.OPEN:
            self.metrics.open_count += 1

    async def call(
        self,
        func: Callable[[], Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async callable to execute
            context: Optional context for error enrichment

        Returns:
            Function result

        Raises:
            ReflexCircuitOpenError: If circuit is open
            Exception: Original exception from func
        """
        context = context or {}

        # Check if circuit should attempt reset
        if self._should_attempt_reset():
            self._transition_to(
                CircuitState.HALF_OPEN,
                f"Recovery timeout ({self.config.recovery_timeout}s) elapsed"
            )

        # Handle OPEN state
        if self.metrics.state == CircuitState.OPEN:
            logger.warning(
                f"Circuit {self.circuit_id} is OPEN, rejecting request",
                extra={"circuit_id": self.circuit_id, "context": context}
            )

            # Check immune alert
            immune_alert = should_alert_immune(NeuroRailErrorCode.REFLEX_CIRCUIT_OPEN)

            raise ReflexCircuitOpenError(
                circuit_id=self.circuit_id,
                details={
                    **context,
                    "state": self.metrics.state,
                    "failure_count": self.metrics.failure_count,
                    "last_failure_time": self.metrics.last_failure_time,
                    "immune_alert": immune_alert,
                },
            )

        # Handle HALF_OPEN state
        if self.metrics.state == CircuitState.HALF_OPEN:
            if self.metrics.half_open_calls >= self.config.half_open_max_calls:
                logger.warning(
                    f"Circuit {self.circuit_id} HALF_OPEN limit reached, rejecting request",
                    extra={
                        "circuit_id": self.circuit_id,
                        "half_open_calls": self.metrics.half_open_calls,
                        "max_calls": self.config.half_open_max_calls,
                    }
                )

                # Reject request (don't transition to OPEN, just limit calls)
                immune_alert = should_alert_immune(NeuroRailErrorCode.REFLEX_CIRCUIT_OPEN)

                raise ReflexCircuitOpenError(
                    circuit_id=self.circuit_id,
                    details={
                        **context,
                        "state": self.metrics.state,
                        "half_open_calls": self.metrics.half_open_calls,
                        "immune_alert": immune_alert,
                    },
                )

            self.metrics.half_open_calls += 1

        # Execute function
        self.metrics.total_calls += 1

        try:
            result = await func()

            # Success
            self.metrics.total_successes += 1
            self._handle_success()

            return result

        except Exception as e:
            # Failure
            self.metrics.total_failures += 1
            self._handle_failure(e)

            raise

    def _handle_success(self):
        """Handle successful call."""
        if self.metrics.state == CircuitState.HALF_OPEN:
            self.metrics.success_count += 1

            logger.debug(
                f"Circuit {self.circuit_id} HALF_OPEN success: {self.metrics.success_count}/{self.config.success_threshold}",
                extra={
                    "circuit_id": self.circuit_id,
                    "success_count": self.metrics.success_count,
                    "success_threshold": self.config.success_threshold,
                }
            )

            # Check if we should close circuit
            if self.metrics.success_count >= self.config.success_threshold:
                self._transition_to(
                    CircuitState.CLOSED,
                    f"Success threshold ({self.config.success_threshold}) reached"
                )
                self.metrics.failure_count = 0

        elif self.metrics.state == CircuitState.CLOSED:
            # Reset failure count on success in CLOSED state
            if self.metrics.failure_count > 0:
                logger.debug(
                    f"Circuit {self.circuit_id} resetting failure count after success",
                    extra={"circuit_id": self.circuit_id}
                )
                self.metrics.failure_count = 0

    def _handle_failure(self, exception: Exception):
        """Handle failed call."""
        self.metrics.failure_count += 1
        self.metrics.last_failure_time = time.time()

        logger.warning(
            f"Circuit {self.circuit_id} failure: {self.metrics.failure_count}/{self.config.failure_threshold}",
            extra={
                "circuit_id": self.circuit_id,
                "failure_count": self.metrics.failure_count,
                "failure_threshold": self.config.failure_threshold,
                "exception": str(exception),
            }
        )

        if self.metrics.state == CircuitState.HALF_OPEN:
            # Any failure in HALF_OPEN → back to OPEN
            self._transition_to(
                CircuitState.OPEN,
                f"Failure in HALF_OPEN state: {exception}"
            )
            self.metrics.failure_count = 0

        elif self.metrics.state == CircuitState.CLOSED:
            # Check if threshold exceeded
            if self.metrics.failure_count >= self.config.failure_threshold:
                self._transition_to(
                    CircuitState.OPEN,
                    f"Failure threshold ({self.config.failure_threshold}) exceeded"
                )

    def reset(self):
        """Manually reset circuit to CLOSED state."""
        logger.info(
            f"Circuit {self.circuit_id} manually reset to CLOSED",
            extra={"circuit_id": self.circuit_id}
        )
        self._transition_to(CircuitState.CLOSED, "Manual reset")
        self.metrics.failure_count = 0
        self.metrics.success_count = 0

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get circuit breaker metrics.

        Returns:
            Dictionary with current metrics
        """
        return {
            "circuit_id": self.circuit_id,
            "state": self.metrics.state,
            "failure_count": self.metrics.failure_count,
            "success_count": self.metrics.success_count,
            "total_calls": self.metrics.total_calls,
            "total_failures": self.metrics.total_failures,
            "total_successes": self.metrics.total_successes,
            "open_count": self.metrics.open_count,
            "last_failure_time": self.metrics.last_failure_time,
            "last_state_change_time": self.metrics.last_state_change_time,
        }


# Circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    circuit_id: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> CircuitBreaker:
    """
    Get or create circuit breaker for circuit_id.

    Args:
        circuit_id: Unique identifier for this circuit
        config: Optional configuration (only used when creating new circuit)

    Returns:
        CircuitBreaker instance
    """
    if circuit_id not in _circuit_breakers:
        _circuit_breakers[circuit_id] = CircuitBreaker(circuit_id, config)
    return _circuit_breakers[circuit_id]
