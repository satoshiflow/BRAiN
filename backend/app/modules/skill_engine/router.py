from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import SkillRunCreate, SkillRunExecutionReport, SkillRunListResponse, SkillRunResponse, SkillRunState
from .service import get_skill_engine_service


router = APIRouter(prefix="/api/skill-runs", tags=["skill-engine"], dependencies=[Depends(require_auth)])


@router.get("", response_model=SkillRunListResponse)
async def list_skill_runs(
    skill_key: str | None = Query(default=None),
    state: SkillRunState | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_skill_engine_service()
    items = await service.list_runs(db, principal.tenant_id, skill_key=skill_key, state=state.value if state else None)
    return SkillRunListResponse(items=[SkillRunResponse.model_validate(item) for item in items], total=len(items))


@router.post("", response_model=SkillRunResponse, status_code=status.HTTP_201_CREATED)
async def create_skill_run(
    payload: SkillRunCreate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SERVICE, SystemRole.SYSTEM_ADMIN)),
):
    service = get_skill_engine_service()
    try:
        item = await service.create_run(db, payload, principal)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return SkillRunResponse.model_validate(item)


@router.get("/{run_id}", response_model=SkillRunResponse)
async def get_skill_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_skill_engine_service()
    item = await service.get_run(db, run_id, principal.tenant_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill run {run_id} not found")
    return SkillRunResponse.model_validate(item)


@router.post("/{run_id}/execute", response_model=SkillRunExecutionReport)
async def execute_skill_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SERVICE, SystemRole.SYSTEM_ADMIN)),
):
    service = get_skill_engine_service()
    try:
        return await service.execute_run(db, run_id, principal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{run_id}/cancel", response_model=SkillRunResponse)
async def cancel_skill_run(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SERVICE, SystemRole.SYSTEM_ADMIN)),
):
    service = get_skill_engine_service()
    item = await service.cancel_run(db, run_id, principal)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Skill run {run_id} not found")
    return SkillRunResponse.model_validate(item)
