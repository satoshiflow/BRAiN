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

from .schemas import (
    EvolutionProposalCreateResponse,
    EvolutionProposalResponse,
    EvolutionProposalTransitionRequest,
    EvolutionReviewQueueItem,
    EvolutionReviewQueueResponse,
)
from .service import get_evolution_control_service


router = APIRouter(
    prefix="/api/evolution",
    tags=["evolution-control"],
    dependencies=[Depends(require_auth)],
)


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required"
        )
    return principal.tenant_id


async def _ensure_evolution_control_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "evolution_control")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"evolution_control is {item.lifecycle_status}; writes are blocked",
        )


@router.get("/proposals/{proposal_id}", response_model=EvolutionProposalResponse)
async def get_evolution_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    proposal = await get_evolution_control_service().get_by_id(
        db, proposal_id, tenant_id
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="Evolution proposal not found")
    return EvolutionProposalResponse.model_validate(proposal)


@router.post(
    "/proposals/patterns/{pattern_id}",
    response_model=EvolutionProposalCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_evolution_proposal(
    pattern_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(
        require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)
    ),
):
    _require_tenant(principal)
    await _ensure_evolution_control_writable(db)
    try:
        proposal = await get_evolution_control_service().create_from_pattern(
            db, pattern_id, principal
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Tenant context required":
            raise HTTPException(status_code=403, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return EvolutionProposalCreateResponse(
        pattern_id=pattern_id,
        proposal=EvolutionProposalResponse.model_validate(proposal),
    )


@router.post(
    "/proposals/{proposal_id}/transition", response_model=EvolutionProposalResponse
)
async def transition_evolution_proposal(
    proposal_id: UUID,
    payload: EvolutionProposalTransitionRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(
        require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)
    ),
):
    _require_tenant(principal)
    await _ensure_evolution_control_writable(db)
    try:
        proposal = await get_evolution_control_service().transition_status(
            db, proposal_id, principal, payload.status
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Tenant context required":
            raise HTTPException(status_code=403, detail=message) from exc
        if message in {"Evolution proposal not found"}:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc
    return EvolutionProposalResponse.model_validate(proposal)


@router.get("/review-queue", response_model=EvolutionReviewQueueResponse)
async def list_evolution_review_queue(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    items = await get_evolution_control_service().list_review_queue(
        db, tenant_id, min(max(limit, 1), 200)
    )
    return EvolutionReviewQueueResponse(
        items=[
            EvolutionReviewQueueItem(
                proposal=EvolutionProposalResponse.model_validate(proposal),
                ranking_score=ranking_score,
            )
            for proposal, ranking_score in items
        ]
    )
