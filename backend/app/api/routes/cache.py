"""
Cache Management API Endpoints.

Provides administrative endpoints for:
- Cache statistics
- Manual cache invalidation
- Cache warming
- Health checks
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core.cache import (
    get_cache,
    invalidate_mission_cache,
    invalidate_agent_cache,
    invalidate_policy_cache,
    invalidate_llm_config_cache,
    warm_cache,
)

router = APIRouter(prefix="/api/cache", tags=["cache"])


# ============================================================================
# Response Models
# ============================================================================

class CacheStatsResponse(BaseModel):
    """Cache statistics response."""
    cache_keys: int
    redis_memory_used: str
    redis_memory_peak: str


class CacheInvalidateRequest(BaseModel):
    """Cache invalidation request."""
    pattern: Optional[str] = None
    tags: Optional[list[str]] = None
    mission_id: Optional[str] = None
    agent_id: Optional[str] = None
    invalidate_all: bool = False


class CacheInvalidateResponse(BaseModel):
    """Cache invalidation response."""
    success: bool
    keys_deleted: int
    message: str


class CacheHealthResponse(BaseModel):
    """Cache health check response."""
    status: str
    connected: bool
    stats: Optional[CacheStatsResponse] = None


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats():
    """
    Get cache statistics.

    Returns current cache metrics including:
    - Number of cached keys
    - Redis memory usage
    - Redis memory peak

    Example:
        GET /api/cache/stats
    """
    cache = get_cache()
    stats = await cache.get_stats()

    return CacheStatsResponse(
        cache_keys=stats.get("cache_keys", 0),
        redis_memory_used=stats.get("redis_memory_used", "unknown"),
        redis_memory_peak=stats.get("redis_memory_peak", "unknown"),
    )


@router.get("/health", response_model=CacheHealthResponse)
async def cache_health_check():
    """
    Check cache health.

    Verifies Redis connectivity and returns cache statistics.

    Example:
        GET /api/cache/health
    """
    cache = get_cache()

    try:
        stats = await cache.get_stats()
        return CacheHealthResponse(
            status="healthy",
            connected=True,
            stats=CacheStatsResponse(**stats),
        )
    except Exception as e:
        return CacheHealthResponse(
            status="unhealthy",
            connected=False,
        )


@router.post("/invalidate", response_model=CacheInvalidateResponse)
async def invalidate_cache(request: CacheInvalidateRequest):
    """
    Invalidate cache entries.

    Supports multiple invalidation strategies:
    - By pattern: `{"pattern": "missions:*"}`
    - By tags: `{"tags": ["missions", "queue"]}`
    - By mission ID: `{"mission_id": "mission_123"}`
    - By agent ID: `{"agent_id": "agent_456"}`
    - Invalidate all: `{"invalidate_all": true}`

    Example:
        POST /api/cache/invalidate
        {
            "pattern": "missions:*"
        }
    """
    cache = get_cache()
    keys_deleted = 0

    try:
        # Invalidate all caches (dangerous!)
        if request.invalidate_all:
            keys_deleted = await cache.clear_all()
            return CacheInvalidateResponse(
                success=True,
                keys_deleted=keys_deleted,
                message=f"All cache cleared ({keys_deleted} keys deleted)",
            )

        # Invalidate by pattern
        if request.pattern:
            keys_deleted = await cache.delete_pattern(request.pattern)
            return CacheInvalidateResponse(
                success=True,
                keys_deleted=keys_deleted,
                message=f"Pattern '{request.pattern}' invalidated ({keys_deleted} keys deleted)",
            )

        # Invalidate by tags
        if request.tags:
            keys_deleted = await cache.invalidate_tags(request.tags)
            return CacheInvalidateResponse(
                success=True,
                keys_deleted=keys_deleted,
                message=f"Tags {request.tags} invalidated ({keys_deleted} keys deleted)",
            )

        # Invalidate mission cache
        if request.mission_id:
            await invalidate_mission_cache(request.mission_id)
            keys_deleted = 1
            return CacheInvalidateResponse(
                success=True,
                keys_deleted=keys_deleted,
                message=f"Mission {request.mission_id} cache invalidated",
            )

        # Invalidate agent cache
        if request.agent_id:
            await invalidate_agent_cache(request.agent_id)
            keys_deleted = 1
            return CacheInvalidateResponse(
                success=True,
                keys_deleted=keys_deleted,
                message=f"Agent {request.agent_id} cache invalidated",
            )

        # No invalidation criteria provided
        raise HTTPException(
            status_code=400,
            detail="No invalidation criteria provided (pattern, tags, mission_id, agent_id, or invalidate_all required)",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cache invalidation failed: {str(e)}",
        )


@router.post("/warm")
async def warm_cache_endpoint():
    """
    Warm cache with frequently accessed data.

    Pre-populates cache to reduce cold start latency.
    Typically called after application restart or deployment.

    Example:
        POST /api/cache/warm
    """
    try:
        await warm_cache()
        return {
            "success": True,
            "message": "Cache warming completed",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cache warming failed: {str(e)}",
        )


@router.post("/invalidate/missions")
async def invalidate_missions_cache():
    """
    Invalidate all mission-related cache entries.

    Example:
        POST /api/cache/invalidate/missions
    """
    try:
        await invalidate_mission_cache()
        return {
            "success": True,
            "message": "Mission cache invalidated",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Mission cache invalidation failed: {str(e)}",
        )


@router.post("/invalidate/agents")
async def invalidate_agents_cache():
    """
    Invalidate all agent-related cache entries.

    Example:
        POST /api/cache/invalidate/agents
    """
    try:
        await invalidate_agent_cache()
        return {
            "success": True,
            "message": "Agent cache invalidated",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent cache invalidation failed: {str(e)}",
        )


@router.post("/invalidate/policies")
async def invalidate_policies_cache():
    """
    Invalidate all policy-related cache entries.

    Example:
        POST /api/cache/invalidate/policies
    """
    try:
        await invalidate_policy_cache()
        return {
            "success": True,
            "message": "Policy cache invalidated",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Policy cache invalidation failed: {str(e)}",
        )


@router.post("/invalidate/llm-config")
async def invalidate_llm_config_cache():
    """
    Invalidate LLM configuration cache.

    Example:
        POST /api/cache/invalidate/llm-config
    """
    try:
        await invalidate_llm_config_cache()
        return {
            "success": True,
            "message": "LLM config cache invalidated",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"LLM config cache invalidation failed: {str(e)}",
        )


@router.delete("/keys/{key}")
async def delete_cache_key(key: str):
    """
    Delete specific cache key.

    Args:
        key: Cache key to delete

    Example:
        DELETE /api/cache/keys/missions:mission_123
    """
    cache = get_cache()

    try:
        deleted = await cache.delete(key)
        if deleted:
            return {
                "success": True,
                "message": f"Key '{key}' deleted",
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Key '{key}' not found",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Cache key deletion failed: {str(e)}",
        )


@router.get("/keys/{key}/ttl")
async def get_cache_key_ttl(key: str):
    """
    Get remaining TTL for cache key.

    Args:
        key: Cache key

    Returns:
        TTL in seconds (-1 if no expiry, -2 if not found)

    Example:
        GET /api/cache/keys/missions:mission_123/ttl
    """
    cache = get_cache()

    try:
        ttl = await cache.ttl(key)
        return {
            "key": key,
            "ttl": ttl,
            "exists": ttl >= -1,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TTL check failed: {str(e)}",
        )
