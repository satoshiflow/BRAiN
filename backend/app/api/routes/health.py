"""
Health Check Endpoints for Production Monitoring

Provides Kubernetes-style liveness and readiness probes:
- /health/live: Liveness probe (basic app health)
- /health/ready: Readiness probe (dependency checks)

These endpoints are used by:
- Kubernetes liveness/readiness probes
- Load balancers health checks
- Monitoring systems (Prometheus, etc.)
"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time
import logging

from app.core.redis_client import get_redis
from app.core.db import check_db_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str  # "healthy" | "unhealthy" | "degraded"
    timestamp: float
    checks: dict[str, dict]


class LivenessResponse(BaseModel):
    """Liveness probe response."""
    status: str
    timestamp: float
    uptime_seconds: float


# Track application start time
_start_time = time.time()


@router.get("/live", response_model=LivenessResponse, status_code=status.HTTP_200_OK)
async def liveness_probe() -> LivenessResponse:
    """
    Liveness probe - checks if the application is running.

    This is a simple check that the application process is alive.
    If this fails, the container should be restarted.

    Returns:
        200 OK: Application is running

    Example:
        GET /health/live
        {
            "status": "healthy",
            "timestamp": 1703001234.56,
            "uptime_seconds": 3600.5
        }
    """
    return LivenessResponse(
        status="healthy",
        timestamp=time.time(),
        uptime_seconds=time.time() - _start_time
    )


@router.get("/ready", response_model=HealthStatus)
async def readiness_probe() -> JSONResponse:
    """
    Readiness probe - checks if the application is ready to serve traffic.

    Performs deep health checks on all dependencies:
    - PostgreSQL database connection
    - Redis connection
    - (Qdrant connection - future)

    Returns:
        200 OK: All systems operational, ready to serve traffic
        503 Service Unavailable: One or more dependencies are down

    Example Success:
        GET /health/ready
        {
            "status": "healthy",
            "timestamp": 1703001234.56,
            "checks": {
                "database": {
                    "status": "healthy",
                    "response_time_ms": 5.2
                },
                "redis": {
                    "status": "healthy",
                    "response_time_ms": 2.1
                }
            }
        }

    Example Failure:
        GET /health/ready (503)
        {
            "status": "unhealthy",
            "timestamp": 1703001234.56,
            "checks": {
                "database": {
                    "status": "healthy",
                    "response_time_ms": 5.2
                },
                "redis": {
                    "status": "unhealthy",
                    "error": "Connection refused"
                }
            }
        }
    """
    checks = {}
    overall_healthy = True

    # Check PostgreSQL
    db_start = time.time()
    try:
        db_healthy = await check_db_health()
        db_time = (time.time() - db_start) * 1000  # Convert to ms

        if db_healthy:
            checks["database"] = {
                "status": "healthy",
                "response_time_ms": round(db_time, 2)
            }
        else:
            checks["database"] = {
                "status": "unhealthy",
                "error": "Health check query failed"
            }
            overall_healthy = False

    except Exception as e:
        checks["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
        logger.error(f"Database health check failed: {e}")

    # Check Redis
    redis_start = time.time()
    try:
        redis = await get_redis()
        await redis.ping()
        redis_time = (time.time() - redis_start) * 1000  # Convert to ms

        checks["redis"] = {
            "status": "healthy",
            "response_time_ms": round(redis_time, 2)
        }

    except Exception as e:
        checks["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        overall_healthy = False
        logger.error(f"Redis health check failed: {e}")

    # TODO: Add Qdrant health check when needed
    # qdrant_start = time.time()
    # try:
    #     # Check Qdrant connection
    #     qdrant_client = get_qdrant_client()
    #     await qdrant_client.get_collections()
    #     qdrant_time = (time.time() - qdrant_start) * 1000
    #     checks["qdrant"] = {
    #         "status": "healthy",
    #         "response_time_ms": round(qdrant_time, 2)
    #     }
    # except Exception as e:
    #     checks["qdrant"] = {
    #         "status": "unhealthy",
    #         "error": str(e)
    #     }
    #     overall_healthy = False
    #     logger.error(f"Qdrant health check failed: {e}")

    # Determine overall status
    health_status = HealthStatus(
        status="healthy" if overall_healthy else "unhealthy",
        timestamp=time.time(),
        checks=checks
    )

    # Return appropriate status code
    if overall_healthy:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_status.model_dump()
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status.model_dump()
        )


@router.get("/startup", response_model=HealthStatus)
async def startup_probe() -> JSONResponse:
    """
    Startup probe - checks if the application has started successfully.

    Similar to readiness probe but used during startup phase.
    Kubernetes uses this to know when to start sending traffic.

    Returns:
        200 OK: Application started successfully
        503 Service Unavailable: Still starting or startup failed
    """
    # For now, use the same logic as readiness probe
    # In future, could add startup-specific checks
    return await readiness_probe()


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """
    Simple health check endpoint (legacy).

    Returns basic health information without deep dependency checks.
    Use /health/live or /health/ready for production monitoring.

    Returns:
        200 OK: Basic health info
    """
    return {
        "status": "ok",
        "message": "BRAiN Core is running",
        "timestamp": time.time(),
        "uptime_seconds": time.time() - _start_time
    }
