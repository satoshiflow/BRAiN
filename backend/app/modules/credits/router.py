"""Credits API Router - Credit system v2.0 endpoints.

Implements Myzel-Hybrid-Charta:
- Agent/mission account management
- Credit consumption and refunds
- Transaction history and ledger integrity
- Regeneration control
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

from app.core.security import Principal, get_current_principal
from . import service
from .schemas import CreditsHealth, CreditsInfo

router = APIRouter(
    prefix="/api/credits",
    tags=["credits"],
)


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateAgentAccountRequest(BaseModel):
    agent_id: str
    skill_level: Optional[float] = Field(None, ge=0.0, le=1.0)


class CreateMissionBudgetRequest(BaseModel):
    mission_id: str
    complexity: float = Field(1.0, ge=0.5, le=5.0)
    estimated_duration_hours: float = Field(1.0, gt=0.0)


class ConsumeCreditsRequest(BaseModel):
    entity_id: str
    amount: float = Field(gt=0.0)
    reason: str
    metadata: Optional[dict] = None


class CheckSufficientCreditsRequest(BaseModel):
    entity_id: str
    required_amount: float = Field(gt=0.0)


class WithdrawCreditsRequest(BaseModel):
    entity_id: str
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    reason: str
    metadata: Optional[dict] = None


class RefundCreditsRequest(BaseModel):
    entity_id: str
    original_allocation: float = Field(gt=0.0)
    work_completed_percentage: float = Field(ge=0.0, le=1.0)
    reason: str


# ============================================================================
# Agent & Mission Account Endpoints
# ============================================================================

@router.post("/agents/create")
async def create_agent_account(
    request: CreateAgentAccountRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Create credit account for new agent."""
    try:
        return await service.create_agent_account(
            agent_id=request.agent_id,
            skill_level=request.skill_level,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/missions/create")
async def create_mission_budget(
    request: CreateMissionBudgetRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Create credit budget for new mission."""
    try:
        return await service.create_mission_budget(
            mission_id=request.mission_id,
            complexity=request.complexity,
            estimated_duration_hours=request.estimated_duration_hours,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Credit Operations Endpoints
# ============================================================================

@router.post("/consume")
async def consume_credits(
    request: ConsumeCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Consume credits from entity."""
    try:
        return await service.consume_credits(
            entity_id=request.entity_id,
            amount=request.amount,
            reason=request.reason,
            metadata=request.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/check-sufficient")
async def check_sufficient_credits(
    request: CheckSufficientCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Check if entity has sufficient credits."""
    has_sufficient = await service.check_sufficient_credits(
        entity_id=request.entity_id,
        required_amount=request.required_amount,
    )
    current_balance = await service.get_balance(request.entity_id)

    return {
        "entity_id": request.entity_id,
        "required_amount": request.required_amount,
        "current_balance": current_balance,
        "has_sufficient": has_sufficient,
    }


@router.post("/withdraw")
async def withdraw_credits(
    request: WithdrawCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Withdraw credits (ImmuneService Entzug)."""
    try:
        return await service.withdraw_credits(
            entity_id=request.entity_id,
            severity=request.severity,
            reason=request.reason,
            metadata=request.metadata,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refund")
async def refund_credits(
    request: RefundCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """Refund credits (Synergie-Mechanik)."""
    try:
        return await service.refund_credits(
            entity_id=request.entity_id,
            original_allocation=request.original_allocation,
            work_completed_percentage=request.work_completed_percentage,
            reason=request.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Query Endpoints
# ============================================================================

@router.get("/balance/{entity_id}")
async def get_balance(
    entity_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """Get current credit balance for entity."""
    balance = await service.get_balance(entity_id)
    return {
        "entity_id": entity_id,
        "balance": balance,
    }


@router.get("/history")
async def get_transaction_history(
    principal: Principal = Depends(get_current_principal),
    entity_id: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 100,
):
    """Get transaction history with optional filters."""
    return await service.get_transaction_history(
        entity_id=entity_id,
        transaction_type=transaction_type,
        limit=limit,
    )


@router.get("/ledger/statistics")
async def get_ledger_statistics(
    principal: Principal = Depends(get_current_principal),
):
    """Get ledger statistics."""
    return await service.get_ledger_statistics()


@router.get("/ledger/verify-integrity")
async def verify_ledger_integrity(
    principal: Principal = Depends(get_current_principal),
):
    """Verify ledger integrity (HMAC-SHA256 signatures)."""
    return await service.verify_ledger_integrity()


# ============================================================================
# Lifecycle Management Endpoints
# ============================================================================

@router.post("/regeneration/start")
async def start_regeneration(
    principal: Principal = Depends(get_current_principal),
):
    """Start background credit regeneration."""
    return await service.start_regeneration()


@router.post("/regeneration/stop")
async def stop_regeneration(
    principal: Principal = Depends(get_current_principal),
):
    """Stop background credit regeneration."""
    return await service.stop_regeneration()


# ============================================================================
# Health & Info (Legacy compatibility)
# ============================================================================

@router.get("/health", response_model=CreditsHealth)
async def credits_health(
    principal: Principal = Depends(get_current_principal),
):
    """Get Credits module health status."""
    return await service.get_health()


@router.get("/info", response_model=CreditsInfo)
async def credits_info(
    principal: Principal = Depends(get_current_principal),
):
    """Get Credits module information."""
    return await service.get_info()
