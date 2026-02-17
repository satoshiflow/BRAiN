"""
Pydantic schemas for the integrations module.

All configuration and data structures for API clients, authentication,
rate limiting, circuit breakers, and retry logic.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Authentication Schemas
# ============================================================================

class AuthType(str, Enum):
    """Supported authentication types."""
    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    OAUTH2 = "oauth2"
    CUSTOM = "custom"


class AuthLocation(str, Enum):
    """Where to place auth credentials."""
    HEADER = "header"
    QUERY = "query"
    BODY = "body"


class AuthConfig(BaseModel):
    """Authentication configuration."""

    type: AuthType = Field(default=AuthType.NONE, description="Authentication type")

    # API Key / Bearer Token
    token: Optional[str] = Field(default=None, description="API key or bearer token")
    token_location: AuthLocation = Field(default=AuthLocation.HEADER, description="Where to place token")
    token_key: str = Field(default="Authorization", description="Header/query param name for token")
    token_prefix: Optional[str] = Field(default=None, description="Token prefix (e.g., 'Bearer')")

    # Basic Auth
    username: Optional[str] = Field(default=None, description="Username for basic auth")
    password: Optional[str] = Field(default=None, description="Password for basic auth")

    # OAuth 2.0
    client_id: Optional[str] = Field(default=None, description="OAuth client ID")
    client_secret: Optional[str] = Field(default=None, description="OAuth client secret")
    token_url: Optional[str] = Field(default=None, description="OAuth token endpoint")
    refresh_token: Optional[str] = Field(default=None, description="OAuth refresh token")
    access_token: Optional[str] = Field(default=None, description="Current OAuth access token")
    token_expires_at: Optional[datetime] = Field(default=None, description="Access token expiration")
    scopes: List[str] = Field(default_factory=list, description="OAuth scopes")

    # Custom auth
    custom_headers: Dict[str, str] = Field(default_factory=dict, description="Custom auth headers")
    custom_params: Dict[str, str] = Field(default_factory=dict, description="Custom auth params")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "bearer",
                "token": "sk-abc123...",
                "token_location": "header",
                "token_key": "Authorization",
                "token_prefix": "Bearer"
            }
        }


# ============================================================================
# Rate Limiting Schemas
# ============================================================================

class RateLimitConfig(BaseModel):
    """Rate limiter configuration using token bucket algorithm."""

    max_requests: int = Field(
        default=60,
        gt=0,
        description="Maximum requests allowed per window"
    )
    window_seconds: float = Field(
        default=60.0,
        gt=0.0,
        description="Time window in seconds"
    )
    burst_size: Optional[int] = Field(
        default=None,
        description="Maximum burst size (defaults to max_requests if not set)"
    )

    # Advanced settings
    respect_retry_after: bool = Field(
        default=True,
        description="Respect Retry-After headers from API"
    )
    backoff_factor: float = Field(
        default=1.5,
        ge=1.0,
        description="Backoff multiplier when rate limited"
    )

    @field_validator("burst_size", mode="before")
    @classmethod
    def set_burst_default(cls, v: Optional[int], info) -> int:
        """Set burst_size to max_requests if not provided."""
        if v is None:
            # Access max_requests from values
            return info.data.get("max_requests", 60)
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "max_requests": 100,
                "window_seconds": 60.0,
                "burst_size": 120,
                "respect_retry_after": True
            }
        }


# ============================================================================
# Circuit Breaker Schemas
# ============================================================================

class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures exceeded threshold, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = Field(
        default=5,
        gt=0,
        description="Number of failures before opening circuit"
    )
    recovery_timeout: float = Field(
        default=60.0,
        gt=0.0,
        description="Seconds to wait before attempting recovery"
    )
    success_threshold: int = Field(
        default=2,
        gt=0,
        description="Consecutive successes needed to close circuit from half-open"
    )

    # What counts as a failure
    failure_status_codes: List[int] = Field(
        default_factory=lambda: [500, 502, 503, 504],
        description="HTTP status codes that count as failures"
    )
    count_timeouts_as_failures: bool = Field(
        default=True,
        description="Count timeouts as failures"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "failure_threshold": 5,
                "recovery_timeout": 60.0,
                "success_threshold": 2,
                "failure_status_codes": [500, 502, 503, 504]
            }
        }


class CircuitBreakerState(BaseModel):
    """Current state of a circuit breaker."""

    state: CircuitState = Field(default=CircuitState.CLOSED)
    failure_count: int = Field(default=0)
    success_count: int = Field(default=0)
    last_failure_time: Optional[datetime] = Field(default=None)
    next_retry_at: Optional[datetime] = Field(default=None)

    def record_success(self) -> None:
        """Record a successful request."""
        self.success_count += 1
        self.failure_count = 0

    def record_failure(self) -> None:
        """Record a failed request."""
        self.failure_count += 1
        self.success_count = 0
        self.last_failure_time = datetime.now(timezone.utc)

    def reset(self) -> None:
        """Reset to initial state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.next_retry_at = None


# ============================================================================
# Retry Schemas
# ============================================================================

class RetryStrategy(str, Enum):
    """Retry backoff strategies."""
    FIXED = "fixed"            # Fixed delay between retries
    EXPONENTIAL = "exponential"  # Exponential backoff
    LINEAR = "linear"          # Linear backoff


