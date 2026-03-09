from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db
from app.modules.module_lifecycle.service import get_module_lifecycle_service

from .schemas import (
    DeliberationSummaryCreate,
    DeliberationSummaryResponse,
    MissionTensionCreate,
    MissionTensionListResponse,
    MissionTensionResponse,
)
from .service import get_deliberation_layer_service


router = APIRouter(prefix="/api/deliberation", tags=["deliberation-layer"], dependencies=[Depends(require_auth)])


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    return principal.tenant_id


async def _ensure_deliberation_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "deliberation_layer")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"deliberation_layer is {item.lifecycle_status}; writes are blocked",
        )


@router.post("/missions/{mission_id}/summaries", response_model=DeliberationSummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_deliberation_summary(
    mission_id: str,
    payload: DeliberationSummaryCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    _require_tenant(principal)
    await _ensure_deliberation_writable(db)
    try:
        item = await get_deliberation_layer_service().create_summary(db, mission_id, payload, principal)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return DeliberationSummaryResponse.model_validate(item)


@router.get("/missions/{mission_id}/summaries/latest", response_model=DeliberationSummaryResponse)
async def get_latest_deliberation_summary(
    mission_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    item = await get_deliberation_layer_service().get_latest_summary(db, mission_id, tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Deliberation summary not found")
    return DeliberationSummaryResponse.model_validate(item)


@router.post("/missions/{mission_id}/tensions", response_model=MissionTensionResponse, status_code=status.HTTP_201_CREATED)
async def create_mission_tension(
    mission_id: str,
    payload: MissionTensionCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    _require_tenant(principal)
    await _ensure_deliberation_writable(db)
    try:
        item = await get_deliberation_layer_service().create_tension(db, mission_id, payload, principal)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return MissionTensionResponse.model_validate(item)


@router.get("/missions/{mission_id}/tensions", response_model=MissionTensionListResponse)
async def list_mission_tensions(
    mission_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    items = await get_deliberation_layer_service().list_tensions(db, mission_id, tenant_id)
    return MissionTensionListResponse(items=[MissionTensionResponse.model_validate(item) for item in items], total=len(items))
