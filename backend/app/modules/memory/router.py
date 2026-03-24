"""
Memory Module - API Routes

FastAPI endpoints for the Advanced Memory Architecture.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query, status, Depends, Path
from loguru import logger

from app.core.auth_deps import require_auth, require_role, Principal, SystemRole as UserRole

from .schemas import (
    CompressionRequest,
    CompressionResult,
    ConversationTurn,
    MemoryEntry,
    MemoryLayer,
    MemoryQuery,
    MemoryRecallResult,
    MemoryStats,
    MemoryStoreRequest,
    SkillRunMemoryIngestResponse,
    MemorySystemInfo,
    MemoryType,
    SessionAddTurnRequest,
    SessionContext,
    SessionCreateRequest,
)
from .service import get_memory_service
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.module_lifecycle.service import get_module_lifecycle_service
from app.modules.skill_engine.service import get_skill_engine_service
from app.modules.skill_evaluator.service import get_skill_evaluator_service

router = APIRouter(
    prefix="/api/memory",
    tags=["memory"],
)


# ============================================================================
# Authorization Helpers
# ============================================================================


async def verify_agent_ownership(principal: Principal, agent_id: str) -> bool:
    """
    Verify that principal can access memories for this agent.

    Admins can access any agent's memories.
    Users can only access their own agent's memories.
    """
    if principal.has_role("admin"):
        return True
    return principal.agent_id == agent_id


async def _ensure_memory_writable(db: AsyncSession) -> None:
    if db is None:
        return
    item = await get_module_lifecycle_service().get_module(db, "memory")
    if item and item.lifecycle_status in {"deprecated", "retired"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"memory is {item.lifecycle_status}; writes are blocked",
        )


def _require_tenant(principal: Principal) -> str:
    if not principal.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context required")
    return principal.tenant_id


# ============================================================================
# Info & Stats
# ============================================================================


@router.get("/info", response_model=MemorySystemInfo)
async def memory_info(principal: Principal = Depends(require_auth)):
    """Get memory system module information."""
    svc = get_memory_service()
    return await svc.get_info()


@router.get("/stats", response_model=MemoryStats)
async def memory_stats(principal: Principal = Depends(require_auth)):
    """Get memory system statistics."""
    svc = get_memory_service()
    return await svc.get_stats_for_tenant(principal.tenant_id)


# ============================================================================
# Memory CRUD
# ============================================================================


@router.post("/store", response_model=MemoryEntry, status_code=status.HTTP_201_CREATED)
async def store_memory(
    request: MemoryStoreRequest,
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    """Store a new memory entry."""
    await _ensure_memory_writable(db)
    tenant_id = _require_tenant(principal)
    svc = get_memory_service()
    memory = await svc.store_memory(request.model_copy(update={"tenant_id": tenant_id}))
    logger.info(
        "Memory entry stored",
        extra={
            "memory_id": memory.memory_id,
            "agent_id": request.agent_id,
            "principal_id": principal.principal_id,
            "action": "store_memory",
        },
    )
    return memory


@router.get("/entries/{memory_id}", response_model=MemoryEntry)
async def get_memory(
    memory_id: str,
    principal: Principal = Depends(require_auth),
):
    """Get a memory by ID."""
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    entry = await svc.get_memory_for_tenant(memory_id, tenant_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Memory '{memory_id}' not found")
    # Verify ownership if agent_id is present
    if entry.agent_id and not await verify_agent_ownership(principal, entry.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this memory")
    return entry


@router.delete("/entries/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: str,
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    """Delete a memory."""
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    # Get the memory first to verify ownership
    entry = await svc.get_memory_for_tenant(memory_id, tenant_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Memory '{memory_id}' not found")
    # Verify ownership
    if entry.agent_id and not await verify_agent_ownership(principal, entry.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this memory")

    await svc.delete_memory(memory_id, tenant_id=tenant_id)
    logger.info(
        "Memory entry deleted",
        extra={
            "memory_id": memory_id,
            "agent_id": entry.agent_id,
            "principal_id": principal.principal_id,
            "action": "delete_memory",
        },
    )


# ============================================================================
# Recall
# ============================================================================


@router.post("/recall", response_model=MemoryRecallResult)
async def recall_memories(
    query: MemoryQuery,
    principal: Principal = Depends(require_auth),
):
    """
    Selective recall with KARMA-scored ranking.

    Combines keyword matching, importance scoring, recency,
    and access frequency for optimal retrieval.
    """
    # Verify ownership if agent_id is specified
    tenant_id = _require_tenant(principal)
    if query.agent_id and not await verify_agent_ownership(principal, query.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this agent")
    svc = get_memory_service()
    return await svc.recall_memories(query.model_copy(update={"tenant_id": tenant_id}))


# ============================================================================
# Sessions
# ============================================================================


@router.post("/sessions", response_model=SessionContext, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreateRequest,
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    """
    Create a new working memory session for an agent.

    If the agent already has a session, the old one is ended
    and its context is promoted to episodic memory.
    """
    # Verify ownership for agent-specific resources
    tenant_id = _require_tenant(principal)
    if not await verify_agent_ownership(principal, request.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this agent")

    svc = get_memory_service()
    session = await svc.start_session(
        agent_id=request.agent_id,
        tenant_id=tenant_id,
        max_tokens=request.max_tokens,
        metadata=request.metadata,
    )
    logger.info(
        "Memory session created",
        extra={
            "session_id": session.session_id,
            "agent_id": request.agent_id,
            "principal_id": principal.principal_id,
            "action": "create_session",
        },
    )
    return session


@router.get("/sessions/{session_id}", response_model=SessionContext)
async def get_session(
    session_id: str = Path(..., max_length=100),
    principal: Principal = Depends(require_auth),
):
    """Get a session by ID."""
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    session = await svc.get_session(session_id, tenant_id=tenant_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    # Verify ownership
    if not await verify_agent_ownership(principal, session.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")
    return session


@router.delete("/sessions/{session_id}")
async def end_session(
    session_id: str = Path(..., max_length=100),
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    """
    End a session. Important context is promoted to episodic memory.
    """
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    # Get session first to verify ownership
    session = await svc.get_session(session_id, tenant_id=tenant_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    # Verify ownership
    if not await verify_agent_ownership(principal, session.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")

    result = await svc.end_session(session_id, tenant_id=tenant_id)
    logger.info(
        "Memory session ended",
        extra={
            "session_id": session_id,
            "agent_id": session.agent_id,
            "principal_id": principal.principal_id,
            "action": "end_session",
        },
    )
    return result


@router.get("/sessions", response_model=list[SessionContext])
async def list_sessions(
    agent_id: Optional[str] = Query(None, max_length=100),
    principal: Principal = Depends(require_auth),
):
    """List active sessions, optionally filtered by agent."""
    # If filtering by agent_id, verify ownership
    if agent_id and not await verify_agent_ownership(principal, agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this agent")
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    return await svc.list_sessions(agent_id, tenant_id=tenant_id)


# ============================================================================
# Conversation turns
# ============================================================================


@router.post("/sessions/{session_id}/turns", response_model=ConversationTurn)
async def add_turn(
    session_id: str,
    request: SessionAddTurnRequest,
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    """
    Add a conversation turn to a session.

    Auto-compresses oldest turns when token budget is near limit.
    """
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    # Get session first to verify ownership
    session = await svc.get_session(session_id, tenant_id=tenant_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    # Verify ownership
    if not await verify_agent_ownership(principal, session.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")

    turn = await svc.add_turn(
        session_id=session_id,
        role=request.role,
        content=request.content,
        tenant_id=tenant_id,
        metadata=request.metadata,
    )
    if not turn:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    return turn


@router.get("/sessions/{session_id}/context")
async def get_context_window(
    session_id: str = Path(..., max_length=100),
    principal: Principal = Depends(require_auth),
):
    """
    Get the current context window for a session.

    Returns compressed summary + recent turns, ready for LLM consumption.
    """
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    # Get session first to verify ownership
    session = await svc.get_session(session_id, tenant_id=tenant_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    # Verify ownership
    if not await verify_agent_ownership(principal, session.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")

    ctx = await svc.get_context_window(session_id, tenant_id=tenant_id)
    if not ctx:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    return ctx


# ============================================================================
# Cross-session
# ============================================================================


@router.get("/agents/{agent_id}/history", response_model=list[MemoryEntry])
async def get_agent_history(
    agent_id: str = Path(..., max_length=100),
    limit: int = Query(20, ge=1, le=100),
    min_importance: float = Query(30.0, ge=0.0, le=100.0),
    principal: Principal = Depends(require_auth),
):
    """Get an agent's cross-session memory history."""
    # Verify ownership
    if not await verify_agent_ownership(principal, agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this agent")
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    return await svc.get_agent_history(agent_id, tenant_id=tenant_id, limit=limit, min_importance=min_importance)


@router.get("/missions/{mission_id}/context", response_model=list[MemoryEntry])
async def get_mission_context(
    mission_id: str = Path(..., max_length=100),
    principal: Principal = Depends(require_auth),
):
    """Get all memories associated with a mission."""
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    # Get mission context and verify ownership of associated agent (if any)
    return await svc.get_mission_context(mission_id, tenant_id=tenant_id)


@router.get("/skill-runs/{skill_run_id}", response_model=list[MemoryEntry])
async def get_skill_run_context(
    skill_run_id: str = Path(..., max_length=64),
    principal: Principal = Depends(require_auth),
):
    svc = get_memory_service()
    tenant_id = _require_tenant(principal)
    return await svc.get_skill_run_context(skill_run_id, tenant_id=tenant_id)


@router.post("/skill-runs/{skill_run_id}/ingest", response_model=SkillRunMemoryIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_skill_run_memory(
    skill_run_id: str = Path(..., max_length=64),
    db: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    await _ensure_memory_writable(db)
    run = await get_skill_engine_service().get_run(db, skill_run_id, principal.tenant_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Skill run not found")
    memory = await get_memory_service().store_memory(
        MemoryStoreRequest(
            tenant_id=_require_tenant(principal),
            content=f"SkillRun {run.skill_key} v{run.skill_version} ended as {run.state}",
            memory_type=MemoryType.MISSION_OUTCOME,
            layer=MemoryLayer.EPISODIC,
            agent_id=run.requested_by,
            mission_id=run.mission_id,
            skill_run_id=str(run.id),
            importance=75.0 if run.state == 'succeeded' else 85.0,
            tags=[run.skill_key, run.state],
            metadata={
                "evaluation_summary": run.evaluation_summary,
                "failure_code": run.failure_code,
                "correlation_id": run.correlation_id,
            },
        )
    )
    return SkillRunMemoryIngestResponse(skill_run_id=str(run.id), memory=memory)


# ============================================================================
# Compression & Maintenance
# ============================================================================


@router.post("/compress", response_model=CompressionResult)
async def compress_memories(
    request: CompressionRequest,
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    """
    Compress old memories to reduce storage and improve retrieval.
    """
    # Verify ownership if agent_id is specified
    if request.agent_id and not await verify_agent_ownership(principal, request.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this agent")

    svc = get_memory_service()
    return await svc.compress_old(
        max_age_hours=request.max_age_hours,
        target_ratio=request.target_ratio,
        agent_id=request.agent_id,
    )


@router.post("/merge/{agent_id}")
async def merge_memories(
    agent_id: str = Path(..., max_length=100),
    memory_type: Optional[MemoryType] = Query(None),
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    """
    Merge related episodic memories into semantic knowledge.
    """
    # Verify ownership
    if not await verify_agent_ownership(principal, agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this agent")

    svc = get_memory_service()
    count = await svc.merge_memories(agent_id, memory_type)
    return {"merged": count, "agent_id": agent_id}


@router.post("/maintenance")
async def run_maintenance(
    principal: Principal = Depends(require_role(UserRole.ADMIN)),
):
    """
    Run memory maintenance: evict expired, apply importance decay.
    """
    svc = get_memory_service()
    logger.info(
        "Memory maintenance started",
        extra={"principal_id": principal.principal_id, "action": "run_maintenance"},
    )
    return await svc.run_maintenance_for_tenant(principal.tenant_id)
