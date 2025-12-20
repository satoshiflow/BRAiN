"""
Rate limiter implementation using token bucket algorithm.

Provides per-client rate limiting with burst support, automatic token refill,
and respect for API-provided rate limit headers.
"""

from __future__ import annotations

import asyncio
import time
from typing import Optional, Dict
from loguru import logger

from .schemas import RateLimitConfig
from .exceptions import RateLimitExceededError


class TokenBucket:
    """
    Token bucket for rate limiting.

    The token bucket algorithm allows for bursts while maintaining a steady
    rate over time. Tokens are added at a constant rate, and requests consume
    tokens. If no tokens are available, the request is rate-limited.
    """

    def __init__(
        self,
        max_tokens: int,
        refill_rate: float,
        *,
        burst_size: Optional[int] = None,
    ) -> None:
        """
        Initialize token bucket.

        Args:
            max_tokens: Maximum number of tokens in the bucket
            refill_rate: Tokens added per second
            burst_size: Maximum burst size (defaults to max_tokens)
        """
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        self.burst_size = burst_size or max_tokens

        # Start with a full bucket
        self._tokens = float(min(max_tokens, self.burst_size))
        self._last_refill = time.monotonic()

    def _refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.monotonic()
        elapsed = now - self._last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self._tokens = min(self._tokens + tokens_to_add, self.burst_size)
        self._last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if not enough tokens available
        """
        self._refill()

        if self._tokens >= tokens:
            self._tokens -= tokens
            return True

        return False

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until enough tokens are available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait (0 if tokens available now)
        """
        self._refill()

        if self._tokens >= tokens:
            return 0.0

        # Calculate how many tokens we need
        tokens_needed = tokens - self._tokens

        # Calculate how long to wait for those tokens
        return tokens_needed / self.refill_rate

    @property
    def available_tokens(self) -> float:
        """Get current number of available tokens."""
        self._refill()
        return self._tokens


