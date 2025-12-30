"""
Legacy Health Endpoint

DEPRECATED: Use /api/system/health for comprehensive health data.
This endpoint is kept for backward compatibility and simple health checks.
"""

from fastapi import APIRouter, Depends
from backend.app.modules.system_health.service import SystemHealthService

router = APIRouter(prefix="/api", tags=["core"])

# Singleton instance
_health_service = None


def get_health_service() -> SystemHealthService:
    """Get SystemHealthService instance"""
    global _health_service
    if _health_service is None:
        _health_service = SystemHealthService()
    return _health_service


@router.get(
    "/health",
    summary="Simple health check (deprecated)",
    description="Simple health check. Use /api/system/health for comprehensive data.",
    deprecated=True,
)
async def health(
    service: SystemHealthService = Depends(get_health_service),
) -> dict:
    """
    Legacy health check endpoint.

    DEPRECATED: Use /api/system/health/status for enhanced health checks.

    Returns:
        Simple status object for backward compatibility
    """
    try:
        summary = await service.get_health_summary()
        return {
            "status": "ok" if summary.status.value != "critical" else "degraded",
            "timestamp": summary.timestamp.isoformat(),
            "message": summary.message,
            # Add hint to new endpoint
            "enhanced_health_endpoint": "/api/system/health",
        }
    except Exception as e:
        # Fallback to simple response
        return {
            "status": "ok",
            "error": str(e),
            "enhanced_health_endpoint": "/api/system/health",
        }
