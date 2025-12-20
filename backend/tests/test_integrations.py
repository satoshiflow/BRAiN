"""
Tests for the integrations module (Generic API Client Framework).

Tests cover:
- RateLimiter with token bucket algorithm
- CircuitBreaker with three states
- RetryHandler with exponential backoff
- AuthenticationManager with multiple auth types
- BaseAPIClient integration
"""

import sys
import os
import asyncio
import time
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.app.modules.integrations import (
    # Core
    BaseAPIClient,
    # Auth
    AuthenticationManager,
    create_api_key_auth,
    create_bearer_auth,
    create_basic_auth,
    # Rate limiting
    RateLimiter,
    TokenBucket,
    # Circuit breaker
    CircuitBreaker,
    # Retry
    RetryHandler,
    # Schemas
    APIClientConfig,
    AuthConfig,
    AuthType,
    AuthLocation,
    RateLimitConfig,
    CircuitBreakerConfig,
    CircuitState,
    RetryConfig,
    RetryStrategy,
    # Exceptions
    RateLimitExceededError,
    CircuitBreakerOpenError,
    RetryExhaustedError,
    AuthenticationError,
)


# ============================================================================
# Rate Limiter Tests
# ============================================================================

class TestTokenBucket:
    """Test token bucket algorithm."""

    def test_initial_tokens(self):
        """Test bucket starts with max tokens."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)
        assert bucket.available_tokens == 10.0

    def test_consume_tokens(self):
        """Test consuming tokens."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)

        assert bucket.consume(5) is True
        assert bucket.available_tokens == 5.0

        assert bucket.consume(3) is True
        assert bucket.available_tokens == 2.0

    def test_consume_too_many_tokens(self):
        """Test consuming more tokens than available fails."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)

        bucket.consume(8)
        assert bucket.consume(5) is False  # Only 2 tokens left

    def test_token_refill(self):
        """Test tokens refill over time."""
        bucket = TokenBucket(max_tokens=10, refill_rate=10.0)  # 10/second

        # Consume all tokens
        bucket.consume(10)
        assert bucket.available_tokens == 0.0

        # Wait 0.5 seconds (should add 5 tokens)
        time.sleep(0.5)
        available = bucket.available_tokens
        assert 4.0 <= available <= 6.0  # Allow some timing variance

    def test_burst_size(self):
        """Test burst size limits."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0, burst_size=5)

        # Even if refill_rate is high, burst_size limits maximum
        assert bucket.available_tokens == 5.0  # Limited by burst_size

    def test_wait_time_calculation(self):
        """Test wait time calculation."""
        bucket = TokenBucket(max_tokens=10, refill_rate=1.0)  # 1/second

        bucket.consume(10)  # Consume all

        # Need 5 tokens, should take 5 seconds
        wait_time = bucket.get_wait_time(5)
        assert 4.9 <= wait_time <= 5.1  # Allow small variance


