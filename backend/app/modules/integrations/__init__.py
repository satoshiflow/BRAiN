"""
BRAiN Integrations Module - Generic API Client Framework

This module provides a robust foundation for all external integrations with:
- BaseAPIClient: Abstract base class for API clients
- AuthenticationManager: Multiple authentication types (API Key, OAuth2, Basic, etc.)
- RateLimiter: Token bucket algorithm with burst support
- CircuitBreaker: Resilience pattern with three states
- RetryHandler: Exponential backoff with jitter

Usage:
    from backend.app.modules.integrations import (
        BaseAPIClient,
        APIClientConfig,
        AuthConfig,
        AuthType,
        create_api_key_auth,
    )

    # Configure client
    config = APIClientConfig(
        name="my_api",
        base_url="https://api.example.com",
        auth=AuthConfig(type=AuthType.API_KEY, token="sk-abc123"),
        rate_limit=RateLimitConfig(max_requests=100, window_seconds=60),
        retry=RetryConfig(max_retries=3),
    )

    # Create custom client
    class MyAPIClient(BaseAPIClient):
        async def _build_base_url(self) -> str:
            return self.config.base_url

        async def get_users(self):
            response = await self.get("/users")
            return response.body

    # Use client
    async with MyAPIClient(config).session():
        users = await client.get_users()
"""

# Core base client
from .base_client import BaseAPIClient

# Authentication
from .auth import (
    AuthenticationManager,
    create_api_key_auth,
    create_bearer_auth,
    create_basic_auth,
    create_oauth2_auth,
)

# Rate limiting
from .rate_limit import (
    RateLimiter,
    TokenBucket,
    RateLimiterRegistry,
    get_rate_limiter_registry,
)

# Circuit breaker
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerRegistry,
    get_circuit_breaker_registry,
)

# Retry logic
from .retry import (
    RetryHandler,
    create_retry_handler,
)

# Schemas
from .schemas import (
    # Config
    APIClientConfig,
    AuthConfig,
    RateLimitConfig,
    CircuitBreakerConfig,
    RetryConfig,
    # Enums
    AuthType,
    AuthLocation,
    CircuitState,
    RetryStrategy,
    # State
    CircuitBreakerState,
    # Request/Response
    APIRequest,
    APIResponse,
    # Metrics
    ClientMetrics,
)

# Exceptions
from .exceptions import (
    IntegrationError,
    AuthenticationError,
    RateLimitExceededError,
    CircuitBreakerOpenError,
    RetryExhaustedError,
    APIError,
    ConfigurationError,
    TimeoutError,
)

__all__ = [
    # Core
    "BaseAPIClient",
    # Authentication
    "AuthenticationManager",
    "create_api_key_auth",
    "create_bearer_auth",
    "create_basic_auth",
    "create_oauth2_auth",
    # Rate limiting
    "RateLimiter",
    "TokenBucket",
    "RateLimiterRegistry",
    "get_rate_limiter_registry",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "get_circuit_breaker_registry",
    # Retry
    "RetryHandler",
    "create_retry_handler",
    # Schemas - Config
    "APIClientConfig",
    "AuthConfig",
    "RateLimitConfig",
    "CircuitBreakerConfig",
    "RetryConfig",
    # Schemas - Enums
    "AuthType",
    "AuthLocation",
    "CircuitState",
    "RetryStrategy",
    # Schemas - State
    "CircuitBreakerState",
    # Schemas - Request/Response
    "APIRequest",
    "APIResponse",
    # Schemas - Metrics
    "ClientMetrics",
    # Exceptions
    "IntegrationError",
    "AuthenticationError",
    "RateLimitExceededError",
    "CircuitBreakerOpenError",
    "RetryExhaustedError",
    "APIError",
    "ConfigurationError",
    "TimeoutError",
]

__version__ = "1.0.0"
