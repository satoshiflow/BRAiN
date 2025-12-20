"""
Production-grade Redis-based Rate Limiter for BRAiN Core.

Features:
- Distributed rate limiting across multiple backend instances
- Sliding window log algorithm for accurate counting
- Per-IP and per-user rate limiting
- Multiple limit tiers (global, authenticated, premium)
- Automatic key expiration
- Prometheus metrics integration

Algorithms:
- Sliding Window Log: Most accurate, stores individual request timestamps
- Fixed Window Counter: Memory-efficient, less accurate at boundaries

Usage:
    rate_limiter = RateLimiter(redis_client)

    # Check if request is allowed
    allowed, retry_after = await rate_limiter.is_allowed(
        key="user_123",
        max_requests=100,
        window_seconds=60
    )

    if not allowed:
        raise HTTPException(status_code=429, headers={"Retry-After": str(retry_after)})
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import redis.asyncio as redis
from loguru import logger


# ============================================================================
# Redis-based Rate Limiter
# ============================================================================

class RateLimiter:
    """
    Distributed rate limiter using Redis sorted sets (sliding window log).

    How it works:
    1. Each request adds a timestamp to a Redis sorted set
    2. Old timestamps (outside the window) are removed
    3. If count < limit, request is allowed
    4. Keys auto-expire after window + buffer time

    Pros:
    - Accurate: No edge cases at window boundaries
    - Distributed: Works across multiple backend instances
    - Fair: True sliding window, not fixed buckets

    Cons:
    - Memory: Stores individual timestamps (mitigated by expiration)
    - Redis I/O: 3 Redis commands per request (optimized with pipeline)
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "brain:ratelimit"
    ):
        """
        Initialize rate limiter.

        Args:
            redis_client: Async Redis client
            key_prefix: Redis key prefix for namespacing
        """
        self.redis = redis_client
        self.key_prefix = key_prefix

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        cost: int = 1
    ) -> Tuple[bool, int]:
        """
        Check if a request is allowed under the rate limit.

        Args:
            key: Unique identifier (IP address, user ID, etc.)
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
            cost: Request cost (default 1, can be higher for expensive operations)

        Returns:
            Tuple of (allowed: bool, retry_after: int)
            - allowed: True if request is within limits
            - retry_after: Seconds to wait before retry (0 if allowed)

        Example:
            allowed, retry_after = await rate_limiter.is_allowed("user_123", 100, 60)
            if not allowed:
                raise HTTPException(429, headers={"Retry-After": str(retry_after)})
        """
        redis_key = f"{self.key_prefix}:{key}"
        now = time.time()
        window_start = now - window_seconds

        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()

        try:
            # 1. Remove old timestamps (outside the window)
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # 2. Count current requests in window
            pipe.zcard(redis_key)

            # 3. Add current request timestamp(s)
            # For cost > 1, add multiple timestamps
            for i in range(cost):
                pipe.zadd(redis_key, {f"{now}:{i}": now})

            # 4. Set key expiration (window + 1 minute buffer)
            pipe.expire(redis_key, window_seconds + 60)

            # Execute pipeline
            results = await pipe.execute()

            # Get current count (before adding new request)
            current_count = results[1]  # ZCARD result

            # Check if request exceeds limit
            if current_count + cost > max_requests:
                # Remove the timestamps we just added (rollback)
                for i in range(cost):
                    await self.redis.zrem(redis_key, f"{now}:{i}")

                # Calculate retry_after: time until oldest request expires
                oldest_timestamps = await self.redis.zrange(
                    redis_key, 0, 0, withscores=True
                )

                if oldest_timestamps:
                    oldest_timestamp = oldest_timestamps[0][1]
                    retry_after = int(oldest_timestamp + window_seconds - now) + 1
                else:
                    retry_after = window_seconds

                logger.warning(
                    f"Rate limit exceeded",
                    extra={
                        "key": key,
                        "current_count": current_count,
                        "max_requests": max_requests,
                        "window_seconds": window_seconds,
                        "retry_after": retry_after,
                    }
                )

                return False, retry_after

            # Request allowed
            return True, 0

        except Exception as e:
            logger.error(
                f"Rate limiter error: {e}",
                extra={"key": key, "error": str(e)}
            )
            # Fail open: Allow request if Redis is unavailable
            # This prevents cascading failures
            return True, 0

    async def get_usage(
        self,
        key: str,
        window_seconds: int
    ) -> dict:
        """
        Get current rate limit usage for a key.

        Args:
            key: Unique identifier
            window_seconds: Time window in seconds

        Returns:
            dict with usage statistics

        Example:
            usage = await rate_limiter.get_usage("user_123", 60)
            # {"count": 45, "window_seconds": 60, "remaining": 55}
        """
        redis_key = f"{self.key_prefix}:{key}"
        now = time.time()
        window_start = now - window_seconds

        try:
            # Remove old timestamps
            await self.redis.zremrangebyscore(redis_key, 0, window_start)

            # Count requests in window
            count = await self.redis.zcard(redis_key)

            return {
                "count": count,
                "window_seconds": window_seconds,
            }

        except Exception as e:
            logger.error(f"Failed to get rate limit usage: {e}")
            return {
                "count": 0,
                "window_seconds": window_seconds,
            }

    async def reset(self, key: str) -> bool:
        """
        Reset rate limit for a key (admin operation).

        Args:
            key: Unique identifier

        Returns:
            True if key was deleted, False otherwise
        """
        redis_key = f"{self.key_prefix}:{key}"

        try:
            deleted = await self.redis.delete(redis_key)
            logger.info(f"Rate limit reset for key: {key}")
            return deleted > 0

        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False


