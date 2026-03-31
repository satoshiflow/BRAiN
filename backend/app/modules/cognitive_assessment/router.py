from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, get_current_principal, require_auth, require_role
from app.core.database import get_db

from .schemas import CognitiveAssessmentRequest, CognitiveAssessmentResponse
from .service import get_cognitive_assessment_service


router = APIRouter(prefix="/api/cognitive-assessment", tags=["cognitive-assessment"], dependencies=[Depends(require_auth)])


@router.post("/assess", response_model=CognitiveAssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: CognitiveAssessmentRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)),
):
    try:
        return await get_cognitive_assessment_service().assess(db, payload, principal)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{assessment_id}", response_model=CognitiveAssessmentResponse)
async def get_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    item = await get_cognitive_assessment_service().get_assessment(db, assessment_id, principal)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cognitive assessment not found")
    return item
