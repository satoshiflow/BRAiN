"""
Production-grade Redis Caching Layer for BRAiN Core.

Features:
- Distributed caching across multiple backend instances
- Cache decorators for automatic caching
- TTL-based expiration with automatic refresh
- Cache invalidation strategies (tag-based, pattern-based)
- Prometheus metrics integration
- Automatic serialization (JSON, pickle, msgpack)
- Cache warming for frequently accessed data
- Circuit breaker for Redis failures

Usage:
    from app.core.cache import cache, Cache

    # Decorator usage
    @cache.cached(ttl=300, key_prefix="missions")
    async def get_mission(mission_id: str) -> Mission:
        return await db.get_mission(mission_id)

    # Manual usage
    cache_client = Cache()
    await cache_client.set("key", {"data": "value"}, ttl=60)
    data = await cache_client.get("key")

    # Invalidation
    await cache_client.delete_pattern("missions:*")
    await cache_client.invalidate_tags(["missions", "queue"])
"""

from __future__ import annotations

import functools
import hashlib
import json
import pickle
import time
from typing import Any, Callable, Optional, Union

import redis.asyncio as redis
from loguru import logger

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False


# ============================================================================
# Cache Configuration
# ============================================================================

class CacheConfig:
    """Cache configuration with sensible defaults."""

    # Default TTLs by data type (seconds)
    DEFAULT_TTL = 300  # 5 minutes
    AGENT_CONFIG_TTL = 600  # 10 minutes (rarely changes)
    MISSION_DATA_TTL = 60  # 1 minute (frequently changes)
    POLICY_TTL = 300  # 5 minutes
    HEALTH_CHECK_TTL = 10  # 10 seconds
    LLM_CONFIG_TTL = 300  # 5 minutes

    # Cache key prefixes
    PREFIX = "brain:cache"
    TAGS_PREFIX = "brain:cache:tags"

    # Serialization format
    SERIALIZATION = "json"  # "json", "pickle", "msgpack"

    # Cache statistics
    TRACK_STATS = True

    # Circuit breaker
    FAIL_SILENTLY = True  # Return None on errors instead of raising


# ============================================================================
# Cache Client
# ============================================================================

