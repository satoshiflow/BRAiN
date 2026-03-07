"""API router for Unified Recovery Policy Engine."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_deps import require_auth
from app.core.database import get_db
from app.modules.recovery_policy_engine.schemas import (
    RecoveryAdapterRequest,
    RecoveryAuditListResponse,
    RecoveryDecisionListResponse,
    RecoveryDecisionResponse,
    RecoveryMetrics,
    RecoveryPolicyConfig,
    RecoveryRequest,
)
from app.modules.recovery_policy_engine.service import get_recovery_policy_service


router = APIRouter(
    prefix="/api/recovery-policy",
    tags=["Recovery Policy Engine"],
    dependencies=[Depends(require_auth)],
)


@router.post("/decide", response_model=RecoveryDecisionResponse)
async def decide(request: RecoveryRequest, db: AsyncSession = Depends(get_db)) -> RecoveryDecisionResponse:
    service = get_recovery_policy_service()
    decision = await service.decide(request, db=db)
    return RecoveryDecisionResponse(request=request, decision=decision)


@router.post("/decide/{adapter_name}", response_model=RecoveryDecisionResponse)
async def decide_from_adapter(
    adapter_name: str,
    body: RecoveryAdapterRequest,
    db: AsyncSession = Depends(get_db),
) -> RecoveryDecisionResponse:
    service = get_recovery_policy_service()
    try:
        request = service.build_request_from_adapter(adapter_name, body.payload)
        decision = await service.decide(request, db=db)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown adapter: {adapter_name}")
    return RecoveryDecisionResponse(request=request, decision=decision)


@router.get("/policy", response_model=RecoveryPolicyConfig)
async def get_policy() -> RecoveryPolicyConfig:
    service = get_recovery_policy_service()
    return service.get_policy()


@router.put("/policy", response_model=RecoveryPolicyConfig)
async def update_policy(config: RecoveryPolicyConfig) -> RecoveryPolicyConfig:
    service = get_recovery_policy_service()
    return service.update_policy(config)


@router.get("/decisions", response_model=RecoveryDecisionListResponse)
async def list_decisions(db: AsyncSession = Depends(get_db)) -> RecoveryDecisionListResponse:
    service = get_recovery_policy_service()
    return RecoveryDecisionListResponse(items=await service.list_decisions(db=db))


@router.get("/audit", response_model=RecoveryAuditListResponse)
async def list_audit(db: AsyncSession = Depends(get_db)) -> RecoveryAuditListResponse:
    service = get_recovery_policy_service()
    return RecoveryAuditListResponse(items=await service.list_audit_entries(db=db))


@router.get("/metrics", response_model=RecoveryMetrics)
async def get_metrics(db: AsyncSession = Depends(get_db)) -> RecoveryMetrics:
    service = get_recovery_policy_service()
    return await service.metrics(db=db)
