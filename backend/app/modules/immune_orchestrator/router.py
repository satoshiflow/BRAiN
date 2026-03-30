"""API router for Immune Orchestrator."""

from __future__ import annotations

import asyncio
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasicCredentials, HTTPBasic
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


@router.get("/stream")
async def stream_immune_events(
    db: AsyncSession = Depends(get_db),
):
    service = get_immune_orchestrator_service()

    async def event_generator():
        try:
            while True:
                audit = await service.list_audit_entries(db=db)
                decisions = await service.list_decisions(db=db)
                payload = {
                    "audit": [item.model_dump() for item in audit.items[:10]],
                    "decisions": [item.model_dump() for item in decisions.items[:10]],
                }
                yield f"data: {json.dumps(payload)}\n\n"
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