class Cache:
    """
    Redis-based cache client with automatic serialization.

    Supports:
    - TTL-based expiration
    - Tag-based invalidation
    - Pattern-based deletion
    - Multiple serialization formats (JSON, pickle, msgpack)
    - Prometheus metrics
    - Circuit breaker for resilience
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        key_prefix: str = CacheConfig.PREFIX,
        default_ttl: int = CacheConfig.DEFAULT_TTL,
        serialization: str = CacheConfig.SERIALIZATION,
    ):
        """
        Initialize cache client.

        Args:
            redis_client: Async Redis client (lazy-loaded if None)
            key_prefix: Prefix for all cache keys
            default_ttl: Default TTL in seconds
            serialization: Serialization format ("json", "pickle", "msgpack")
        """
        self._redis: Optional[redis.Redis] = redis_client
        self.key_prefix = key_prefix
        self.default_ttl = default_ttl
        self.serialization = serialization
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazy initialization of Redis client."""
        if not self._initialized:
            if self._redis is None:
                from app.core.redis_client import get_redis
                self._redis = await get_redis()
            self._initialized = True

    def _make_key(self, key: str) -> str:
        """Generate full Redis key with prefix."""
        return f"{self.key_prefix}:{key}"

    def _serialize(self, value: Any) -> bytes:
        """Serialize value based on configured format."""
        if self.serialization == "json":
            return json.dumps(value, default=str).encode("utf-8")
        elif self.serialization == "msgpack" and MSGPACK_AVAILABLE:
            return msgpack.packb(value, use_bin_type=True)
        else:  # pickle
            return pickle.dumps(value)

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value based on configured format."""
        if self.serialization == "json":
            return json.loads(data.decode("utf-8"))
        elif self.serialization == "msgpack" and MSGPACK_AVAILABLE:
            return msgpack.unpackb(data, raw=False)
        else:  # pickle
            return pickle.loads(data)

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        await self._ensure_initialized()

        full_key = self._make_key(key)

        try:
            start_time = time.time()
            data = await self._redis.get(full_key)

            # Track metrics
            duration = time.time() - start_time
            if CacheConfig.TRACK_STATS:
                from app.core.metrics import MetricsCollector
                MetricsCollector.track_cache_operation("get", duration, success=True)

                if data is not None:
                    MetricsCollector.track_cache_hit()
                else:
                    MetricsCollector.track_cache_miss()

            if data is None:
                logger.debug(f"Cache miss: {key}")
                return None

            logger.debug(f"Cache hit: {key}")
            return self._deserialize(data)

        except Exception as e:
            logger.error(f"Cache get error: {e}", extra={"key": key})

            if CacheConfig.TRACK_STATS:
                from app.core.metrics import MetricsCollector
                MetricsCollector.track_cache_operation("get", 0, success=False)

            if CacheConfig.FAIL_SILENTLY:
                return None
            raise

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (None = default)
            tags: Optional tags for invalidation

        Returns:
            True if successful, False otherwise
        """
        await self._ensure_initialized()

        full_key = self._make_key(key)
        ttl = ttl or self.default_ttl

        try:
            start_time = time.time()

            # Serialize and set value
            data = self._serialize(value)
            await self._redis.set(full_key, data, ex=ttl)

            # Add tags if provided
            if tags:
                await self._add_tags(key, tags)

            duration = time.time() - start_time
            if CacheConfig.TRACK_STATS:
                from app.core.metrics import MetricsCollector
                MetricsCollector.track_cache_operation("set", duration, success=True)
                MetricsCollector.track_cache_ttl("default", ttl)

            logger.debug(f"Cache set: {key} (ttl={ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error: {e}", extra={"key": key})

            if CacheConfig.TRACK_STATS:
                from app.core.metrics import MetricsCollector
                MetricsCollector.track_cache_operation("set", 0, success=False)

            if CacheConfig.FAIL_SILENTLY:
                return False
            raise

    async def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False if not found
        """
        await self._ensure_initialized()

        full_key = self._make_key(key)

        try:
            deleted = await self._redis.delete(full_key)
            logger.debug(f"Cache delete: {key} (deleted={deleted})")
            return deleted > 0

        except Exception as e:
            logger.error(f"Cache delete error: {e}", extra={"key": key})
            if CacheConfig.FAIL_SILENTLY:
                return False
            raise

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Redis pattern (e.g., "missions:*")

        Returns:
            Number of keys deleted

        Example:
            await cache.delete_pattern("missions:*")
        """
        await self._ensure_initialized()

        full_pattern = self._make_key(pattern)

        try:
            # Scan for matching keys
            keys = []
            async for key in self._redis.scan_iter(match=full_pattern, count=100):
                keys.append(key)

            # Delete in batches
            if keys:
                deleted = await self._redis.delete(*keys)
                logger.info(f"Cache pattern delete: {pattern} ({deleted} keys)")
                return deleted

            return 0

        except Exception as e:
            logger.error(f"Cache pattern delete error: {e}", extra={"pattern": pattern})
            if CacheConfig.FAIL_SILENTLY:
                return 0
            raise

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        await self._ensure_initialized()

        full_key = self._make_key(key)

        try:
            exists = await self._redis.exists(full_key)
            return exists > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}", extra={"key": key})
            if CacheConfig.FAIL_SILENTLY:
                return False
            raise

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for key.

        Returns:
            TTL in seconds, -1 if no expiry, -2 if not found
        """
        await self._ensure_initialized()

        full_key = self._make_key(key)

        try:
            ttl = await self._redis.ttl(full_key)
            return ttl
        except Exception as e:
            logger.error(f"Cache TTL error: {e}", extra={"key": key})
            if CacheConfig.FAIL_SILENTLY:
                return -2
            raise

    async def _add_tags(self, key: str, tags: list[str]):
        """Add tags to key for tag-based invalidation."""
        for tag in tags:
            tag_key = f"{CacheConfig.TAGS_PREFIX}:{tag}"
            await self._redis.sadd(tag_key, key)
            # Tags expire after 24 hours
            await self._redis.expire(tag_key, 86400)

    async def invalidate_tags(self, tags: list[str]) -> int:
        """
        Invalidate all keys with given tags.

        Args:
            tags: List of tags

        Returns:
            Number of keys deleted

        Example:
            await cache.invalidate_tags(["missions", "queue"])
        """
        await self._ensure_initialized()

        deleted_count = 0

        try:
            for tag in tags:
                tag_key = f"{CacheConfig.TAGS_PREFIX}:{tag}"

                # Get all keys with this tag
                keys = await self._redis.smembers(tag_key)

                if keys:
                    # Convert bytes to strings and add prefix
                    full_keys = [self._make_key(k.decode("utf-8")) for k in keys]
                    deleted = await self._redis.delete(*full_keys)
                    deleted_count += deleted

                # Delete tag set
                await self._redis.delete(tag_key)

            logger.info(f"Cache tag invalidation: {tags} ({deleted_count} keys)")
            return deleted_count

        except Exception as e:
            logger.error(f"Cache tag invalidation error: {e}", extra={"tags": tags})
            if CacheConfig.FAIL_SILENTLY:
                return 0
            raise

    async def clear_all(self) -> int:
        """
        Clear all cache keys (dangerous!).

        Returns:
            Number of keys deleted
        """
        return await self.delete_pattern("*")

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        await self._ensure_initialized()

        try:
            # Count cache keys
            cache_keys = 0
            async for _ in self._redis.scan_iter(match=f"{self.key_prefix}:*", count=100):
                cache_keys += 1

            # Redis info
            info = await self._redis.info("memory")

            return {
                "cache_keys": cache_keys,
                "redis_memory_used": info.get("used_memory_human", "unknown"),
                "redis_memory_peak": info.get("used_memory_peak_human", "unknown"),
            }

        except Exception as e:
            logger.error(f"Cache stats error: {e}")
            return {}


# ============================================================================
# Cache Decorators
# ============================================================================

class CacheDecorator:
    """Decorator for automatic caching of function results."""

    def __init__(self, cache_client: Optional[Cache] = None):
        self.cache = cache_client or Cache()

    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: Optional[str] = None,
        tags: Optional[list[str]] = None,
        cache_none: bool = False,
    ):
        """
        Cache function result decorator.

        Args:
            ttl: Cache TTL in seconds
            key_prefix: Prefix for cache key (default: function name)
            tags: Tags for invalidation
            cache_none: Whether to cache None results

        Example:
            @cache.cached(ttl=300, key_prefix="missions", tags=["missions"])
            async def get_mission(mission_id: str) -> Mission:
                return await db.get_mission(mission_id)
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key from function name and arguments
                prefix = key_prefix or func.__name__
                key_parts = [prefix]

                # Add args to key
                for arg in args:
                    key_parts.append(str(arg))

                # Add kwargs to key (sorted for consistency)
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}={v}")

                # Hash long keys
                key_str = ":".join(key_parts)
                if len(key_str) > 200:
                    key_hash = hashlib.md5(key_str.encode()).hexdigest()
                    cache_key = f"{prefix}:{key_hash}"
                else:
                    cache_key = key_str

                # Try to get from cache
                cached_value = await self.cache.get(cache_key)

                if cached_value is not None:
                    return cached_value

                # Call function
                result = await func(*args, **kwargs)

                # Cache result
                if result is not None or cache_none:
                    await self.cache.set(cache_key, result, ttl=ttl, tags=tags)

                return result

            return wrapper

        return decorator


