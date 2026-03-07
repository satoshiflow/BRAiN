"""API router for Genetic Quarantine Manager."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, require_auth, require_role
from app.core.database import get_db
from app.modules.genetic_quarantine.schemas import (
    QuarantineAuditResponse,
    QuarantineRecordsResponse,
    QuarantineRequest,
    QuarantineResponse,
    QuarantineTransitionRequest,
)
from app.modules.genetic_quarantine.service import get_genetic_quarantine_service


router = APIRouter(
    prefix="/api/genetic-quarantine",
    tags=["Genetic Quarantine"],
    dependencies=[Depends(require_auth)],
)


@router.post("/records", response_model=QuarantineResponse)
async def create_quarantine_record(
    request: QuarantineRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> QuarantineResponse:
    service = get_genetic_quarantine_service()
    actor = request.actor or principal.email or principal.principal_id
    record = await service.quarantine(request.model_copy(update={"actor": actor}), db=db)
    return QuarantineResponse(record=record)


@router.post("/records/transition", response_model=QuarantineResponse)
async def transition_quarantine_record(
    request: QuarantineTransitionRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> QuarantineResponse:
    service = get_genetic_quarantine_service()
    actor = request.actor or principal.email or principal.principal_id
    record = await service.transition(request.model_copy(update={"actor": actor}), db=db)
    return QuarantineResponse(record=record)


@router.get("/records", response_model=QuarantineRecordsResponse)
async def list_quarantine_records(db: AsyncSession = Depends(get_db)) -> QuarantineRecordsResponse:
    service = get_genetic_quarantine_service()
    return QuarantineRecordsResponse(items=await service.list_records(db=db))


@router.get("/audit", response_model=QuarantineAuditResponse)
async def list_quarantine_audit(db: AsyncSession = Depends(get_db)) -> QuarantineAuditResponse:
    service = get_genetic_quarantine_service()
    return QuarantineAuditResponse(items=await service.list_audit_entries(db=db))
