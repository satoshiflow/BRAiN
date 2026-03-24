from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db
from app.modules.module_lifecycle.service import get_module_lifecycle_service

from .schemas import ExperienceIngestResponse, ExperienceRecordResponse
from .service import get_experience_layer_service


router = APIRouter(prefix="/api/experience", tags=["experience-layer"], dependencies=[Depends(require_auth)])


async def _ensure_experience_layer_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "experience_layer")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"experience_layer is {item.lifecycle_status}; writes are blocked",
        )


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    return principal.tenant_id


@router.get("/{experience_id}", response_model=ExperienceRecordResponse)
async def get_experience_record(
    experience_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
): 
    tenant_id = _require_tenant(principal)
    record = await get_experience_layer_service().get_by_id(db, experience_id, tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Experience record not found")
    return ExperienceRecordResponse.model_validate(record)


@router.get("/skill-runs/{skill_run_id}", response_model=ExperienceRecordResponse)
async def get_experience_for_skill_run(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    record = await get_experience_layer_service().get_by_skill_run_id(db, skill_run_id, tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Experience record not found")
    return ExperienceRecordResponse.model_validate(record)


@router.post("/skill-runs/{skill_run_id}/ingest", response_model=ExperienceIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_skill_run(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    _require_tenant(principal)
    await _ensure_experience_layer_writable(db)
    try:
        record = await get_experience_layer_service().ingest_skill_run(db, skill_run_id, principal)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExperienceIngestResponse(skill_run_id=skill_run_id, experience=ExperienceRecordResponse.model_validate(record))
