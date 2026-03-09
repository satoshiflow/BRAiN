from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db
from app.modules.module_lifecycle.service import get_module_lifecycle_service

from .schemas import InsightCandidateResponse, InsightDeriveResponse
from .service import get_insight_layer_service


router = APIRouter(prefix="/api/insights", tags=["insight-layer"], dependencies=[Depends(require_auth)])


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    return principal.tenant_id


async def _ensure_insight_layer_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "insight_layer")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"insight_layer is {item.lifecycle_status}; writes are blocked",
        )


@router.get("/{insight_id}", response_model=InsightCandidateResponse)
async def get_insight(
    insight_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    item = await get_insight_layer_service().get_by_id(db, insight_id, tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Insight candidate not found")
    return InsightCandidateResponse.model_validate(item)


@router.get("/skill-runs/{skill_run_id}", response_model=InsightCandidateResponse)
async def get_insight_for_skill_run(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    item = await get_insight_layer_service().get_by_skill_run_id(db, skill_run_id, tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Insight candidate not found")
    return InsightCandidateResponse.model_validate(item)


@router.post("/skill-runs/{skill_run_id}/derive", response_model=InsightDeriveResponse, status_code=status.HTTP_201_CREATED)
async def derive_insight(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    _require_tenant(principal)
    await _ensure_insight_layer_writable(db)
    try:
        item = await get_insight_layer_service().derive_from_skill_run(db, skill_run_id, principal)
    except ValueError as exc:
        message = str(exc)
        if message == "Tenant context required":
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return InsightDeriveResponse(skill_run_id=skill_run_id, insight=InsightCandidateResponse.model_validate(item))