class TestRateLimiter:
    """Test rate limiter."""

    @pytest.mark.asyncio
    async def test_acquire_tokens(self):
        """Test acquiring tokens."""
        config = RateLimitConfig(max_requests=10, window_seconds=1.0)
        limiter = RateLimiter(config)

        # Should succeed immediately
        await limiter.acquire()
        await limiter.acquire()
        await limiter.acquire()

    @pytest.mark.asyncio
    async def test_acquire_waits_when_limited(self):
        """Test that acquire waits when rate limited."""
        config = RateLimitConfig(
            max_requests=2,
            window_seconds=1.0,
            burst_size=2,
        )
        limiter = RateLimiter(config)

        # Consume all tokens
        await limiter.acquire()
        await limiter.acquire()

        # Next acquire should wait
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start

        # Should have waited ~0.5 seconds (1 token / 2 per second)
        assert 0.3 <= elapsed <= 0.7

    def test_try_acquire_without_waiting(self):
        """Test try_acquire doesn't wait."""
        config = RateLimitConfig(max_requests=2, window_seconds=1.0)
        limiter = RateLimiter(config)

        # Should succeed
        assert limiter.try_acquire() is True
        assert limiter.try_acquire() is True

        # Should fail (no more tokens)
        assert limiter.try_acquire() is False

    def test_update_from_retry_after_header(self):
        """Test updating from Retry-After header."""
        config = RateLimitConfig(max_requests=10, window_seconds=1.0)
        limiter = RateLimiter(config)

        # Simulate API returning Retry-After header
        headers = {"Retry-After": "2"}
        limiter.update_from_headers(headers)

        # Should be rate limited now
        assert limiter.is_rate_limited is True

        # Wait time should be ~2 seconds
        wait_time = limiter.get_wait_time()
        assert 1.9 <= wait_time <= 2.1


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker."""

    def test_initial_state_is_closed(self):
        """Test circuit starts in CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5.0)
        breaker = CircuitBreaker(config)

        assert breaker.current_state == CircuitState.CLOSED
        assert breaker.is_closed is True

    def test_opens_after_threshold_failures(self):
        """Test circuit opens after failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5.0)
        breaker = CircuitBreaker(config)

        # Record failures
        breaker.record_failure(status_code=500)
        assert breaker.is_closed is True  # Still closed

        breaker.record_failure(status_code=502)
        assert breaker.is_closed is True  # Still closed

        breaker.record_failure(status_code=503)
        assert breaker.is_open is True  # Now OPEN!

    def test_success_resets_failure_count(self):
        """Test successes reset failure count in CLOSED state."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5.0)
        breaker = CircuitBreaker(config)

        # Some failures
        breaker.record_failure(status_code=500)
        breaker.record_failure(status_code=500)

        # Success resets count
        breaker.record_success()

        # More failures (should need 3 more to open)
        breaker.record_failure(status_code=500)
        breaker.record_failure(status_code=500)
        assert breaker.is_closed is True  # Still closed

        breaker.record_failure(status_code=500)
        assert breaker.is_open is True  # Now open

    @pytest.mark.asyncio
    async def test_call_method_succeeds(self):
        """Test calling function through circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=5.0)
        breaker = CircuitBreaker(config)

        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.is_closed is True

    @pytest.mark.asyncio
    async def test_call_method_handles_failures(self):
        """Test circuit breaker handles failures."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=5.0)
        breaker = CircuitBreaker(config)

        class APIException(Exception):
            status_code = 500

        async def failing_func():
            raise APIException("API error")

        # First failure
        with pytest.raises(APIException):
            await breaker.call(failing_func)

        assert breaker.is_closed is True  # Still closed

        # Second failure - should open circuit
        with pytest.raises(APIException):
            await breaker.call(failing_func)

        assert breaker.is_open is True  # Now open

        # Third call should fail immediately with CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(failing_func)

    def test_manual_reset(self):
        """Test manually resetting circuit breaker."""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=5.0)
        breaker = CircuitBreaker(config)

        # Open the circuit
        breaker.record_failure(status_code=500)
        breaker.record_failure(status_code=500)
        assert breaker.is_open is True

        # Manual reset
        breaker.reset()
        assert breaker.is_closed is True
        assert breaker.state.failure_count == 0


# ============================================================================
# Retry Handler Tests
# ============================================================================

