"""
Example: Rate-Limited API Client

This example demonstrates handling APIs with strict rate limits,
including burst support and API header-based rate limiting.
"""

import asyncio
import time
from typing import Dict, Any

from app.modules.integrations import (
    BaseAPIClient,
    APIClientConfig,
    AuthConfig,
    AuthType,
    RateLimitConfig,
    CircuitBreakerConfig,
    RetryConfig,
)


class StrictlyRateLimitedClient(BaseAPIClient):
    """
    Example client for an API with strict rate limits.

    Demonstrates:
    - Token bucket rate limiting
    - Burst support
    - Respecting Retry-After headers
    - Circuit breaker on repeated failures
    """

    async def _build_base_url(self) -> str:
        """Return API base URL."""
        return self.config.base_url

    async def fetch_data(self, endpoint: str) -> Dict[str, Any]:
        """
        Fetch data from endpoint.

        Args:
            endpoint: API endpoint path

        Returns:
            Response data
        """
        response = await self.get(endpoint)
        return response.body


async def example_burst_handling():
    """Demonstrate burst handling with token bucket."""

    print("=" * 60)
    print("Example: Burst Handling with Token Bucket")
    print("=" * 60)

    # Configure client with burst support
    config = APIClientConfig(
        name="burst_example",
        base_url="https://httpbin.org",  # Public testing API
        # Allow bursts of up to 5 requests, refilling at 1/second
        rate_limit=RateLimitConfig(
            max_requests=1,  # 1 request per window
            window_seconds=1.0,  # 1 second window
            burst_size=5,  # Allow bursts up to 5 requests
        ),
        log_requests=True,
        log_responses=True,
    )

    client = StrictlyRateLimitedClient(config)

    try:
        print("\nSending burst of 5 requests...")
        start = time.time()

        # Send 5 requests in rapid succession (should work due to burst)
        for i in range(5):
            response = await client.get("/delay/0.1")
            print(f"  Request {i+1}: {response.status_code} "
                  f"(elapsed: {time.time() - start:.2f}s)")

        print(f"\nBurst completed in {time.time() - start:.2f}s")

        # Now bucket is empty, next request should wait
        print("\nSending 6th request (should wait for token refill)...")
        start = time.time()
        response = await client.get("/delay/0.1")
        print(f"  Request 6: {response.status_code} "
              f"(waited: {time.time() - start:.2f}s)")

    finally:
        await client.close()


async def example_strict_rate_limit():
    """Demonstrate strict rate limiting without bursts."""

    print("\n" + "=" * 60)
    print("Example: Strict Rate Limiting (No Burst)")
    print("=" * 60)

    # Configure client with strict rate limiting
    config = APIClientConfig(
        name="strict_example",
        base_url="https://httpbin.org",
        # Strict: 2 requests per second, no burst
        rate_limit=RateLimitConfig(
            max_requests=2,
            window_seconds=1.0,
            burst_size=2,  # Same as max_requests = no burst allowance
        ),
        log_requests=True,
    )

    client = StrictlyRateLimitedClient(config)

    try:
        print("\nSending 4 requests (rate limit: 2/second)...")
        start = time.time()

        for i in range(4):
            req_start = time.time()
            await client.get("/delay/0.1")
            print(f"  Request {i+1} completed "
                  f"(total elapsed: {time.time() - start:.2f}s, "
                  f"request took: {time.time() - req_start:.2f}s)")

        print(f"\nTotal time: {time.time() - start:.2f}s")
        print("Expected: ~2 seconds (4 requests / 2 per second)")

    finally:
        await client.close()


