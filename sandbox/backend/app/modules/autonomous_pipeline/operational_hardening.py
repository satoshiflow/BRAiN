"""
Operational Hardening (Sprint 9-D)

Retry policies, circuit breakers, and unified error taxonomy.
No silent failures - every error is classified and handled.
"""

from typing import Optional, Callable, Any, Dict
from enum import Enum
import time
import asyncio
from loguru import logger


# ============================================================================
# Error Taxonomy
# ============================================================================

class ErrorCategory(str, Enum):
    """
    Unified error taxonomy for pipeline execution.

    All errors must be categorized - no silent failures.
    """

    # Governance & Policy
    GOVERNANCE_VIOLATION = "governance_violation"
    BUDGET_EXCEEDED = "budget_exceeded"
    APPROVAL_REQUIRED = "approval_required"
    QUOTA_EXCEEDED = "quota_exceeded"

    # External Dependencies
    EXTERNAL_DEPENDENCY_FAILED = "external_dependency_failed"
    DNS_SERVICE_ERROR = "dns_service_error"
    ODOO_SERVICE_ERROR = "odoo_service_error"
    WEBGENESIS_SERVICE_ERROR = "webgenesis_service_error"

    # Network & Connectivity
    NETWORK_TIMEOUT = "network_timeout"
    NETWORK_CONNECTION_ERROR = "network_connection_error"
    NETWORK_RATE_LIMIT = "network_rate_limit"

    # Data & Validation
    INVALID_INPUT = "invalid_input"
    SCHEMA_VALIDATION_ERROR = "schema_validation_error"
    CONTRACT_VERIFICATION_FAILED = "contract_verification_failed"

    # Execution
    NODE_EXECUTION_FAILED = "node_execution_failed"
    GRAPH_CONSTRUCTION_FAILED = "graph_construction_failed"
    CYCLIC_DEPENDENCY = "cyclic_dependency"
    ROLLBACK_FAILED = "rollback_failed"

    # Storage & Resources
    STORAGE_ERROR = "storage_error"
    INSUFFICIENT_RESOURCES = "insufficient_resources"

    # Unknown
    UNKNOWN_ERROR = "unknown_error"


class PipelineError(Exception):
    """
    Base exception for pipeline errors with taxonomy.

    All pipeline exceptions should extend this class.
    """

    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        retryable: bool = False,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize pipeline error.

        Args:
            message: Error message
            category: Error category from taxonomy
            retryable: Whether error is retryable
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.retryable = retryable
        self.details = details or {}

    def __str__(self):
        return f"[{self.category.value}] {self.message}"


class GovernanceError(PipelineError):
    """Governance violation error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.GOVERNANCE_VIOLATION,
            retryable=False,
            details=details,
        )


class BudgetError(PipelineError):
    """Budget exceeded error."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.BUDGET_EXCEEDED,
            retryable=False,
            details=details,
        )


class ExternalDependencyError(PipelineError):
    """External dependency failure (retryable)."""

    def __init__(self, message: str, service: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["service"] = service
        super().__init__(
            message=message,
            category=ErrorCategory.EXTERNAL_DEPENDENCY_FAILED,
            retryable=True,  # External errors are often transient
            details=details,
        )


class NetworkError(PipelineError):
    """Network error (retryable)."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            category=ErrorCategory.NETWORK_CONNECTION_ERROR,
            retryable=True,
            details=details,
        )


# ============================================================================
# Retry Policy
# ============================================================================

class RetryPolicy:
    """
    Exponential backoff retry policy.

    Features:
    - Configurable max retries
    - Exponential backoff with jitter
    - Selective retry based on error type
    - Async support
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Base delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Exponential backoff base
            jitter: Add random jitter to delay
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt with exponential backoff.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: base_delay * (exponential_base ^ attempt)
        delay = self.base_delay * (self.exponential_base ** attempt)

        # Cap at max_delay
        delay = min(delay, self.max_delay)

        # Add jitter (±20%)
        if self.jitter:
            import random
            jitter_factor = random.uniform(0.8, 1.2)
            delay *= jitter_factor

        return delay

    def _should_retry(self, error: Exception) -> bool:
        """
        Determine if error should be retried.

        Args:
            error: Exception raised

        Returns:
            True if should retry
        """
        # If error is a PipelineError, check retryable flag
        if isinstance(error, PipelineError):
            return error.retryable

        # Default: retry on common transient errors
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )

        return isinstance(error, retryable_errors)

    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with retry policy (async).

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: Last exception if all retries failed
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                # Execute function
                result = await func(*args, **kwargs)
                return result

            except Exception as e:
                last_exception = e

                # Check if should retry
                if not self._should_retry(e):
                    logger.warning(f"[Retry] Error not retryable: {e}")
                    raise

                # Check if we have retries left
                if attempt >= self.max_retries:
                    logger.error(
                        f"[Retry] Max retries ({self.max_retries}) exceeded. Last error: {e}"
                    )
                    raise

                # Calculate delay
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"[Retry] Attempt {attempt + 1}/{self.max_retries} failed: {e}. "
                    f"Retrying in {delay:.2f}s..."
                )

                # Wait before retry
                await asyncio.sleep(delay)

        # Should not reach here, but raise last exception just in case
        raise last_exception


