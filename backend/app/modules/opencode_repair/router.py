"""API router for OpenCode repair loop."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import Principal, SystemRole, require_auth, require_role
from app.core.database import get_db
from app.modules.opencode_repair.schemas import (
    RepairAuditResponse,
    RepairAutotriggerRequest,
    RepairTicketCreateRequest,
    RepairTicketResponse,
    RepairTicketsResponse,
    RepairTicketUpdateRequest,
)
from app.modules.opencode_repair.service import get_opencode_repair_service


router = APIRouter(
    prefix="/api/opencode-repair",
    tags=["OpenCode Repair"],
    dependencies=[Depends(require_auth)],
)


@router.post("/tickets", response_model=RepairTicketResponse)
async def create_ticket(
    request: RepairTicketCreateRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RepairTicketResponse:
    actor = request.actor or principal.email or principal.principal_id
    service = get_opencode_repair_service()
    ticket = await service.create_ticket(request.model_copy(update={"actor": actor}), db=db)
    return RepairTicketResponse(ticket=ticket)


@router.post("/tickets/auto", response_model=RepairTicketResponse)
async def autotrigger_ticket(
    request: RepairAutotriggerRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RepairTicketResponse:
    actor = request.actor or principal.email or principal.principal_id
    service = get_opencode_repair_service()
    ticket = await service.create_ticket_from_signal(request.model_copy(update={"actor": actor}), db=db)
    return RepairTicketResponse(ticket=ticket)


@router.post("/tickets/update", response_model=RepairTicketResponse)
async def update_ticket(
    request: RepairTicketUpdateRequest,
    principal: Principal = Depends(require_role(SystemRole.OPERATOR, SystemRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RepairTicketResponse:
    actor = request.actor or principal.email or principal.principal_id
    service = get_opencode_repair_service()
    ticket = await service.update_ticket(request.model_copy(update={"actor": actor}), db=db)
    return RepairTicketResponse(ticket=ticket)


@router.get("/tickets", response_model=RepairTicketsResponse)
async def list_tickets(db: AsyncSession = Depends(get_db)) -> RepairTicketsResponse:
    service = get_opencode_repair_service()
    return RepairTicketsResponse(items=await service.list_tickets(db=db))


@router.get("/audit", response_model=RepairAuditResponse)
async def list_ticket_audit(db: AsyncSession = Depends(get_db)) -> RepairAuditResponse:
    service = get_opencode_repair_service()
    return RepairAuditResponse(items=await service.list_audit_entries(db=db))
