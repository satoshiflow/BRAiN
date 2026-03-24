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
    CapabilityGapResponse,
    DiscoveryAnalyzeResponse,
    DiscoveryListResponse,
    EvidenceThresholdsResponse,
    ProposalEvidenceResponse,
    QueueReviewResponse,
    SkillGapResponse,
    SkillProposalResponse,
)
from .service import get_discovery_layer_service


router = APIRouter(
    prefix="/api/discovery",
    tags=["discovery-layer"],
    dependencies=[Depends(require_auth)],
)


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required"
        )
    return principal.tenant_id


async def _ensure_discovery_layer_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "discovery_layer")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"discovery_layer is {item.lifecycle_status}; writes are blocked",
        )


async def _ensure_evolution_control_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "evolution_control")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"evolution_control is {item.lifecycle_status}; review handoff is blocked",
        )


@router.post(
    "/skill-runs/{skill_run_id}/analyze",
    response_model=DiscoveryAnalyzeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def analyze_skill_run(
    skill_run_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(
        require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)
    ),
):
    _require_tenant(principal)
    await _ensure_discovery_layer_writable(db)
    try:
        (
            skill_gap,
            capability_gap,
            proposal,
            evidence,
        ) = await get_discovery_layer_service().analyze_skill_run(
            db,
            skill_run_id,
            principal,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Tenant context required":
            raise HTTPException(status_code=403, detail=message) from exc
        if message == "Discovery evidence thresholds not met":
            raise HTTPException(status_code=422, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return DiscoveryAnalyzeResponse(
        skill_run_id=skill_run_id,
        skill_gap=SkillGapResponse.model_validate(skill_gap),
        capability_gap=CapabilityGapResponse.model_validate(capability_gap),
        proposal=SkillProposalResponse.model_validate(proposal),
        evidence=ProposalEvidenceResponse(
            evidence_sources=list(evidence.get("evidence_sources", [])),
            observer_signal_count=int(evidence.get("observer_signal_count", 0) or 0),
            knowledge_item_count=int(evidence.get("knowledge_item_count", 0) or 0),
            thresholds=EvidenceThresholdsResponse(
                min_pattern_confidence=float(
                    dict(evidence.get("thresholds", {})).get(
                        "min_pattern_confidence", 0.55
                    )
                ),
                min_recurrence_support=float(
                    dict(evidence.get("thresholds", {})).get(
                        "min_recurrence_support", 0.45
                    )
                ),
                min_observer_signals=int(
                    dict(evidence.get("thresholds", {})).get("min_observer_signals", 1)
                ),
                min_knowledge_items=int(
                    dict(evidence.get("thresholds", {})).get("min_knowledge_items", 1)
                ),
            ),
            evidence_score=float(evidence.get("evidence_score", 0.0) or 0.0),
        ),
    )


@router.get("/proposals", response_model=DiscoveryListResponse)
async def list_skill_proposals(
    status_filter: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    items = await get_discovery_layer_service().list_proposals(
        db,
        tenant_id,
        status_filter=status_filter,
        limit=min(max(limit, 1), 200),
    )
    return DiscoveryListResponse(
        proposals=[SkillProposalResponse.model_validate(item) for item in items]
    )


@router.get("/proposals/{proposal_id}", response_model=SkillProposalResponse)
async def get_skill_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    tenant_id = _require_tenant(principal)
    proposal = await get_discovery_layer_service().get_proposal_by_id(
        db, proposal_id, tenant_id
    )
    if proposal is None:
        raise HTTPException(status_code=404, detail="Skill proposal not found")
    return SkillProposalResponse.model_validate(proposal)


@router.post(
    "/proposals/{proposal_id}/queue-review", response_model=QueueReviewResponse
)
async def queue_proposal_for_review(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(
        require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)
    ),
):
    _require_tenant(principal)
    await _ensure_discovery_layer_writable(db)
    await _ensure_evolution_control_writable(db)
    try:
        (
            proposal,
            evolution_proposal_id,
        ) = await get_discovery_layer_service().queue_for_review(
            db, proposal_id, principal
        )
    except ValueError as exc:
        message = str(exc)
        if message == "Tenant context required":
            raise HTTPException(status_code=403, detail=message) from exc
        if message == "Evolution proposal is not reviewable":
            raise HTTPException(status_code=409, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    return QueueReviewResponse(
        proposal=SkillProposalResponse.model_validate(proposal),
        evolution_proposal_id=UUID(evolution_proposal_id),
    )
