from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import (
    SkillOptimizerRecommendationListResponse,
    SkillOptimizerRecommendationResponse,
    SkillOptimizerRecommendationStatusUpdateRequest,
)
from .service import get_skill_optimizer_service


router = APIRouter(prefix="/api/optimizer", tags=["skill-optimizer"], dependencies=[Depends(require_auth)])


@router.post("/recommendations", response_model=SkillOptimizerRecommendationListResponse)
async def generate_recommendations(
    skill_key: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_skill_optimizer_service()
    items = await service.generate_for_skill(db, principal.tenant_id, skill_key)
    return SkillOptimizerRecommendationListResponse(items=[SkillOptimizerRecommendationResponse.model_validate(item) for item in items], total=len(items))


@router.get("/recommendations", response_model=SkillOptimizerRecommendationListResponse)
async def list_recommendations(
    skill_key: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_skill_optimizer_service()
    items = await service.list_for_skill(db, principal.tenant_id, skill_key)
    return SkillOptimizerRecommendationListResponse(items=[SkillOptimizerRecommendationResponse.model_validate(item) for item in items], total=len(items))


@router.patch("/recommendations/{recommendation_id}/status", response_model=SkillOptimizerRecommendationResponse)
async def update_recommendation_status(
    recommendation_id: UUID,
    payload: SkillOptimizerRecommendationStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    service = get_skill_optimizer_service()
    try:
        item = await service.update_status(
            db,
            recommendation_id=recommendation_id,
            tenant_id=principal.tenant_id,
            status=payload.status,
            actor_id=principal.principal_id,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    if item is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return SkillOptimizerRecommendationResponse.model_validate(item)
