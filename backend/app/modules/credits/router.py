"""
Credits API Router

REST API endpoints for the credit system.

Endpoints:
- GET /health - Health check
- GET /info - Module information
- GET /balance/{entity_id} - Get credit balance
- GET /ledger/{entity_id} - Get transaction history
- POST /agents - Create agent with credits
- POST /spend - Spend credits
- POST /transfer - Transfer credits
- POST /tax/collect - Collect existence tax (admin)
- POST /tax/auto-terminate - Check auto-termination (admin)
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import Principal, get_current_principal

from .models import (
    CreditAllocationRequest,
    CreditBalance,
    CreditSpendRequest,
    CreditTransaction,
    CreditTransferRequest,
    CreditType,
)
from .schemas import CreditsHealth, CreditsInfo
from .service import CreditsService, get_health, get_info

router = APIRouter(
    prefix="/api/credits/v2",
    tags=["credits-v2"],
)


def get_credits_service(
    session: AsyncSession = Depends(get_session),
) -> CreditsService:
    """Dependency: Get credits service instance."""
    # TODO: Get signing key from settings
    return CreditsService(session, signing_key="CHANGE_ME_IN_PRODUCTION")


# ============================================================================
# SYSTEM ENDPOINTS
# ============================================================================


@router.get("/health", response_model=CreditsHealth)
async def credits_health(principal: Principal = Depends(get_current_principal)):
    """Get module health status."""
    return await get_health()


@router.get("/info", response_model=CreditsInfo)
async def credits_info(principal: Principal = Depends(get_current_principal)):
    """Get module information."""
    return await get_info()


# ============================================================================
# BALANCE & LEDGER ENDPOINTS
# ============================================================================


@router.get("/balance/{entity_id}", response_model=CreditBalance)
async def get_balance(
    entity_id: str,
    principal: Principal = Depends(get_current_principal),
    service: CreditsService = Depends(get_credits_service),
):
    """
    Get credit balance for an entity.

    Returns balances for all credit types plus lifetime statistics.
    """
    try:
        balance = await service.get_balance(entity_id)
        return balance
    except Exception as e:
        logger.error(f"Error getting balance for {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ledger/{entity_id}", response_model=list[CreditTransaction])
async def get_ledger(
    entity_id: str,
    credit_type: Optional[CreditType] = None,
    limit: int = 100,
    offset: int = 0,
    principal: Principal = Depends(get_current_principal),
    service: CreditsService = Depends(get_credits_service),
):
    """
    Get transaction history for an entity.

    Query parameters:
    - credit_type: Filter by credit type (optional)
    - limit: Maximum results (default 100, max 1000)
    - offset: Pagination offset (default 0)
    """
    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")

    try:
        transactions = await service.get_transaction_history(
            entity_id=entity_id,
            credit_type=credit_type,
            limit=limit,
            offset=offset,
        )
        return transactions
    except Exception as e:
        logger.error(f"Error getting ledger for {entity_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# AGENT MANAGEMENT ENDPOINTS
# ============================================================================


@router.post("/agents")
async def create_agent(
    request: CreditAllocationRequest,
    principal: Principal = Depends(get_current_principal),
    service: CreditsService = Depends(get_credits_service),
):
    """
    Create a new agent with initial credit allocation.

    The system automatically mints initial credits based on
    the AGENT_CREATION_MINT rule (1000 CC).
    """
    try:
        # Extract agent details from request
        agent_name = request.metadata.get("agent_name", request.entity_id)
        agent_type = request.metadata.get("agent_type", "GENERIC")

        agent = await service.create_agent(
            agent_name=agent_name,
            agent_type=agent_type,
            metadata=request.metadata,
        )

        return {
            "success": True,
            "agent": agent,
            "message": f"Agent {agent_name} created with initial credits",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CREDIT TRANSACTION ENDPOINTS
# ============================================================================


@router.post("/spend", response_model=CreditTransaction)
async def spend_credits(
    request: CreditSpendRequest,
    principal: Principal = Depends(get_current_principal),
    service: CreditsService = Depends(get_credits_service),
):
    """
    Spend (burn) credits from an entity.

    Fails if entity has insufficient credits.
    """
    try:
        # Determine entity type from metadata or default to AGENT
        entity_type = request.metadata.get("entity_type", "AGENT")

        transaction = await service.spend_credits(
            entity_id=request.entity_id,
            entity_type=entity_type,
            credit_type=request.credit_type,
            amount=request.amount,
            reason=request.reason,
            metadata=request.metadata,
        )

        return transaction
    except Exception as e:
        logger.error(f"Error spending credits: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/transfer")
async def transfer_credits(
    request: CreditTransferRequest,
    principal: Principal = Depends(get_current_principal),
    service: CreditsService = Depends(get_credits_service),
):
    """
    Transfer credits between entities.

    Implemented as atomic burn + mint.
    """
    try:
        # Determine entity types
        from_type = request.metadata.get("from_entity_type", "AGENT")
        to_type = request.metadata.get("to_entity_type", "AGENT")

        burn_tx, mint_tx = await service.transfer_credits(
            from_entity_id=request.from_entity_id,
            from_entity_type=from_type,
            to_entity_id=request.to_entity_id,
            to_entity_type=to_type,
            credit_type=request.credit_type,
            amount=request.amount,
            reason=request.reason,
            metadata=request.metadata,
        )

        return {
            "success": True,
            "burn_transaction": burn_tx,
            "mint_transaction": mint_tx,
            "message": f"Transferred {request.amount} {request.credit_type.value}",
        }
    except Exception as e:
        logger.error(f"Error transferring credits: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# TAX & LIFECYCLE ENDPOINTS (ADMIN)
# ============================================================================


@router.post("/tax/collect")
async def collect_existence_tax(
    principal: Principal = Depends(get_current_principal),
    service: CreditsService = Depends(get_credits_service),
):
    """
    Collect existence tax from all active agents.

    **ADMIN ONLY**

    Returns statistics about tax collection.
    """
    # TODO: Check admin permission
    try:
        stats = await service.collect_existence_tax()
        return {
            "success": True,
            "stats": stats,
            "message": f"Collected tax from {stats['collected']} agents",
        }
    except Exception as e:
        logger.error(f"Error collecting existence tax: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tax/auto-terminate")
async def check_auto_terminate(
    principal: Principal = Depends(get_current_principal),
    service: CreditsService = Depends(get_credits_service),
):
    """
    Check for and terminate suspended agents.

    **ADMIN ONLY**

    Terminates agents suspended for longer than threshold (7 days).
    """
    # TODO: Check admin permission
    try:
        stats = await service.check_auto_terminate()
        return {
            "success": True,
            "stats": stats,
            "message": f"Terminated {stats.get('terminated', 0)} agents",
        }
    except Exception as e:
        logger.error(f"Error checking auto-termination: {e}")
        raise HTTPException(status_code=500, detail=str(e))
