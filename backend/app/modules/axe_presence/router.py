"""FastAPI routes for AXE 2035 presence surface."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, require_auth
from app.core.database import get_db

from .schemas import AXEPresenceResponse, AXERelaysListResponse, AXERuntimeSurfaceResponse
from .service import AXEPresenceService


router = APIRouter(
    prefix="/api/axe",
    tags=["axe-presence"],
    dependencies=[Depends(require_auth)],
)


def get_service(db: AsyncSession = Depends(get_db)) -> AXEPresenceService:
    return AXEPresenceService(db)


@router.get("/presence", response_model=AXEPresenceResponse)
async def get_presence(
    principal: Principal = Depends(require_auth),
    service: AXEPresenceService = Depends(get_service),
) -> AXEPresenceResponse:
    try:
        return await service.get_presence(tenant_id=principal.tenant_id)
    except Exception as exc:  # pragma: no cover
        logger.error("[AXEPresence] /presence failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Presence surface is temporarily unavailable",
        ) from exc


@router.get("/relays", response_model=AXERelaysListResponse)
async def get_relays(
    principal: Principal = Depends(require_auth),
    service: AXEPresenceService = Depends(get_service),
) -> AXERelaysListResponse:
    try:
        return await service.get_relays(tenant_id=principal.tenant_id)
    except Exception as exc:  # pragma: no cover
        logger.error("[AXEPresence] /relays failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Relay surface is temporarily unavailable",
        ) from exc


@router.get("/runtime/surface", response_model=AXERuntimeSurfaceResponse)
async def get_runtime_surface(
    principal: Principal = Depends(require_auth),
    service: AXEPresenceService = Depends(get_service),
) -> AXERuntimeSurfaceResponse:
    try:
        return await service.get_runtime_surface(tenant_id=principal.tenant_id)
    except Exception as exc:  # pragma: no cover
        logger.error("[AXEPresence] /runtime/surface failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Runtime surface is temporarily unavailable",
        ) from exc
