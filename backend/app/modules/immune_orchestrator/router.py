"""API router for Immune Orchestrator."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import require_auth
from app.core.database import get_db
from app.modules.immune_orchestrator.schemas import (
    DecisionsResponse,
    EvaluateSignalResponse,
    ImmuneAuditResponse,
    ImmuneMetrics,
    IncidentSignal,
    SignalsResponse,
)
from app.modules.immune_orchestrator.service import get_immune_orchestrator_service


router = APIRouter(
    prefix="/api/immune-orchestrator",
    tags=["Immune Orchestrator"],
    dependencies=[Depends(require_auth)],
)


@router.post("/signals", response_model=EvaluateSignalResponse)
async def ingest_signal(signal: IncidentSignal, db: AsyncSession = Depends(get_db)) -> EvaluateSignalResponse:
    service = get_immune_orchestrator_service()
    decision = await service.ingest_signal(signal, db)
    return EvaluateSignalResponse(signal=signal, decision=decision)


@router.get("/signals", response_model=SignalsResponse)
async def list_signals(db: AsyncSession = Depends(get_db)) -> SignalsResponse:
    service = get_immune_orchestrator_service()
    return SignalsResponse(items=await service.list_signals(db=db))


@router.get("/decisions", response_model=DecisionsResponse)
async def list_decisions(db: AsyncSession = Depends(get_db)) -> DecisionsResponse:
    service = get_immune_orchestrator_service()
    return DecisionsResponse(items=await service.list_decisions(db=db))


@router.get("/audit", response_model=ImmuneAuditResponse)
async def list_audit_entries(db: AsyncSession = Depends(get_db)) -> ImmuneAuditResponse:
    service = get_immune_orchestrator_service()
    return ImmuneAuditResponse(items=await service.list_audit_entries(db=db))


@router.get("/metrics", response_model=ImmuneMetrics)
async def get_metrics(db: AsyncSession = Depends(get_db)) -> ImmuneMetrics:
    service = get_immune_orchestrator_service()
    return await service.metrics(db=db)
