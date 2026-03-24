from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Query

from app.core.auth_deps import (
    Principal,
    SystemRole,
    get_current_principal,
    require_auth,
    require_role,
)
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import (
    AgentStatus,
    DomainEscalationDecisionRequest,
    DomainEscalationListResponse,
    DomainEscalationRequest,
    DomainEscalationResponse,
    SupervisorHealth,
    SupervisorStatus,
)
from .service import (
    create_domain_escalation_handoff,
    decide_domain_escalation_handoff,
    get_domain_escalation_handoff,
    get_health,
    get_status,
    list_agents,
    list_domain_escalation_handoffs,
)

router = APIRouter(
    prefix="/api/supervisor",
    tags=["supervisor"],
    dependencies=[Depends(require_auth)]
)


async def _get_db():
    from app.core.database import get_db

    async for session in get_db():
        yield session


@router.get("/health", response_model=SupervisorHealth)
async def supervisor_health(
    principal: Principal = Depends(get_current_principal),
) -> SupervisorHealth:
    return await get_health()


@router.get("/status", response_model=SupervisorStatus)
async def supervisor_status(
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(get_current_principal),
) -> SupervisorStatus:
    return await get_status(db)


@router.get("/agents", response_model=List[AgentStatus])
async def supervisor_agents(
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(get_current_principal),
) -> List[AgentStatus]:
    return await list_agents(db)


@router.post(
    "/escalations/domain",
    response_model=DomainEscalationResponse,
)
async def create_domain_escalation(
    payload: DomainEscalationRequest,
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(
        require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN, SystemRole.SERVICE)
    ),
) -> DomainEscalationResponse:
    scoped_payload = payload.model_copy(update={"tenant_id": principal.tenant_id})
    return await create_domain_escalation_handoff(scoped_payload, db=db)


@router.get(
    "/escalations/domain",
    response_model=DomainEscalationListResponse,
)
async def list_domain_escalations(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(get_current_principal),
) -> DomainEscalationListResponse:
    items = await list_domain_escalation_handoffs(limit=limit, db=db, tenant_id=principal.tenant_id)
    return DomainEscalationListResponse(items=items, total=len(items))


@router.get(
    "/escalations/domain/{escalation_id}",
    response_model=DomainEscalationResponse,
)
async def get_domain_escalation(
    escalation_id: str,
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(get_current_principal),
) -> DomainEscalationResponse:
    item = await get_domain_escalation_handoff(escalation_id, db=db, tenant_id=principal.tenant_id)
    if item is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found")
    return item


@router.post(
    "/escalations/domain/{escalation_id}/decision",
    response_model=DomainEscalationResponse,
)
async def decide_domain_escalation(
    escalation_id: str,
    payload: DomainEscalationDecisionRequest,
    db: AsyncSession = Depends(_get_db),
    principal: Principal = Depends(
        require_role(SystemRole.OPERATOR, SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)
    ),
) -> DomainEscalationResponse:
    scoped_payload = payload.model_copy(update={"reviewer_id": principal.principal_id})
    try:
        item = await decide_domain_escalation_handoff(
            escalation_id,
            scoped_payload,
            db=db,
            tenant_id=principal.tenant_id,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    if item is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escalation not found")
    return item