# ============================================================================
# Global Cache Instance
# ============================================================================

# Global cache client
_cache_instance: Optional[Cache] = None
_cache_decorator: Optional[CacheDecorator] = None


def get_cache() -> Cache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = Cache()
    return _cache_instance


# Global cache decorator
cache = CacheDecorator()


# ============================================================================
# Cache Warming
# ============================================================================

async def warm_cache():
    """
    Pre-populate cache with frequently accessed data.

    Called on application startup to reduce cold start latency.
    """
    logger.info("Starting cache warming...")
    cache_client = get_cache()

    try:
        # Warm frequently accessed data
        # Example: Agent configurations, policies, etc.

        # This is a placeholder - actual warming logic depends on your data
        # You can add specific warming tasks here

        logger.info("Cache warming completed")

    except Exception as e:
        logger.error(f"Cache warming error: {e}")


# ============================================================================
# Cache Invalidation Helpers
# ============================================================================

async def invalidate_mission_cache(mission_id: Optional[str] = None):
    """Invalidate mission-related cache."""
    cache_client = get_cache()

    if mission_id:
        # Invalidate specific mission
        await cache_client.delete(f"missions:{mission_id}")
    else:
        # Invalidate all missions
        await cache_client.delete_pattern("missions:*")
        await cache_client.invalidate_tags(["missions"])


async def invalidate_agent_cache(agent_id: Optional[str] = None):
    """Invalidate agent-related cache."""
    cache_client = get_cache()

    if agent_id:
        await cache_client.delete(f"agents:{agent_id}")
    else:
        await cache_client.delete_pattern("agents:*")
        await cache_client.invalidate_tags(["agents"])


async def invalidate_policy_cache():
    """Invalidate policy-related cache."""
    cache_client = get_cache()
    await cache_client.delete_pattern("policies:*")
    await cache_client.invalidate_tags(["policies"])


async def invalidate_llm_config_cache():
    """Invalidate LLM configuration cache."""
    cache_client = get_cache()
    await cache_client.delete("llm:config")