async def example_circuit_breaker_with_rate_limit():
    """Demonstrate circuit breaker combined with rate limiting."""

    print("\n" + "=" * 60)
    print("Example: Circuit Breaker + Rate Limiting")
    print("=" * 60)

    # Configure client with both rate limiting and circuit breaker
    config = APIClientConfig(
        name="circuit_breaker_example",
        base_url="https://httpbin.org",
        # Rate limiting
        rate_limit=RateLimitConfig(
            max_requests=10,
            window_seconds=1.0,
        ),
        # Circuit breaker
        circuit_breaker=CircuitBreakerConfig(
            failure_threshold=3,  # Open after 3 failures
            recovery_timeout=5.0,  # Try recovery after 5 seconds
            success_threshold=2,  # Need 2 successes to close
        ),
        # Retry
        retry=RetryConfig(
            max_retries=2,
            initial_delay=0.5,
        ),
        timeout=2.0,  # Short timeout to trigger failures
    )

    client = StrictlyRateLimitedClient(config)

    try:
        # Make some successful requests
        print("\nMaking successful requests...")
        for i in range(3):
            response = await client.get("/delay/0.1")
            print(f"  Request {i+1}: Success ({response.status_code})")

        # Now trigger failures by requesting very slow endpoint
        print("\nTriggering failures (timeout)...")
        for i in range(3):
            try:
                await client.get("/delay/5")  # Will timeout (> 2s)
                print(f"  Request {i+1}: Success (unexpected)")
            except Exception as exc:
                print(f"  Request {i+1}: Failed ({type(exc).__name__})")

                # Check circuit breaker state
                if client.circuit_breaker:
                    state = client.circuit_breaker.current_state
                    print(f"    Circuit breaker state: {state}")

        # Circuit should be OPEN now
        if client.circuit_breaker and client.circuit_breaker.is_open:
            print("\n✓ Circuit breaker is OPEN (protecting against failures)")

            # Try another request (should fail immediately)
            try:
                print("\nAttempting request with open circuit...")
                await client.get("/delay/0.1")
            except Exception as exc:
                print(f"  Request blocked: {type(exc).__name__}")
                print(f"  Message: {exc}")

        # Get metrics
        print("\nClient Metrics:")
        metrics = client.get_metrics()
        print(f"  Total requests: {metrics.total_requests}")
        print(f"  Successful: {metrics.successful_requests}")
        print(f"  Failed: {metrics.failed_requests}")
        print(f"  Circuit breaker opens: {metrics.circuit_breaker_opens}")

    finally:
        await client.close()


async def example_adaptive_rate_limiting():
    """Demonstrate adaptive rate limiting based on API headers."""

    print("\n" + "=" * 60)
    print("Example: Adaptive Rate Limiting (API Headers)")
    print("=" * 60)

    # Many APIs return rate limit info in headers:
    # - X-RateLimit-Remaining: Requests remaining
    # - X-RateLimit-Reset: When limit resets (timestamp)
    # - Retry-After: Seconds to wait

    # Our rate limiter automatically respects these headers!

    config = APIClientConfig(
        name="adaptive_example",
        base_url="https://api.github.com",  # GitHub returns rate limit headers
        auth=AuthConfig(type=AuthType.NONE),  # Unauthenticated (low limits)
        rate_limit=RateLimitConfig(
            max_requests=60,
            window_seconds=3600.0,  # GitHub's unauthenticated limit
            respect_retry_after=True,  # KEY: Respect server headers
        ),
        log_responses=True,
        log_response_body=False,
    )

    client = StrictlyRateLimitedClient(config)

    try:
        print("\nFetching GitHub repositories...")
        print("(GitHub returns X-RateLimit-* headers)")

        # Make a request
        response = await client.get("/repositories")

        print("\nRate limit headers from GitHub:")
        for header, value in response.headers.items():
            if "ratelimit" in header.lower():
                print(f"  {header}: {value}")

        # The rate limiter has updated itself based on these headers!
        if client.rate_limiter:
            print(f"\nRate limiter state:")
            print(f"  Available tokens: {client.rate_limiter.available_tokens:.0f}")
            print(f"  Is rate limited: {client.rate_limiter.is_rate_limited}")

    finally:
        await client.close()


async def main():
    """Run all examples."""

    print("\n" + "=" * 60)
    print("Rate-Limited API Client Examples")
    print("=" * 60)

    # Run examples
    await example_burst_handling()
    await example_strict_rate_limit()
    await example_circuit_breaker_with_rate_limit()
    await example_adaptive_rate_limiting()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
