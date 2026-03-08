from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import ModuleLifecycleListResponse, ModuleLifecycleResponse, ModuleLifecycleTransitionRequest
from .service import get_module_lifecycle_service


router = APIRouter(prefix="/api/module-lifecycle", tags=["module-lifecycle"], dependencies=[Depends(require_auth)])


@router.get("", response_model=ModuleLifecycleListResponse)
async def list_module_lifecycle(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    items = await get_module_lifecycle_service().list_modules(db)
    return ModuleLifecycleListResponse(items=[ModuleLifecycleResponse.model_validate(item) for item in items], total=len(items))


@router.get("/{module_id}", response_model=ModuleLifecycleResponse)
async def get_module_lifecycle(
    module_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    item = await get_module_lifecycle_service().get_module(db, module_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Module lifecycle record not found")
    return ModuleLifecycleResponse.model_validate(item)


@router.post("/{module_id}/deprecate", response_model=ModuleLifecycleResponse)
async def deprecate_module(
    module_id: str,
    payload: ModuleLifecycleTransitionRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    item = await get_module_lifecycle_service().set_status(db, module_id, "deprecated", payload.replacement_target, payload.sunset_phase, payload.notes)
    if item is None:
        raise HTTPException(status_code=404, detail="Module lifecycle record not found")
    return ModuleLifecycleResponse.model_validate(item)


@router.post("/{module_id}/retire", response_model=ModuleLifecycleResponse)
async def retire_module(
    module_id: str,
    payload: ModuleLifecycleTransitionRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    item = await get_module_lifecycle_service().set_status(db, module_id, "retired", payload.replacement_target, payload.sunset_phase, payload.notes)
    if item is None:
        raise HTTPException(status_code=404, detail="Module lifecycle record not found")
    return ModuleLifecycleResponse.model_validate(item)
