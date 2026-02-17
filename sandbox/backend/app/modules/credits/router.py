from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from app.core.security import Principal, get_current_principal
from . import service
from .schemas import CreditsHealth, CreditsInfo

router = APIRouter(
    prefix="/api/credits",
    tags=["credits"],
)


# ============================================================================
# Request/Response Models (Event Sourcing)
# ============================================================================


class CreateAgentRequest(BaseModel):
    """Request to create agent with credits."""
    agent_id: str = Field(..., description="Unique agent identifier")
    skill_level: float = Field(..., ge=0.0, le=1.0, description="Skill level (0.0-1.0)")
    actor_id: str = Field(default="system", description="Who created the agent")


class ConsumeCreditsRequest(BaseModel):
    """Request to consume credits."""
    agent_id: str = Field(..., description="Agent consuming credits")
    amount: float = Field(..., gt=0, description="Credits to consume")
    reason: str = Field(..., description="Why credits are consumed")
    mission_id: Optional[str] = Field(None, description="Related mission ID")
    actor_id: str = Field(default="system", description="Who initiated consumption")


class RefundCreditsRequest(BaseModel):
    """Request to refund credits."""
    agent_id: str = Field(..., description="Agent receiving refund")
    amount: float = Field(..., gt=0, description="Credits to refund")
    reason: str = Field(..., description="Why credits are refunded")
    mission_id: Optional[str] = Field(None, description="Related mission ID")
    actor_id: str = Field(default="system", description="Who initiated refund")


class AddCreditsRequest(BaseModel):
    """Request to add credits to existing agent."""
    agent_id: str = Field(..., description="Agent receiving credits")
    amount: float = Field(..., gt=0, description="Credits to add")
    reason: str = Field(..., description="Why credits are added")
    actor_id: str = Field(default="system", description="Who initiated addition")


# ============================================================================
# Basic Endpoints
# ============================================================================


@router.get("/health", response_model=CreditsHealth)
async def credits_health(principal: Principal = Depends(get_current_principal)):
    """Get Credits module health status."""
    return await service.get_health()


@router.get("/info", response_model=CreditsInfo)
async def credits_info(principal: Principal = Depends(get_current_principal)):
    """
    Get Credits module information.

    Returns:
        - Module name and version
        - Event Sourcing status
        - System metrics (if available)
    """
    return await service.get_info()


# ============================================================================
# Event Sourcing Endpoints
# ============================================================================


@router.post("/agents", response_model=Dict)
async def create_agent(
    request: CreateAgentRequest,
    principal: Principal = Depends(get_current_principal),
):
    """
    Create agent and allocate initial credits (Event Sourcing).

    Formula:
        initial_credits = skill_level * 100.0

    Example:
        - skill_level=0.8 → 80.0 credits

    Returns:
        - agent_id
        - initial_credits
        - balance
        - skill_level
    """
    try:
        return await service.create_agent_with_credits(
            agent_id=request.agent_id,
            skill_level=request.skill_level,
            actor_id=request.actor_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/consume", response_model=Dict)
async def consume_credits(
    request: ConsumeCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """
    Consume credits for agent (Event Sourcing).

    Validates:
        - Sufficient credits available
        - Amount > 0

    Returns:
        - agent_id
        - amount
        - balance_after
        - reason
        - mission_id
    """
    try:
        return await service.consume_agent_credits(
            agent_id=request.agent_id,
            amount=request.amount,
            reason=request.reason,
            mission_id=request.mission_id,
            actor_id=request.actor_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/refund", response_model=Dict)
async def refund_credits(
    request: RefundCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """
    Refund credits to agent (Event Sourcing).

    Use cases:
        - Failed mission
        - Cancelled mission
        - System error compensation

    Returns:
        - agent_id
        - amount
        - balance_after
        - reason
        - mission_id
    """
    try:
        return await service.refund_agent_credits(
            agent_id=request.agent_id,
            amount=request.amount,
            reason=request.reason,
            mission_id=request.mission_id,
            actor_id=request.actor_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.post("/add", response_model=Dict)
async def add_credits(
    request: AddCreditsRequest,
    principal: Principal = Depends(get_current_principal),
):
    """
    Add credits to existing agent (Event Sourcing).

    Use cases:
        - Monthly budget top-up
        - Performance bonus
        - Manual credit allocation
        - Subscription renewal

    Returns:
        - agent_id
        - amount
        - balance_after
        - reason

    Example:
        ```json
        {
            "agent_id": "agent_001",
            "amount": 100.0,
            "reason": "Monthly budget top-up",
            "actor_id": "admin"
        }
        ```
    """
    try:
        return await service.add_agent_credits(
            agent_id=request.agent_id,
            amount=request.amount,
            reason=request.reason,
            actor_id=request.actor_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/balance/{agent_id}", response_model=Dict)
async def get_balance(
    agent_id: str,
    principal: Principal = Depends(get_current_principal),
):
    """
    Get current balance for agent (Event Sourcing).

    Returns:
        - agent_id
        - balance (0.0 if agent not found)
    """
    try:
        return await service.get_agent_balance(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/balances", response_model=Dict)
async def get_all_balances(
    principal: Principal = Depends(get_current_principal),
):
    """
    Get all agent balances (Event Sourcing).

    Returns:
        - balances: Dict[agent_id, balance]
        - total_agents: Number of agents
    """
    try:
        return await service.get_all_agent_balances()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/history/{agent_id}", response_model=Dict)
async def get_history(
    agent_id: str,
    limit: int = 10,
    principal: Principal = Depends(get_current_principal),
):
    """
    Get transaction history for agent (Event Sourcing).

    Args:
        - agent_id: Agent ID
        - limit: Max number of entries (default: 10)

    Returns:
        - agent_id
        - history: List[LedgerEntry]
        - total_entries: Number of entries returned
    """
    try:
        return await service.get_agent_history(agent_id, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


@router.get("/metrics", response_model=Dict)
async def get_metrics(
    principal: Principal = Depends(get_current_principal),
):
    """
    Get Event Sourcing system metrics.

    Returns:
        - journal: EventJournal metrics
          - total_events
          - file_size_mb
          - idempotency_violations
        - event_bus: EventBus metrics
          - total_published
          - total_subscriber_errors
          - subscribers_by_type
        - replay: ReplayEngine metrics
          - total_events
          - replay_duration_seconds
          - last_replay_timestamp
          - integrity_errors_count
    """
    try:
        return await service.get_event_sourcing_metrics()
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