# ============================================================================
# Fixed Window Counter (Alternative Algorithm)
# ============================================================================

class FixedWindowRateLimiter:
    """
    Fixed window counter rate limiter (more memory-efficient).

    How it works:
    1. Each window (e.g., 13:00:00-13:01:00) has a counter
    2. Increment counter on each request
    3. If counter < limit, allow request

    Pros:
    - Memory-efficient: Single counter per window
    - Simple: Easy to understand and debug

    Cons:
    - Less accurate: Edge case at window boundaries
      (e.g., 100 requests at 12:59:59, 100 more at 13:00:01 = 200 in 2 seconds)

    Use case: High-traffic endpoints where slight inaccuracy is acceptable
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "brain:ratelimit:fixed"
    ):
        self.redis = redis_client
        self.key_prefix = key_prefix

    async def is_allowed(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> Tuple[bool, int]:
        """Check if request is allowed (fixed window)."""
        now = int(time.time())
        window_id = now // window_seconds
        redis_key = f"{self.key_prefix}:{key}:{window_id}"

        try:
            # Increment counter
            count = await self.redis.incr(redis_key)

            # Set expiration on first request in window
            if count == 1:
                await self.redis.expire(redis_key, window_seconds * 2)

            # Check limit
            if count > max_requests:
                retry_after = window_seconds - (now % window_seconds)
                return False, retry_after

            return True, 0

        except Exception as e:
            logger.error(f"Fixed window rate limiter error: {e}")
            return True, 0  # Fail open


# ============================================================================
# Rate Limit Configuration
# ============================================================================

class RateLimitTier:
    """Rate limit tiers for different user types."""

    # Global limits (per IP)
    GLOBAL = {
        "max_requests": 100,
        "window_seconds": 60,
        "burst": 20,  # Allow bursts up to 20 over limit
    }

    # Authenticated user limits
    AUTHENTICATED = {
        "max_requests": 500,
        "window_seconds": 60,
        "burst": 50,
    }

    # Premium/admin user limits
    PREMIUM = {
        "max_requests": 5000,
        "window_seconds": 60,
        "burst": 500,
    }

    # Endpoint-specific limits
    EXPENSIVE_ENDPOINTS = {
        "max_requests": 10,
        "window_seconds": 60,
    }

    @classmethod
    def get_limit(cls, tier: str) -> dict:
        """Get rate limit configuration for tier."""
        return getattr(cls, tier.upper(), cls.GLOBAL)


# ============================================================================
# Utility Functions
# ============================================================================

def get_client_identifier(request) -> str:
    """
    Get unique client identifier for rate limiting.

    Priority:
    1. Authenticated user ID
    2. API key
    3. Client IP address

    Args:
        request: FastAPI Request object

    Returns:
        Unique client identifier string
    """
    # Check for authenticated user (from JWT)
    if hasattr(request.state, "principal") and request.state.principal:
        return f"user:{request.state.principal.principal_id}"

    # Check for API key in headers
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"apikey:{api_key[:16]}"  # Use first 16 chars

    # Fall back to IP address
    client_ip = request.client.host if request.client else "unknown"

    # Check for forwarded IP (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Use first IP in chain
        client_ip = forwarded_for.split(",")[0].strip()

    return f"ip:{client_ip}"


def get_rate_limit_tier(request) -> str:
    """
    Determine rate limit tier for request.

    Args:
        request: FastAPI Request object

    Returns:
        Tier name ("global", "authenticated", "premium")
    """
    if hasattr(request.state, "principal") and request.state.principal:
        principal = request.state.principal

        # Check for premium/admin roles
        if "admin" in principal.roles or "premium" in principal.roles:
            return "premium"

        # Authenticated user
        return "authenticated"

    # Unauthenticated request
    return "global"
