"""
Health Monitor System - API Router
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import require_auth, get_current_principal, Principal

from .schemas import (
    HealthCheckCreate, HealthCheckResponse, HealthStatusSummary,
    HealthHistoryResponse
)
from .service import get_health_monitor_service


router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/status", response_model=HealthStatusSummary, dependencies=[Depends(require_auth)])
async def get_health_status(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get overall health status of all monitored services."""
    service = get_health_monitor_service()
    return await service.get_status(db)


@router.get("/services/{service_name}", response_model=HealthCheckResponse, dependencies=[Depends(require_auth)])
async def get_service_health(
    service_name: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get detailed health status for a specific service."""
    service = get_health_monitor_service()
    check = await service.get_service(db, service_name)
    
    if not check:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Service {service_name} not found"
        )
    
    return HealthCheckResponse.model_validate(check)


@router.post("/check", response_model=HealthStatusSummary, dependencies=[Depends(require_auth)])
async def run_health_checks(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Manually trigger health checks for all services."""
    service = get_health_monitor_service()
    await service.check_all_services(db)
    return await service.get_status(db)


@router.get("/history/{service_name}", response_model=HealthHistoryResponse, dependencies=[Depends(require_auth)])
async def get_health_history(
    service_name: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get health check history for a specific service."""
    service = get_health_monitor_service()
    return await service.get_history(db, service_name, limit)
