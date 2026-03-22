from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import ProviderBindingCreate, ProviderBindingResponse, ProviderBindingStatus
from .service import get_provider_binding_service


class ProviderBindingListResponse(BaseModel):
    items: list[ProviderBindingResponse] = Field(default_factory=list)
    total: int


class ProviderBindingHealthUpdate(BaseModel):
    health_status: str = Field(..., min_length=1, max_length=32)
    latency_p95_ms: float | None = None
    error_rate_5m: float | None = None
    circuit_state: str | None = Field(default=None, max_length=32)
    ttl_seconds: int = Field(default=300, ge=1, le=3600)


class ProviderBindingHealthResponse(BaseModel):
    provider_binding_id: str
    health: dict


router = APIRouter(prefix="/api/provider-bindings", tags=["provider-bindings"], dependencies=[Depends(require_auth)])


@router.post("", response_model=ProviderBindingResponse, status_code=status.HTTP_201_CREATED)
async def create_provider_binding(
    payload: ProviderBindingCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_binding_service()
    try:
        item = await service.create_binding(db, payload, principal)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return ProviderBindingResponse.model_validate(item)


@router.get("", response_model=ProviderBindingListResponse)
async def list_provider_bindings(
    capability_key: str = Query(..., min_length=1),
    capability_version: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_provider_binding_service()
    items = await service.list_bindings(db, capability_key, capability_version, principal.tenant_id)
    normalized = [ProviderBindingResponse.model_validate(item) for item in items]
    return ProviderBindingListResponse(items=normalized, total=len(normalized))


@router.get("/{binding_id}", response_model=ProviderBindingResponse)
async def get_provider_binding(
    binding_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_provider_binding_service()
    item = await service.get_binding(db, binding_id, principal.tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Provider binding not found")
    return ProviderBindingResponse.model_validate(item)


@router.post("/{binding_id}/enable", response_model=ProviderBindingResponse)
async def enable_provider_binding(
    binding_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_binding_service()
    try:
        item = await service.transition_binding(db, binding_id, ProviderBindingStatus.ENABLED, principal)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Provider binding not found")
    return ProviderBindingResponse.model_validate(item)


@router.post("/{binding_id}/disable", response_model=ProviderBindingResponse)
async def disable_provider_binding(
    binding_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_binding_service()
    try:
        item = await service.transition_binding(db, binding_id, ProviderBindingStatus.DISABLED, principal)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Provider binding not found")
    return ProviderBindingResponse.model_validate(item)


@router.post("/{binding_id}/quarantine", response_model=ProviderBindingResponse)
async def quarantine_provider_binding(
    binding_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_provider_binding_service()
    try:
        item = await service.transition_binding(db, binding_id, ProviderBindingStatus.QUARANTINED, principal)
    except (PermissionError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Provider binding not found")
    return ProviderBindingResponse.model_validate(item)


@router.put("/{binding_id}/health", response_model=ProviderBindingHealthResponse)
async def update_provider_binding_health(
    binding_id: UUID,
    payload: ProviderBindingHealthUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN, SystemRole.SERVICE)),
):
    service = get_provider_binding_service()
    item = await service.get_binding(db, binding_id, principal.tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Provider binding not found")
    health = await service.update_health_projection(
        binding_id=str(binding_id),
        health_status=payload.health_status,
        latency_p95_ms=payload.latency_p95_ms,
        error_rate_5m=payload.error_rate_5m,
        circuit_state=payload.circuit_state,
        ttl_seconds=payload.ttl_seconds,
        db=db,
        principal=principal,
    )
    return ProviderBindingHealthResponse(provider_binding_id=str(binding_id), health=health)


@router.get("/{binding_id}/health", response_model=ProviderBindingHealthResponse)
async def get_provider_binding_health(
    binding_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_provider_binding_service()
    item = await service.get_binding(db, binding_id, principal.tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Provider binding not found")
    health = await service.get_health_projection(str(binding_id)) or {}
    return ProviderBindingHealthResponse(provider_binding_id=str(binding_id), health=health)
