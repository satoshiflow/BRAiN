"""
System Health Router

API endpoints for comprehensive system health monitoring.
"""

from fastapi import APIRouter, Depends
from typing import Optional

from backend.app.modules.system_health.service import SystemHealthService
from backend.app.modules.system_health.schemas import (
    SystemHealth,
    SystemHealthSummary,
)

router = APIRouter(prefix="/api/system/health", tags=["System Health"])

# Singleton instances
_system_health_service: Optional[SystemHealthService] = None
_runtime_auditor: Optional[object] = None


def get_system_health_service() -> SystemHealthService:
    """Dependency injection for SystemHealthService"""
    global _system_health_service
    if _system_health_service is None:
        _system_health_service = SystemHealthService()
    return _system_health_service


def get_runtime_auditor() -> Optional[object]:
    """Dependency injection for RuntimeAuditor"""
    global _runtime_auditor
    if _runtime_auditor is None:
        try:
            from backend.app.modules.runtime_auditor.service import RuntimeAuditor
            from backend.app.modules.immune.core.service import ImmuneService

            # Initialize with Immune System integration
            immune_service = ImmuneService()
            _runtime_auditor = RuntimeAuditor(
                collection_interval=60.0,
                immune_service=immune_service,
            )
        except Exception as e:
            # RuntimeAuditor optional - system works without it
            pass
    return _runtime_auditor


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get(
    "",
    response_model=SystemHealth,
    summary="Get comprehensive system health",
    description="""
    Get comprehensive system health overview including:
    - Overall status (healthy, degraded, critical)
    - Sub-system health (immune, threats, missions, agents)
    - Audit metrics (edge-of-chaos, performance, resources)
    - Identified bottlenecks
    - Optimization recommendations
    """,
)
async def get_system_health(
    service: SystemHealthService = Depends(get_system_health_service),
    runtime_auditor: Optional[object] = Depends(get_runtime_auditor),
) -> SystemHealth:
    """Get comprehensive system health overview"""
    return await service.get_comprehensive_health(runtime_auditor=runtime_auditor)


@router.get(
    "/summary",
    response_model=SystemHealthSummary,
    summary="Get lightweight health summary",
    description="Get lightweight health summary for quick checks and dashboard widgets",
)
async def get_health_summary(
    service: SystemHealthService = Depends(get_system_health_service),
) -> SystemHealthSummary:
    """Get lightweight health summary"""
    return await service.get_health_summary()


@router.get(
    "/status",
    summary="Simple health check",
    description="Simple health check endpoint for load balancers and monitoring tools",
)
async def health_check(
    service: SystemHealthService = Depends(get_system_health_service),
) -> dict:
    """Simple health check"""
    summary = await service.get_health_summary()
    return {
        "status": summary.status.value,
        "timestamp": summary.timestamp.isoformat(),
        "ok": summary.status.value != "critical",
    }
