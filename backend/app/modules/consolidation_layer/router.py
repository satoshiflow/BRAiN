from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db
from app.modules.module_lifecycle.service import get_module_lifecycle_service

from .schemas import PatternCandidateResponse, PatternDeriveResponse
from .service import get_consolidation_layer_service


router = APIRouter(prefix="/api/consolidation", tags=["consolidation-layer"], dependencies=[Depends(require_auth)])


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    return principal.tenant_id


async def _ensure_consolidation_layer_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "consolidation_layer")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"consolidation_layer is {item.lifecycle_status}; writes are blocked",
        )


@router.get("/{pattern_id}", response_model=PatternCandidateResponse)
async def get_pattern(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    item = await get_consolidation_layer_service().get_by_id(db, pattern_id, tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pattern candidate not found")
    return PatternCandidateResponse.model_validate(item)


@router.get("/skill-runs/{skill_run_id}", response_model=PatternCandidateResponse)
async def get_pattern_for_skill_run(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    item = await get_consolidation_layer_service().get_by_skill_run_id(db, skill_run_id, tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Pattern candidate not found")
    return PatternCandidateResponse.model_validate(item)


@router.post("/skill-runs/{skill_run_id}/derive", response_model=PatternDeriveResponse, status_code=status.HTTP_201_CREATED)
async def derive_pattern(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    _require_tenant(principal)
    await _ensure_consolidation_layer_writable(db)
    try:
        item = await get_consolidation_layer_service().derive_from_skill_run(db, skill_run_id, principal)
    except ValueError as exc:
        message = str(exc)
        if message == "Tenant context required":
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return PatternDeriveResponse(skill_run_id=skill_run_id, pattern=PatternCandidateResponse.model_validate(item))
