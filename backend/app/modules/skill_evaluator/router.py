from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, get_current_principal, require_auth
from app.core.database import get_db

from .schemas import EvaluationResultListResponse, EvaluationResultResponse
from .service import get_skill_evaluator_service


router = APIRouter(prefix="/api/evaluation-results", tags=["skill-evaluator"], dependencies=[Depends(require_auth)])


@router.get("/skill-runs/{skill_run_id}", response_model=EvaluationResultListResponse)
async def list_evaluations_for_run(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_skill_evaluator_service()
    items = await service.list_for_run(db, skill_run_id, principal.tenant_id)
    normalized = [EvaluationResultResponse.model_validate(item) for item in items]
    return EvaluationResultListResponse(items=normalized, total=len(normalized))


@router.get("/{evaluation_id}", response_model=EvaluationResultResponse)
async def get_evaluation_result(
    evaluation_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    service = get_skill_evaluator_service()
    item = await service.get_evaluation(db, evaluation_id, principal.tenant_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Evaluation result not found")
    return EvaluationResultResponse.model_validate(item)
