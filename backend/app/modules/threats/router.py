from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.auth_deps import require_auth, get_current_principal, Principal
from .models import (
    Threat,
    ThreatCreate,
    ThreatListResponse,
    ThreatSeverity,
    ThreatStatsResponse,
    ThreatStatus,
)
from .service import (
    create_threat,
    get_stats,
    get_threat,
    list_threats,
    update_threat_status,
)

router = APIRouter(
    prefix="/api/threats",
    tags=["threats"],
    dependencies=[Depends(require_auth)]
)


@router.get("/health")
async def threats_health() -> dict:
    return {"status": "ok"}


@router.get("", response_model=ThreatListResponse)
async def list_threats_endpoint(
    status: Optional[ThreatStatus] = Query(default=None),
    severity: Optional[ThreatSeverity] = Query(default=None),
    principal: Principal = Depends(get_current_principal),
) -> ThreatListResponse:
    return await list_threats(status=status, severity=severity)


@router.post("", response_model=Threat, status_code=status.HTTP_201_CREATED)
async def create_threat_endpoint(
    payload: ThreatCreate,
    principal: Principal = Depends(get_current_principal),
) -> Threat:
    return await create_threat(payload)


@router.get("/{threat_id}", response_model=Threat)
async def get_threat_endpoint(
    threat_id: str,
    principal: Principal = Depends(get_current_principal),
) -> Threat:
    threat = await get_threat(threat_id)
    if not threat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Threat not found",
        )
    return threat


@router.post("/{threat_id}/status", response_model=Threat)
async def update_threat_status_endpoint(
    threat_id: str,
    status: ThreatStatus,
    principal: Principal = Depends(get_current_principal),
) -> Threat:
    threat = await update_threat_status(threat_id, status)
    if not threat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Threat not found",
        )
    return threat


@router.get("/stats/overview", response_model=ThreatStatsResponse)
async def get_stats_endpoint(
    principal: Principal = Depends(get_current_principal),
) -> ThreatStatsResponse:
    return await get_stats()