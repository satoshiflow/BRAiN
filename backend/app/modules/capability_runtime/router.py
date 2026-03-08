from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.capabilities.schemas import CapabilityExecutionRequest, CapabilityExecutionResponse
from app.core.capabilities.service import get_capability_execution_service
from app.core.database import get_db


router = APIRouter(prefix="/api/capabilities", tags=["capability-runtime"], dependencies=[Depends(require_auth)])


@router.post("/execute", response_model=CapabilityExecutionResponse)
async def execute_capability(
    payload: CapabilityExecutionRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SERVICE, SystemRole.SYSTEM_ADMIN)),
):
    service = get_capability_execution_service()
    enriched = payload.model_copy(update={"tenant_id": principal.tenant_id, "actor_id": principal.principal_id})
    try:
        return await service.execute(db, enriched)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/bindings/{provider_binding_id}/health")
async def capability_binding_health(
    provider_binding_id: str,
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_capability_execution_service()
    try:
        return await service.health_check(provider_binding_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/bindings")
async def list_capability_bindings(
    capability_key: str = Query(..., min_length=1),
    capability_version: int = Query(..., ge=1),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_capability_execution_service()
    items = service.list_bindings(capability_key, capability_version)
    return {"items": [item.model_dump(mode="json") for item in items], "total": len(items)}
