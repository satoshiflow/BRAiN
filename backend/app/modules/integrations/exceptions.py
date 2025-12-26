"""
Custom exceptions for the integrations module.

These exceptions provide specific error handling for API client operations,
following BRAiN's defensive programming principles.
"""

from typing import Optional, Dict, Any


class IntegrationError(Exception):
    """Base exception for all integration errors."""

    def __init__(
        self,
        message: str,
        *,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.details = details or {}
        self.cause = cause


class AuthenticationError(IntegrationError):
    """Raised when authentication fails."""
    pass


class RateLimitExceededError(IntegrationError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        *,
        retry_after: Optional[float] = None,
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class CircuitBreakerOpenError(IntegrationError):
    """Raised when circuit breaker is open."""

    def __init__(
        self,
        message: str = "Circuit breaker is open",
        *,
        failure_count: int = 0,
        next_retry_at: Optional[float] = None,
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)
        self.failure_count = failure_count
        self.next_retry_at = next_retry_at


class RetryExhaustedError(IntegrationError):
    """Raised when all retry attempts are exhausted."""

    def __init__(
        self,
        message: str = "All retry attempts exhausted",
        *,
        attempts: int = 0,
        last_error: Optional[Exception] = None,
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)
        self.attempts = attempts
        self.last_error = last_error


class APIError(IntegrationError):
    """Raised when API returns an error response."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.response_body = response_body


class ConfigurationError(IntegrationError):
    """Raised when configuration is invalid."""
    pass


class TimeoutError(IntegrationError):
    """Raised when request times out."""

    def __init__(
        self,
        message: str = "Request timed out",
        *,
        timeout: Optional[float] = None,
        **kwargs
    ) -> None:
        super().__init__(message, **kwargs)
        self.timeout = timeout