# ============================================================================
# Circuit Breaker
# ============================================================================

class CircuitState(str, Enum):
    """Circuit breaker state."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failure threshold exceeded, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpen(PipelineError):
    """Exception raised when circuit breaker is open."""

    def __init__(self, service: str, details: Optional[Dict[str, Any]] = None):
        details = details or {}
        details["service"] = service
        super().__init__(
            message=f"Circuit breaker OPEN for service: {service}",
            category=ErrorCategory.EXTERNAL_DEPENDENCY_FAILED,
            retryable=False,
            details=details,
        )


class CircuitBreaker:
    """
    Circuit breaker for external services.

    Prevents cascading failures by stopping requests to failing services.

    States:
    - CLOSED: Normal operation, requests allowed
    - OPEN: Too many failures, requests rejected
    - HALF_OPEN: Testing recovery, limited requests allowed
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            service_name: Name of protected service
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to count as failure
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        # State
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.success_count_half_open = 0

    def _should_attempt_reset(self) -> bool:
        """Check if should attempt to reset circuit."""
        if self.state != CircuitState.OPEN:
            return False

        if self.last_failure_time is None:
            return False

        # Check if recovery timeout elapsed
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout

    async def call(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs,
    ) -> Any:
        """
        Call function through circuit breaker (async).

        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception if call fails
        """
        # Check if should attempt reset
        if self._should_attempt_reset():
            logger.info(f"[CircuitBreaker] {self.service_name} transitioning to HALF_OPEN")
            self.state = CircuitState.HALF_OPEN
            self.success_count_half_open = 0

        # Check current state
        if self.state == CircuitState.OPEN:
            logger.warning(f"[CircuitBreaker] {self.service_name} is OPEN. Request rejected.")
            raise CircuitBreakerOpen(
                service=self.service_name,
                details={
                    "failure_count": self.failure_count,
                    "last_failure_time": self.last_failure_time,
                },
            )

        # Attempt call
        try:
            result = await func(*args, **kwargs)

            # Success
            self._on_success()
            return result

        except self.expected_exception as e:
            # Failure
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count_half_open += 1

            # If enough successes in HALF_OPEN, close circuit
            if self.success_count_half_open >= 2:
                logger.info(
                    f"[CircuitBreaker] {self.service_name} recovered. Transitioning to CLOSED."
                )
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.last_failure_time = None

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Immediate transition back to OPEN
            logger.warning(
                f"[CircuitBreaker] {self.service_name} still failing. Transitioning back to OPEN."
            )
            self.state = CircuitState.OPEN

        elif self.state == CircuitState.CLOSED:
            # Check if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    f"[CircuitBreaker] {self.service_name} failure threshold exceeded "
                    f"({self.failure_count}/{self.failure_threshold}). Opening circuit."
                )
                self.state = CircuitState.OPEN


# ============================================================================
# Circuit Breaker Registry
# ============================================================================

class CircuitBreakerRegistry:
    """
    Global registry for circuit breakers.

    Manages circuit breakers for all external services.
    """

    def __init__(self):
        """Initialize circuit breaker registry."""
        self.breakers: Dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
    ) -> CircuitBreaker:
        """
        Get or create circuit breaker for service.

        Args:
            service_name: Service name
            failure_threshold: Failure threshold
            recovery_timeout: Recovery timeout

        Returns:
            CircuitBreaker instance
        """
        if service_name not in self.breakers:
            self.breakers[service_name] = CircuitBreaker(
                service_name=service_name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
            )
            logger.info(
                f"[CircuitBreaker] Created breaker for {service_name} "
                f"(threshold={failure_threshold}, timeout={recovery_timeout}s)"
            )

        return self.breakers[service_name]

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics for all circuit breakers.

        Returns:
            Dictionary of breaker stats
        """
        return {
            name: {
                "state": breaker.state.value,
                "failure_count": breaker.failure_count,
                "last_failure_time": breaker.last_failure_time,
            }
            for name, breaker in self.breakers.items()
        }


# Singleton registry
_circuit_breaker_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get singleton circuit breaker registry."""
    global _circuit_breaker_registry
    if _circuit_breaker_registry is None:
        _circuit_breaker_registry = CircuitBreakerRegistry()
    return _circuit_breaker_registry
