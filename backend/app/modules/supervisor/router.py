from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends

from app.core.auth_deps import require_auth, get_current_principal, Principal
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import AgentStatus, SupervisorHealth, SupervisorStatus
from .service import get_health, get_status, list_agents

router = APIRouter(
    prefix="/api/supervisor",
    tags=["supervisor"],
    dependencies=[Depends(require_auth)]
)


@router.get("/health", response_model=SupervisorHealth)
async def supervisor_health(
    principal: Principal = Depends(get_current_principal),
) -> SupervisorHealth:
    return await get_health()


@router.get("/status", response_model=SupervisorStatus)
async def supervisor_status(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> SupervisorStatus:
    return await get_status(db)


@router.get("/agents", response_model=List[AgentStatus])
async def supervisor_agents(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> List[AgentStatus]:
    return await list_agents(db)