class RateLimiter:
    """
    Rate limiter with token bucket algorithm and API header support.

    Manages rate limits for API clients, respecting both client-side
    configured limits and server-provided rate limit headers.
    """

    def __init__(self, config: RateLimitConfig) -> None:
        """
        Initialize rate limiter.

        Args:
            config: Rate limit configuration
        """
        self.config = config

        # Calculate refill rate (tokens per second)
        self._refill_rate = config.max_requests / config.window_seconds

        # Create token bucket
        self._bucket = TokenBucket(
            max_tokens=config.max_requests,
            refill_rate=self._refill_rate,
            burst_size=config.burst_size,
        )

        # Server-side rate limit tracking (from headers)
        self._server_retry_after: Optional[float] = None  # Timestamp when to retry

        logger.debug(
            "RateLimiter initialized: {req}/{window}s (burst={burst})",
            req=config.max_requests,
            window=config.window_seconds,
            burst=config.burst_size,
        )

    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire

        Raises:
            RateLimitExceededError: If rate limit exceeded and waiting disabled
        """
        # Check server-side rate limit first
        if self._server_retry_after is not None:
            now = time.time()
            if now < self._server_retry_after:
                wait_time = self._server_retry_after - now
                logger.warning(
                    "Server rate limit active, waiting {wait:.1f}s",
                    wait=wait_time,
                )
                await asyncio.sleep(wait_time)
                self._server_retry_after = None

        # Try to consume tokens
        if self._bucket.consume(tokens):
            return

        # Not enough tokens, calculate wait time
        wait_time = self._bucket.get_wait_time(tokens)

        logger.warning(
            "Rate limit reached, waiting {wait:.2f}s for {tokens} token(s)",
            wait=wait_time,
            tokens=tokens,
        )

        await asyncio.sleep(wait_time)

        # Consume tokens after waiting
        consumed = self._bucket.consume(tokens)
        if not consumed:
            # Should not happen, but defensive programming
            raise RateLimitExceededError(
                "Failed to acquire tokens after waiting",
                retry_after=wait_time,
            )

    def try_acquire(self, tokens: int = 1) -> bool:
        """
        Try to acquire tokens without waiting.

        Args:
            tokens: Number of tokens to acquire

        Returns:
            True if tokens acquired, False if not enough tokens
        """
        # Check server-side rate limit
        if self._server_retry_after is not None:
            now = time.time()
            if now < self._server_retry_after:
                return False
            self._server_retry_after = None

        return self._bucket.consume(tokens)

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait for tokens without consuming them.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait (0 if available now)
        """
        # Check server-side rate limit
        if self._server_retry_after is not None:
            now = time.time()
            if now < self._server_retry_after:
                return self._server_retry_after - now
            self._server_retry_after = None

        return self._bucket.get_wait_time(tokens)

    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """
        Update rate limit state from API response headers.

        Supports common rate limit headers:
        - Retry-After: Seconds to wait before retry
        - X-RateLimit-Remaining: Remaining requests
        - X-RateLimit-Reset: Timestamp when limit resets

        Args:
            headers: HTTP response headers
        """
        if not self.config.respect_retry_after:
            return

        # Case-insensitive header lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Check for Retry-After header (most explicit)
        retry_after = headers_lower.get("retry-after")
        if retry_after:
            try:
                # Can be either seconds (int) or HTTP date
                seconds = float(retry_after)
                self._server_retry_after = time.time() + seconds
                logger.info(
                    "Server rate limit: retry after {seconds}s",
                    seconds=seconds,
                )
            except ValueError:
                # HTTP date format - not commonly used
                logger.warning("Retry-After header has date format, not supported yet")

        # Check for X-RateLimit-Remaining
        remaining = headers_lower.get("x-ratelimit-remaining")
        if remaining:
            try:
                remaining_count = int(remaining)
                if remaining_count == 0:
                    # No requests remaining, check when it resets
                    reset = headers_lower.get("x-ratelimit-reset")
                    if reset:
                        try:
                            reset_timestamp = float(reset)
                            self._server_retry_after = reset_timestamp
                            logger.info(
                                "Server rate limit: 0 remaining, reset at {ts}",
                                ts=reset_timestamp,
                            )
                        except ValueError:
                            logger.warning("Invalid X-RateLimit-Reset value")
            except ValueError:
                logger.warning("Invalid X-RateLimit-Remaining value")

    @property
    def available_tokens(self) -> float:
        """Get current number of available tokens."""
        return self._bucket.available_tokens

    @property
    def is_rate_limited(self) -> bool:
        """Check if currently rate limited."""
        if self._server_retry_after is not None:
            return time.time() < self._server_retry_after
        return self._bucket.available_tokens < 1.0

    def reset(self) -> None:
        """Reset rate limiter to initial state."""
        self._bucket = TokenBucket(
            max_tokens=self.config.max_requests,
            refill_rate=self._refill_rate,
            burst_size=self.config.burst_size,
        )
        self._server_retry_after = None
        logger.debug("RateLimiter reset")


class RateLimiterRegistry:
    """
    Registry for managing multiple rate limiters.

    Allows different rate limits for different API endpoints or clients.
    """

    def __init__(self) -> None:
        self._limiters: Dict[str, RateLimiter] = {}

    def get_or_create(self, name: str, config: RateLimitConfig) -> RateLimiter:
        """
        Get existing rate limiter or create a new one.

        Args:
            name: Unique identifier for the rate limiter
            config: Rate limit configuration

        Returns:
            Rate limiter instance
        """
        if name not in self._limiters:
            self._limiters[name] = RateLimiter(config)
            logger.debug("Created new rate limiter: {name}", name=name)

        return self._limiters[name]

    def get(self, name: str) -> Optional[RateLimiter]:
        """
        Get rate limiter by name.

        Args:
            name: Rate limiter identifier

        Returns:
            Rate limiter instance or None if not found
        """
        return self._limiters.get(name)

    def remove(self, name: str) -> bool:
        """
        Remove rate limiter.

        Args:
            name: Rate limiter identifier

        Returns:
            True if removed, False if not found
        """
        if name in self._limiters:
            del self._limiters[name]
            logger.debug("Removed rate limiter: {name}", name=name)
            return True
        return False

    def clear(self) -> None:
        """Remove all rate limiters."""
        self._limiters.clear()
        logger.debug("Cleared all rate limiters")


# Global registry instance
_registry = RateLimiterRegistry()


def get_rate_limiter_registry() -> RateLimiterRegistry:
    """Get global rate limiter registry."""
    return _registry
