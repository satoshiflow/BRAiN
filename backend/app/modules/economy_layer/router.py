from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import (
    Principal,
    SystemRole,
    get_current_principal,
    require_auth,
    require_role,
)
from app.core.database import get_db
from app.modules.module_lifecycle.service import get_module_lifecycle_service
from app.modules.discovery_layer.schemas import SkillProposalResponse

from .schemas import (
    EconomyAnalyzeResponse,
    EconomyAssessmentResponse,
    EconomyQueueReviewResponse,
)
from .service import get_economy_layer_service


router = APIRouter(
    prefix="/api/economy", tags=["economy-layer"], dependencies=[Depends(require_auth)]
)


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required"
        )
    return principal.tenant_id


async def _ensure_economy_layer_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "economy_layer")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"economy_layer is {item.lifecycle_status}; writes are blocked",
        )


@router.post(
    "/proposals/{proposal_id}/analyze",
    response_model=EconomyAnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_proposal_economics(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(
        require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)
    ),
):
    _require_tenant(principal)
    await _ensure_economy_layer_writable(db)
    try:
        assessment, proposal = await get_economy_layer_service().analyze_proposal(
            db, proposal_id, principal
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Tenant context required":
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return EconomyAnalyzeResponse(
        assessment=EconomyAssessmentResponse.model_validate(assessment),
        proposal=SkillProposalResponse.model_validate(proposal),
    )


@router.get("/assessments/{assessment_id}", response_model=EconomyAssessmentResponse)
async def get_assessment(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    item = await get_economy_layer_service().get_assessment_by_id(
        db, assessment_id, tenant_id
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Economy assessment not found")
    return EconomyAssessmentResponse.model_validate(item)


@router.post(
    "/assessments/{assessment_id}/queue-review",
    response_model=EconomyQueueReviewResponse,
)
async def queue_assessment_review(
    assessment_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(
        require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)
    ),
):
    _require_tenant(principal)
    await _ensure_economy_layer_writable(db)
    try:
        assessment = await get_economy_layer_service().queue_for_review(
            db, assessment_id, principal
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Tenant context required":
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return EconomyQueueReviewResponse(
        assessment=EconomyAssessmentResponse.model_validate(assessment)
    )