class TestRetryHandler:
    """Test retry handler."""

    def test_exponential_backoff_delay(self):
        """Test exponential backoff calculation."""
        config = RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.EXPONENTIAL,
            initial_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False,  # Disable jitter for predictable testing
        )
        handler = RetryHandler(config)

        # Attempt 0: 1.0 seconds
        assert handler._calculate_delay(0) == 1.0

        # Attempt 1: 1.0 * 2^1 = 2.0 seconds
        assert handler._calculate_delay(1) == 2.0

        # Attempt 2: 1.0 * 2^2 = 4.0 seconds
        assert handler._calculate_delay(2) == 4.0

    def test_linear_backoff_delay(self):
        """Test linear backoff calculation."""
        config = RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.LINEAR,
            initial_delay=1.0,
            backoff_multiplier=2.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        # Attempt 0: 1.0 * (0+1) * 2.0 = 2.0
        assert handler._calculate_delay(0) == 2.0

        # Attempt 1: 1.0 * (1+1) * 2.0 = 4.0
        assert handler._calculate_delay(1) == 4.0

    def test_fixed_backoff_delay(self):
        """Test fixed backoff calculation."""
        config = RetryConfig(
            max_retries=3,
            strategy=RetryStrategy.FIXED,
            initial_delay=1.0,
            jitter=False,
        )
        handler = RetryHandler(config)

        # All attempts should have same delay
        assert handler._calculate_delay(0) == 1.0
        assert handler._calculate_delay(1) == 1.0
        assert handler._calculate_delay(2) == 1.0

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test successful call doesn't retry."""
        config = RetryConfig(max_retries=3, initial_delay=0.1)
        handler = RetryHandler(config)

        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await handler.call(success_func)

        assert result == "success"
        assert call_count == 1  # Called only once

    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Test retries on retryable failures."""
        config = RetryConfig(
            max_retries=2,
            initial_delay=0.1,
            retry_status_codes=[500],
        )
        handler = RetryHandler(config)

        call_count = 0

        class RetryableError(Exception):
            status_code = 500

        async def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Temporary error")
            return "success"

        result = await handler.call(failing_func)

        assert result == "success"
        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        """Test raises RetryExhaustedError after max retries."""
        config = RetryConfig(max_retries=2, initial_delay=0.1)
        handler = RetryHandler(config)

        async def always_fails():
            raise Exception("Always fails")

        with pytest.raises(RetryExhaustedError) as exc_info:
            await handler.call(always_fails)

        assert exc_info.value.attempts == 2


# ============================================================================
# Authentication Manager Tests
# ============================================================================

class TestAuthenticationManager:
    """Test authentication manager."""

    @pytest.mark.asyncio
    async def test_api_key_auth_header(self):
        """Test API key in header."""
        auth = create_api_key_auth("sk-test-123", header_name="X-API-Key")

        headers, params = await auth.apply_auth({}, {})

        assert headers["X-API-Key"] == "sk-test-123"
        assert len(params) == 0

    @pytest.mark.asyncio
    async def test_api_key_auth_with_prefix(self):
        """Test API key with prefix."""
        auth = create_api_key_auth(
            "test-123",
            header_name="Authorization",
            prefix="ApiKey",
        )

        headers, params = await auth.apply_auth({}, {})

        assert headers["Authorization"] == "ApiKey test-123"

    @pytest.mark.asyncio
    async def test_bearer_auth(self):
        """Test Bearer token authentication."""
        auth = create_bearer_auth("my-token-123")

        headers, params = await auth.apply_auth({}, {})

        assert headers["Authorization"] == "Bearer my-token-123"

    @pytest.mark.asyncio
    async def test_basic_auth(self):
        """Test Basic authentication."""
        auth = create_basic_auth("username", "password")

        headers, params = await auth.apply_auth({}, {})

        # Should have Authorization header with base64 encoded credentials
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Basic ")

        # Decode and verify
        import base64
        encoded = headers["Authorization"].replace("Basic ", "")
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "username:password"

    def test_oauth2_requires_credentials(self):
        """Test OAuth2 config validation."""
        # Missing client_secret
        config = AuthConfig(
            type=AuthType.OAUTH2,
            client_id="client-123",
            token_url="https://auth.example.com/token",
        )

        with pytest.raises(Exception):  # Should raise ConfigurationError
            AuthenticationManager(config)


# ============================================================================
# BaseAPIClient Integration Tests
# ============================================================================

class TestAPIClient(BaseAPIClient):
    """Test implementation of BaseAPIClient."""

    async def _build_base_url(self) -> str:
        return self.config.base_url


class TestBaseAPIClient:
    """Test BaseAPIClient."""

    def test_client_initialization(self):
        """Test client initialization."""
        config = APIClientConfig(
            name="test_client",
            base_url="https://api.example.com",
        )

        client = TestAPIClient(config)

        assert client.config.name == "test_client"
        assert client.metrics.total_requests == 0

    def test_client_with_auth(self):
        """Test client with authentication."""
        config = APIClientConfig(
            name="test_client",
            base_url="https://api.example.com",
            auth=AuthConfig(type=AuthType.BEARER, token="test-token"),
        )

        client = TestAPIClient(config)

        assert client.auth_manager is not None
        assert client.auth_manager.config.type == AuthType.BEARER

    def test_client_with_rate_limiter(self):
        """Test client with rate limiter."""
        config = APIClientConfig(
            name="test_client",
            base_url="https://api.example.com",
            rate_limit=RateLimitConfig(max_requests=10, window_seconds=1.0),
        )

        client = TestAPIClient(config)

        assert client.rate_limiter is not None

    def test_client_with_circuit_breaker(self):
        """Test client with circuit breaker."""
        config = APIClientConfig(
            name="test_client",
            base_url="https://api.example.com",
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout=10.0,
            ),
        )

        client = TestAPIClient(config)

        assert client.circuit_breaker is not None
        assert client.circuit_breaker.is_closed is True

    def test_client_with_retry_handler(self):
        """Test client with retry handler."""
        config = APIClientConfig(
            name="test_client",
            base_url="https://api.example.com",
            retry=RetryConfig(max_retries=3),
        )

        client = TestAPIClient(config)

        assert client.retry_handler is not None

    @pytest.mark.asyncio
    async def test_health_check_with_open_circuit(self):
        """Test health check fails when circuit breaker is open."""
        config = APIClientConfig(
            name="test_client",
            base_url="https://api.example.com",
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=1,
                recovery_timeout=10.0,
            ),
        )

        client = TestAPIClient(config)

        # Health should be good initially
        assert await client.health_check() is True

        # Open circuit breaker
        if client.circuit_breaker:
            client.circuit_breaker.record_failure(status_code=500)

        # Health should fail now
        assert await client.health_check() is False


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