class RetryConfig(BaseModel):
    """Retry handler configuration."""

    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts"
    )
    strategy: RetryStrategy = Field(
        default=RetryStrategy.EXPONENTIAL,
        description="Backoff strategy"
    )

    # Timing
    initial_delay: float = Field(
        default=1.0,
        gt=0.0,
        description="Initial delay in seconds"
    )
    max_delay: float = Field(
        default=60.0,
        gt=0.0,
        description="Maximum delay in seconds"
    )
    backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        description="Multiplier for exponential/linear backoff"
    )
    jitter: bool = Field(
        default=True,
        description="Add random jitter to prevent thundering herd"
    )

    # What to retry
    retry_status_codes: List[int] = Field(
        default_factory=lambda: [408, 429, 500, 502, 503, 504],
        description="HTTP status codes to retry"
    )
    retry_on_timeout: bool = Field(
        default=True,
        description="Retry on timeout errors"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "max_retries": 3,
                "strategy": "exponential",
                "initial_delay": 1.0,
                "max_delay": 60.0,
                "backoff_multiplier": 2.0,
                "jitter": True
            }
        }


# ============================================================================
# API Client Schemas
# ============================================================================

class APIClientConfig(BaseModel):
    """Complete API client configuration."""

    # Basic settings
    name: str = Field(description="Client name/identifier")
    base_url: str = Field(description="Base URL for API")

    # Timeouts
    timeout: float = Field(
        default=30.0,
        gt=0.0,
        description="Request timeout in seconds"
    )
    connect_timeout: float = Field(
        default=10.0,
        gt=0.0,
        description="Connection timeout in seconds"
    )

    # Headers
    default_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Default headers for all requests"
    )

    # Features
    auth: Optional[AuthConfig] = Field(
        default=None,
        description="Authentication configuration"
    )
    rate_limit: Optional[RateLimitConfig] = Field(
        default=None,
        description="Rate limiting configuration"
    )
    circuit_breaker: Optional[CircuitBreakerConfig] = Field(
        default=None,
        description="Circuit breaker configuration"
    )
    retry: Optional[RetryConfig] = Field(
        default=None,
        description="Retry configuration"
    )

    # Logging
    log_requests: bool = Field(
        default=True,
        description="Log all requests"
    )
    log_responses: bool = Field(
        default=True,
        description="Log all responses"
    )
    log_response_body: bool = Field(
        default=False,
        description="Log response bodies (may contain sensitive data)"
    )

    # Connection pooling
    max_connections: int = Field(
        default=100,
        gt=0,
        description="Maximum number of connections in pool"
    )
    max_keepalive_connections: int = Field(
        default=20,
        gt=0,
        description="Maximum number of keepalive connections"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "odoo_client",
                "base_url": "https://api.example.com",
                "timeout": 30.0,
                "auth": {
                    "type": "api_key",
                    "token": "sk-abc123",
                    "token_location": "header"
                },
                "rate_limit": {
                    "max_requests": 100,
                    "window_seconds": 60.0
                },
                "retry": {
                    "max_retries": 3,
                    "strategy": "exponential"
                }
            }
        }


# ============================================================================
# Request/Response Schemas
# ============================================================================

class APIRequest(BaseModel):
    """API request metadata."""

    method: str = Field(description="HTTP method")
    url: str = Field(description="Full request URL")
    headers: Dict[str, str] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)
    body: Optional[Any] = Field(default=None)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class APIResponse(BaseModel):
    """API response metadata."""

    status_code: int = Field(description="HTTP status code")
    headers: Dict[str, str] = Field(default_factory=dict)
    body: Optional[Any] = Field(default=None)
    elapsed_ms: float = Field(description="Response time in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_success(self) -> bool:
        """Check if response is successful (2xx status code)."""
        return 200 <= self.status_code < 300

    @property
    def is_client_error(self) -> bool:
        """Check if response is client error (4xx status code)."""
        return 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """Check if response is server error (5xx status code)."""
        return 500 <= self.status_code < 600


# ============================================================================
# Metrics Schemas
# ============================================================================

class ClientMetrics(BaseModel):
    """API client metrics."""

    total_requests: int = Field(default=0)
    successful_requests: int = Field(default=0)
    failed_requests: int = Field(default=0)

    total_retries: int = Field(default=0)
    rate_limit_hits: int = Field(default=0)
    circuit_breaker_opens: int = Field(default=0)

    average_response_time_ms: float = Field(default=0.0)
    min_response_time_ms: float = Field(default=0.0)
    max_response_time_ms: float = Field(default=0.0)

    first_request_at: Optional[datetime] = Field(default=None)
    last_request_at: Optional[datetime] = Field(default=None)

    def record_request(
        self,
        *,
        success: bool,
        response_time_ms: float,
        retries: int = 0,
        rate_limited: bool = False,
    ) -> None:
        """Record a request in metrics."""
        now = datetime.now(timezone.utc)

        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.total_retries += retries
        if rate_limited:
            self.rate_limit_hits += 1

        # Update response time stats
        if self.total_requests == 1:
            self.average_response_time_ms = response_time_ms
            self.min_response_time_ms = response_time_ms
            self.max_response_time_ms = response_time_ms
        else:
            # Running average
            self.average_response_time_ms = (
                (self.average_response_time_ms * (self.total_requests - 1) + response_time_ms)
                / self.total_requests
            )
            self.min_response_time_ms = min(self.min_response_time_ms, response_time_ms)
            self.max_response_time_ms = max(self.max_response_time_ms, response_time_ms)

        # Update timestamps
        if self.first_request_at is None:
            self.first_request_at = now
        self.last_request_at = now

    def reset(self) -> None:
        """Reset all metrics."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_retries = 0
        self.rate_limit_hits = 0
        self.circuit_breaker_opens = 0
        self.average_response_time_ms = 0.0
        self.min_response_time_ms = 0.0
        self.max_response_time_ms = 0.0
        self.first_request_at = None
        self.last_request_at = None
