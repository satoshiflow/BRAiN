from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import (
    ObserverSignalListResponse,
    ObserverSignalResponse,
    ObserverStateResponse,
    ObserverSummaryResponse,
)
from .service import get_observer_core_service


router = APIRouter(prefix="/api/observer", tags=["observer-core"], dependencies=[Depends(require_auth)])


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    return principal.tenant_id


_OBSERVER_READ_ROLES = (
    SystemRole.VIEWER,
    SystemRole.OPERATOR,
    SystemRole.ADMIN,
    SystemRole.SERVICE,
    SystemRole.SYSTEM_ADMIN,
)


@router.get("/signals", response_model=ObserverSignalListResponse)
async def list_observer_signals(
    source_module: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(*_OBSERVER_READ_ROLES)),
):
    tenant_id = _require_tenant(principal)
    items = await get_observer_core_service().list_signals(
        db=db,
        tenant_id=tenant_id,
        source_module=source_module,
        severity=severity,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    return ObserverSignalListResponse(items=[ObserverSignalResponse.model_validate(i) for i in items], total=len(items))


@router.get("/signals/{signal_id}", response_model=ObserverSignalResponse)
async def get_observer_signal(
    signal_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(*_OBSERVER_READ_ROLES)),
):
    tenant_id = _require_tenant(principal)
    item = await get_observer_core_service().get_signal(db, signal_id, tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Observer signal not found")
    return ObserverSignalResponse.model_validate(item)


@router.get("/state", response_model=ObserverStateResponse)
async def get_observer_state(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(*_OBSERVER_READ_ROLES)),
):
    tenant_id = _require_tenant(principal)
    state = await get_observer_core_service().get_tenant_state(db, tenant_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Observer state not found")
    return ObserverStateResponse.model_validate(state)


@router.get("/state/entities/{entity_type}/{entity_id}", response_model=ObserverStateResponse)
async def get_observer_entity_state(
    entity_type: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(*_OBSERVER_READ_ROLES)),
):
    tenant_id = _require_tenant(principal)
    state = await get_observer_core_service().get_entity_state(db, tenant_id, entity_type, entity_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Observer state not found")
    return ObserverStateResponse.model_validate(state)


@router.get("/summary", response_model=ObserverSummaryResponse)
async def get_observer_summary(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(*_OBSERVER_READ_ROLES)),
):
    tenant_id = _require_tenant(principal)
    state = await get_observer_core_service().get_tenant_state(db, tenant_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Observer state not found")
    return ObserverSummaryResponse(
        tenant_id=state.tenant_id,
        snapshot_version=state.snapshot_version,
        health_summary=state.health_summary,
        risk_summary=state.risk_summary,
        execution_summary=state.execution_summary,
        queue_summary=state.queue_summary,
        updated_at=state.updated_at,
    )
