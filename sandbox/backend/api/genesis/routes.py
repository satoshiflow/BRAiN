"""
API Routes for Genesis Agent

This module provides REST API endpoints for the Genesis Agent System including:
- Agent creation (POST /genesis/create)
- System information (GET /genesis/info)
- Template information (GET /genesis/templates)
- Customization help (GET /genesis/customizations)

Security:
- All creation endpoints require SYSTEM_ADMIN role
- Rate limiting enforced (10 requests per minute)
- Kill switch check before each creation
- Budget reserve protection

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter

from app.core.redis_client import get_redis
from brain.agents.genesis_agent.config import get_genesis_settings
from brain.agents.genesis_agent.dna_validator import ValidationError
from brain.agents.genesis_agent.events import SimpleAuditLog
from brain.agents.genesis_agent.genesis_agent import (
    GenesisAgent,
    InMemoryBudget,
    InMemoryRegistry,
)

from .auth import require_auth
from .schemas import (
    AgentCreationRequest,
    AgentCreationResponse,
    BudgetCheckResponse,
    CustomizationHelpResponse,
    ErrorResponse,
    GenesisInfoResponse,
    TemplateInfoResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/genesis", tags=["genesis"])

# Global instances (in production, use dependency injection)
_registry = InMemoryRegistry()
_budget = InMemoryBudget(initial_credits=10000)
_audit_log = SimpleAuditLog()
_genesis: Optional[GenesisAgent] = None


async def get_genesis_agent() -> GenesisAgent:
    """
    Get or create Genesis Agent instance.

    Returns:
        GenesisAgent: Singleton Genesis Agent

    Example:
        >>> genesis = await get_genesis_agent()
    """
    global _genesis
    if _genesis is None:
        redis_client = await get_redis()
        settings = get_genesis_settings()
        _genesis = GenesisAgent(
            registry=_registry,
            redis_client=redis_client,
            audit_log=_audit_log,
            budget=_budget,
            settings=settings
        )
    return _genesis


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "/create",
    response_model=AgentCreationResponse,
    responses={
        200: {"description": "Agent created successfully"},
        400: {"model": ErrorResponse, "description": "Validation error"},
        403: {"model": ErrorResponse, "description": "Insufficient permissions"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded or insufficient budget"},
        503: {"model": ErrorResponse, "description": "Genesis system disabled"},
    },
    dependencies=[Depends(RateLimiter(times=10, seconds=60))],
)
async def create_agent(
    request: AgentCreationRequest,
    user_id: str = Depends(require_auth),
    genesis: GenesisAgent = Depends(get_genesis_agent),
):
    """
    Create a new agent from template.

    This endpoint creates a new agent with the following security controls:
    - Requires SYSTEM_ADMIN role
    - Rate limited to 10 requests per minute
    - Kill switch check (GENESIS_ENABLED)
    - Budget reserve protection (20%)
    - Idempotency via request_id

    Request Body:
        ```json
        {
            "request_id": "req-abc123",
            "template_name": "worker_base",
            "customizations": {
                "metadata.name": "worker_api_specialist",
                "skills[].domains": ["rest_api", "graphql"]
            }
        }
        ```

    Returns:
        AgentCreationResponse with agent details

    Raises:
        HTTPException:
            - 400: Validation error (invalid DNA or customizations)
            - 403: Insufficient permissions (not SYSTEM_ADMIN)
            - 429: Budget exceeded or rate limit
            - 503: Genesis system disabled (kill switch)
    """
    settings = get_genesis_settings()

    # Check kill switch
    if not settings.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Genesis system disabled by administrator. "
                   "Contact system admin to enable agent creation."
        )

    # Check budget reserve
    estimated_cost = await genesis.estimate_cost(request.template_name)
    has_budget = await genesis.check_budget(estimated_cost)

    if not has_budget:
        available = await _budget.get_available_credits()
        reserve = int(available * settings.reserve_ratio)
        usable = available - reserve

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Insufficient budget. Need {estimated_cost} credits, "
                   f"have {usable} after reserve ({reserve} reserved)."
        )

    # Create agent
    try:
        dna = await genesis.create_agent(
            request_id=request.request_id,
            template_name=request.template_name,
            customizations=request.customizations
        )

        # Compute hashes for response
        dna_hash = genesis.compute_dna_hash(dna)

        return AgentCreationResponse(
            success=True,
            agent_id=str(dna.metadata.id),
            status="CREATED",
            message=f"Agent '{dna.metadata.name}' created successfully",
            cost=estimated_cost,
            dna_hash=dna_hash,
            template_hash=dna.metadata.template_hash
        )

    except ValidationError as e:
        logger.warning(f"Validation error during agent creation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        logger.error(f"Agent creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent creation failed: {str(e)}"
        )


@router.get(
    "/info",
    response_model=GenesisInfoResponse,
    responses={
        200: {"description": "Genesis system information"},
    },
)
async def get_info(
    genesis: GenesisAgent = Depends(get_genesis_agent),
):
    """
    Get Genesis system information.

    Returns information about the Genesis Agent System including:
    - System version
    - Kill switch status
    - Available templates
    - Budget reserve ratio

    This endpoint does NOT require authentication (public info).

    Returns:
        GenesisInfoResponse with system details
    """
    settings = get_genesis_settings()
    available_templates = genesis.validator.list_available_templates()

    return GenesisInfoResponse(
        name="Genesis Agent System",
        version="2.0.0",
        enabled=settings.enabled,
        templates_available=available_templates,
        reserve_ratio=settings.reserve_ratio
    )


@router.get(
    "/templates",
    response_model=List[TemplateInfoResponse],
    responses={
        200: {"description": "List of available templates"},
    },
)
async def list_templates(
    genesis: GenesisAgent = Depends(get_genesis_agent),
):
    """
    List all available agent templates.

    Returns information about each template including:
    - Template name
    - Template hash (SHA256)
    - Agent type
    - Description

    This endpoint does NOT require authentication (public info).

    Returns:
        List[TemplateInfoResponse]: List of template information
    """
    templates = genesis.validator.list_available_templates()
    result = []

    for template_name in templates:
        try:
            # Load template to get info
            dna = await genesis.load_template(template_name)
            template_hash = genesis.validator.compute_template_hash(template_name)

            result.append(
                TemplateInfoResponse(
                    template_name=template_name,
                    template_hash=template_hash,
                    agent_type=dna.metadata.type.value,
                    description=f"{dna.metadata.type.value} agent for {dna.traits.primary_function}"
                )
            )
        except Exception as e:
            logger.warning(f"Failed to load template {template_name}: {e}")

    return result


@router.get(
    "/customizations",
    response_model=CustomizationHelpResponse,
    responses={
        200: {"description": "Allowed customizations documentation"},
    },
)
async def get_customization_help(
    genesis: GenesisAgent = Depends(get_genesis_agent),
):
    """
    Get documentation for allowed customizations.

    Returns the whitelist of fields that can be customized when creating
    an agent, along with validation rules for each field.

    This endpoint does NOT require authentication (public info).

    Returns:
        CustomizationHelpResponse: Customization documentation
    """
    help_info = genesis.validator.get_customization_help()

    return CustomizationHelpResponse(
        allowed_customizations=help_info
    )


@router.get(
    "/budget",
    response_model=BudgetCheckResponse,
    responses={
        200: {"description": "Budget information"},
        403: {"description": "Insufficient permissions"},
    },
)
async def check_budget(
    template_name: str,
    user_id: str = Depends(require_auth),
    genesis: GenesisAgent = Depends(get_genesis_agent),
):
    """
    Check budget availability for creating an agent.

    This endpoint checks if sufficient budget is available to create
    an agent from the specified template, accounting for the reserve.

    Requires SYSTEM_ADMIN role.

    Args:
        template_name: Name of template to check cost for

    Returns:
        BudgetCheckResponse: Budget availability information
    """
    settings = get_genesis_settings()

    # Get costs
    required_credits = await genesis.estimate_cost(template_name)
    available_total = await _budget.get_available_credits()
    reserve_amount = int(available_total * settings.reserve_ratio)
    available_usable = available_total - reserve_amount

    has_sufficient = available_usable >= required_credits

    return BudgetCheckResponse(
        available_credits=available_usable,
        required_credits=required_credits,
        has_sufficient_budget=has_sufficient,
        reserve_amount=reserve_amount
    )


@router.post(
    "/killswitch",
    responses={
        200: {"description": "Kill switch toggled"},
        403: {"description": "Insufficient permissions"},
    },
)
async def toggle_killswitch(
    enabled: bool,
    user_id: str = Depends(require_auth),
):
    """
    Toggle Genesis kill switch.

    This endpoint enables or disables the Genesis Agent system.
    When disabled, all agent creation requests will be rejected.

    Requires SYSTEM_ADMIN role.

    Args:
        enabled: True to enable, False to disable

    Returns:
        dict: New kill switch status
    """
    settings = get_genesis_settings()
    settings.enabled = enabled

    logger.warning(
        f"Genesis kill switch toggled by {user_id}: enabled={enabled}"
    )

    # Emit event if disabled
    if not enabled:
        redis_client = await get_redis()
        await genesis.GenesisEvents.killswitch_triggered(
            reason=f"Manual shutdown by {user_id}",
            redis_client=redis_client,
            audit_log=_audit_log
        )

    return {
        "enabled": enabled,
        "message": f"Genesis system {'enabled' if enabled else 'disabled'}"
    }
