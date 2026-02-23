"""
Agent Management System - API Router

FastAPI endpoints for agent management with EventStream integration.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth_deps import require_role, get_current_principal, Principal, require_auth
from app.core.security import UserRole
from app.core.rate_limit import limiter, RateLimits

from .schemas import (
    AgentRegister, AgentUpdate, AgentHeartbeat,
    AgentResponse, AgentListResponse, AgentStats, AgentStatus
)
from .service import get_agent_service, AgentService
from .models import AgentModel


router = APIRouter(prefix="/api/agents", tags=["agents"])


def agent_to_response(agent: AgentModel) -> AgentResponse:
    """Convert AgentModel to AgentResponse"""
    return AgentResponse.model_validate(agent)


# ============================================================================
# Registration & Heartbeat
# ============================================================================

@router.post("/register", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    registration: AgentRegister,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new agent.
    
    Called by agents when they start up.
    If agent_id already exists, updates the registration.
    """
    service = get_agent_service()
    
    # Get client info
    host = request.client.host if request.client else None
    
    agent = await service.register_agent(
        db=db,
        registration=registration,
        host=host,
        pid=None  # Could be extracted from headers if needed
    )
    
    return agent_to_response(agent)


@router.post("/heartbeat", response_model=AgentResponse)
@limiter.limit(RateLimits.AGENTS_HEARTBEAT)
async def agent_heartbeat(
    request: Request,
    heartbeat: AgentHeartbeat,
    db: AsyncSession = Depends(get_db),
):
    """
    Process agent heartbeat.
    
    Called periodically by agents to report status.
    Rate limited to prevent flooding.
    """
    service = get_agent_service()
    
    host = request.client.host if request.client else None
    
    agent = await service.process_heartbeat(
        db=db,
        heartbeat=heartbeat,
        host=host
    )
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {heartbeat.agent_id} not found"
        )
    
    return agent_to_response(agent)


# ============================================================================
# CRUD Endpoints
# ============================================================================

@router.get("", response_model=AgentListResponse, dependencies=[Depends(require_auth)])
async def list_agents(
    status: Optional[AgentStatus] = Query(None, description="Filter by status"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    List all agents with optional filtering.
    
    Args:
        status: Filter by agent status (active, offline, etc.)
        agent_type: Filter by agent type (worker, supervisor, etc.)
    """
    service = get_agent_service()
    
    agents = await service.get_agents(db, status=status, agent_type=agent_type)
    
    # Calculate status counts
    by_status = {}
    for agent in agents:
        s = agent.status.value if hasattr(agent.status, 'value') else str(agent.status)
        by_status[s] = by_status.get(s, 0) + 1
    
    return AgentListResponse(
        items=[agent_to_response(a) for a in agents],
        total=len(agents),
        by_status=by_status
    )


@router.get("/{agent_id}", response_model=AgentResponse, dependencies=[Depends(require_auth)])
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get agent by agent_id"""
    service = get_agent_service()
    agent = await service.get_agent(db, agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    return agent_to_response(agent)


@router.put("/{agent_id}", response_model=AgentResponse, dependencies=[Depends(require_auth)])
async def update_agent(
    agent_id: str,
    update: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Update agent properties.
    
    Only updates provided fields. Does not affect status/heartbeat.
    """
    service = get_agent_service()
    agent = await service.update_agent(db, agent_id, update)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    return agent_to_response(agent)


@router.post("/{agent_id}/terminate", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def terminate_agent(
    agent_id: str,
    reason: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Gracefully terminate an agent.
    
    Sets status to TERMINATED. Agent should shut down on next check.
    """
    service = get_agent_service()
    success = await service.terminate_agent(db, agent_id, reason)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    logger.info(f"Agent {agent_id} terminated by {principal.principal_id}: {reason}")
    return {"success": True, "message": f"Agent {agent_id} terminated"}


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Hard delete an agent.
    
    Use with caution - prefer terminate for graceful shutdown.
    """
    service = get_agent_service()
    success = await service.delete_agent(db, agent_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    logger.info(f"Agent {agent_id} deleted by {principal.principal_id}")


# ============================================================================
# Statistics & Monitoring
# ============================================================================

@router.get("/stats/summary", response_model=AgentStats, dependencies=[Depends(require_auth)])
async def get_agent_stats(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """Get agent statistics summary"""
    service = get_agent_service()
    stats = await service.get_stats(db)
    return stats


@router.post("/check-offline", dependencies=[Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN))])
async def check_offline_agents(
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Manually trigger offline agent check.
    
    Automatically run by background worker, but can be triggered manually.
    """
    service = get_agent_service()
    offline_agents = await service.check_offline_agents(db)
    
    return {
        "checked": True,
        "offline_count": len(offline_agents),
        "offline_agent_ids": [a.agent_id for a in offline_agents]
    }


# ============================================================================
# Event Stream
# ============================================================================

@router.get("/events/stream", dependencies=[Depends(require_auth)])
async def stream_agent_events(
    request: Request,
    principal: Principal = Depends(get_current_principal),
):
    """
    SSE endpoint for agent events.
    
    Streams real-time agent events (registered, heartbeat, offline, etc.)
    """
    from fastapi.responses import StreamingResponse
    import asyncio
    import json
    
    async def event_generator():
        """Generate SSE events"""
        # TODO: Integrate with EventStream for real events
        # For now, send keepalive every 30 seconds
        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'keepalive', 'timestamp': datetime.utcnow().isoformat()})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
