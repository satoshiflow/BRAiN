"""
Self-Healing Protocol - Automatic recovery and health monitoring

Provides retry mechanisms, health checks, circuit breakers, and automatic
recovery for resilient operation.
"""

from __future__ import annotations

import time
import asyncio
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Dict, List
from enum import Enum
from threading import Lock
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DOWN = "down"
    RECOVERING = "recovering"


class CircuitState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


@dataclass
class HealthCheckConfig:
    """Configuration for health checks"""
    interval: float = 30.0  # seconds
    timeout: float = 5.0
    failure_threshold: int = 3
    success_threshold: int = 2


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 60.0  # seconds before attempting recovery
    half_open_max_calls: int = 3


@dataclass
class ServiceHealth:
    """Health status of a service"""
    service_name: str
    status: ServiceStatus
    last_check: float
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_checks: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def update_success(self) -> None:
        """Update health after successful check"""
        self.consecutive_successes += 1
        self.consecutive_failures = 0
        self.last_check = time.time()
        self.total_checks += 1

        if self.consecutive_successes >= 2:
            self.status = ServiceStatus.HEALTHY
        elif self.status == ServiceStatus.RECOVERING:
            self.status = ServiceStatus.DEGRADED

    def update_failure(self) -> None:
        """Update health after failed check"""
        self.consecutive_failures += 1
        self.consecutive_successes = 0
        self.last_check = time.time()
        self.total_checks += 1

        if self.consecutive_failures >= 3:
            self.status = ServiceStatus.DOWN
        elif self.consecutive_failures >= 2:
            self.status = ServiceStatus.UNHEALTHY
        else:
            self.status = ServiceStatus.DEGRADED


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for service protection

    States:
    - CLOSED: Normal operation, requests allowed
    - OPEN: Too many failures, reject requests
    - HALF_OPEN: Testing if service recovered
    """

    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0
        self._lock = Lock()

        logger.info(f"Circuit breaker '{name}' initialized")

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if (
                self._state == CircuitState.OPEN
                and self._last_failure_time is not None
                and time.time() - self._last_failure_time >= self.config.timeout
            ):
                logger.info(f"Circuit breaker '{self.name}': OPEN -> HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0

            return self._state

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker

        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is OPEN or function fails
        """
        if self.state == CircuitState.OPEN:
            raise Exception(f"Circuit breaker '{self.name}' is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise Exception(
                        f"Circuit breaker '{self.name}' half-open call limit reached"
                    )
                self._half_open_calls += 1

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Async version of call"""
        if self.state == CircuitState.OPEN:
            raise Exception(f"Circuit breaker '{self.name}' is OPEN")

        if self.state == CircuitState.HALF_OPEN:
            with self._lock:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise Exception(
                        f"Circuit breaker '{self.name}' half-open call limit reached"
                    )
                self._half_open_calls += 1

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call"""
        with self._lock:
            self._failure_count = 0
            self._success_count += 1

            if self._state == CircuitState.HALF_OPEN:
                if self._success_count >= self.config.success_threshold:
                    logger.info(f"Circuit breaker '{self.name}': HALF_OPEN -> CLOSED")
                    self._state = CircuitState.CLOSED
                    self._success_count = 0

    def _on_failure(self) -> None:
        """Handle failed call"""
        with self._lock:
            self._failure_count += 1
            self._success_count = 0
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker '{self.name}': HALF_OPEN -> OPEN")
                self._state = CircuitState.OPEN
            elif self._failure_count >= self.config.failure_threshold:
                logger.warning(f"Circuit breaker '{self.name}': CLOSED -> OPEN")
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset circuit breaker"""
        with self._lock:
            logger.info(f"Circuit breaker '{self.name}' manually reset")
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._half_open_calls = 0


class SelfHealingManager:
    """
    Self-healing manager for automatic recovery and health monitoring

    Features:
    - Retry mechanisms with exponential backoff
    - Health checks for services
    - Circuit breakers for failing services
    - Automatic recovery attempts
    - Fallback strategies
    """

    def __init__(self):
        self._lock = Lock()
        self._health_checks: Dict[str, ServiceHealth] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._recovery_handlers: Dict[str, List[Callable]] = {}

        logger.info("SelfHealingManager initialized")

    def retry_with_backoff(
        self,
        func: Callable,
        config: Optional[RetryConfig] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Retry function with exponential backoff

        Args:
            func: Function to retry
            config: Retry configuration
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If all retries exhausted
        """
        config = config or RetryConfig()
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                logger.debug(
                    f"Retry attempt {attempt + 1}/{config.max_attempts} "
                    f"for {func.__name__}"
                )
                return func(*args, **kwargs)
            except config.retryable_exceptions as e:
                last_exception = e

                if attempt < config.max_attempts - 1:
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    # Add jitter
                    if config.jitter:
                        import random
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"All {config.max_attempts} retry attempts failed "
                        f"for {func.__name__}"
                    )

        raise last_exception

    async def retry_with_backoff_async(
        self,
        func: Callable,
        config: Optional[RetryConfig] = None,
        *args,
        **kwargs
    ) -> Any:
        """Async version of retry_with_backoff"""
        config = config or RetryConfig()
        last_exception = None

        for attempt in range(config.max_attempts):
            try:
                logger.debug(
                    f"Async retry attempt {attempt + 1}/{config.max_attempts} "
                    f"for {func.__name__}"
                )
                return await func(*args, **kwargs)
            except config.retryable_exceptions as e:
                last_exception = e

                if attempt < config.max_attempts - 1:
                    delay = min(
                        config.base_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )

                    if config.jitter:
                        import random
                        delay = delay * (0.5 + random.random() * 0.5)

                    logger.warning(
                        f"Async attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"All {config.max_attempts} async retry attempts failed "
                        f"for {func.__name__}"
                    )

        raise last_exception

    def register_health_check(
        self,
        service_name: str,
        check_func: Callable[[], bool],
        config: Optional[HealthCheckConfig] = None
    ) -> None:
        """
        Register a health check for a service

        Args:
            service_name: Name of service to monitor
            check_func: Function returning True if healthy
            config: Health check configuration
        """
        with self._lock:
            self._health_checks[service_name] = ServiceHealth(
                service_name=service_name,
                status=ServiceStatus.HEALTHY,
                last_check=time.time()
            )

        logger.info(f"Registered health check for service: {service_name}")

    def perform_health_check(self, service_name: str, check_func: Callable) -> bool:
        """
        Perform health check for a service

        Args:
            service_name: Service to check
            check_func: Health check function

        Returns:
            True if healthy
        """
        with self._lock:
            if service_name not in self._health_checks:
                self._health_checks[service_name] = ServiceHealth(
                    service_name=service_name,
                    status=ServiceStatus.HEALTHY,
                    last_check=time.time()
                )

            health = self._health_checks[service_name]

        try:
            is_healthy = check_func()

            if is_healthy:
                health.update_success()
                logger.debug(f"Health check passed for {service_name}")
                return True
            else:
                health.update_failure()
                logger.warning(f"Health check failed for {service_name}")
                return False
        except Exception as e:
            health.update_failure()
            logger.error(f"Health check error for {service_name}: {e}")
            return False

    def get_circuit_breaker(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker

        Args:
            name: Circuit breaker name
            config: Configuration (only used if creating new)

        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if name not in self._circuit_breakers:
                self._circuit_breakers[name] = CircuitBreaker(name, config)
            return self._circuit_breakers[name]

    def register_recovery_handler(
        self,
        service_name: str,
        handler: Callable[[ServiceHealth], bool]
    ) -> None:
        """
        Register recovery handler for a service

        Args:
            service_name: Service to handle
            handler: Recovery function returning True if successful
        """
        with self._lock:
            if service_name not in self._recovery_handlers:
                self._recovery_handlers[service_name] = []
            self._recovery_handlers[service_name].append(handler)

        logger.info(f"Registered recovery handler for {service_name}")

    def attempt_recovery(self, service_name: str) -> bool:
        """
        Attempt to recover a service

        Args:
            service_name: Service to recover

        Returns:
            True if recovery successful
        """
        if service_name not in self._health_checks:
            logger.warning(f"No health check registered for {service_name}")
            return False

        health = self._health_checks[service_name]
        health.status = ServiceStatus.RECOVERING

        handlers = self._recovery_handlers.get(service_name, [])

        for handler in handlers:
            try:
                logger.info(f"Attempting recovery for {service_name}: {handler.__name__}")
                success = handler(health)

                if success:
                    health.status = ServiceStatus.HEALTHY
                    health.consecutive_failures = 0
                    logger.info(f"Recovery successful for {service_name}")
                    return True
            except Exception as e:
                logger.error(f"Recovery handler failed for {service_name}: {e}")

        logger.warning(f"All recovery attempts failed for {service_name}")
        health.status = ServiceStatus.DOWN
        return False

    def get_system_health(self) -> Dict:
        """Get overall system health status"""
        with self._lock:
            if not self._health_checks:
                return {
                    "status": "unknown",
                    "services": {},
                    "circuit_breakers": {}
                }

            services = {}
            for name, health in self._health_checks.items():
                services[name] = {
                    "status": health.status.value,
                    "last_check": health.last_check,
                    "consecutive_failures": health.consecutive_failures,
                    "total_checks": health.total_checks
                }

            circuit_breakers = {}
            for name, cb in self._circuit_breakers.items():
                circuit_breakers[name] = {
                    "state": cb.state.value
                }

            # Overall status
            statuses = [h.status for h in self._health_checks.values()]
            if all(s == ServiceStatus.HEALTHY for s in statuses):
                overall = "healthy"
            elif any(s == ServiceStatus.DOWN for s in statuses):
                overall = "degraded"
            elif any(s == ServiceStatus.UNHEALTHY for s in statuses):
                overall = "unhealthy"
            else:
                overall = "healthy"

            return {
                "status": overall,
                "services": services,
                "circuit_breakers": circuit_breakers
            }


# Singleton instance
_self_healing_manager: Optional[SelfHealingManager] = None
_manager_lock = Lock()


def get_self_healing_manager() -> SelfHealingManager:
    """Get or create the global self-healing manager instance"""
    global _self_healing_manager

    with _manager_lock:
        if _self_healing_manager is None:
            _self_healing_manager = SelfHealingManager()
        return _self_healing_manager


# Decorators for easy integration

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: tuple = (Exception,)
):
    """
    Decorator to add retry logic to functions

    Args:
        max_attempts: Maximum retry attempts
        base_delay: Base delay between retries
        retryable_exceptions: Exceptions to retry on
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                retryable_exceptions=retryable_exceptions
            )
            manager = get_self_healing_manager()
            return manager.retry_with_backoff(func, config, *args, **kwargs)
        return wrapper
    return decorator


def with_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator to add circuit breaker protection to functions

    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_self_healing_manager()
            cb = manager.get_circuit_breaker(name, config)
            return cb.call(func, *args, **kwargs)
        return wrapper
    return decorator
