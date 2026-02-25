"""
Memory Module - API Routes

FastAPI endpoints for the Advanced Memory Architecture.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query, status, Depends, Path
from loguru import logger

from app.core.auth_deps import require_auth, require_role, Principal
from app.core.security import UserRole

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
    MemorySystemInfo,
    MemoryType,
    SessionAddTurnRequest,
    SessionContext,
    SessionCreateRequest,
)
from .service import get_memory_service

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
    return await svc.get_stats()


# ============================================================================
# Memory CRUD
# ============================================================================


@router.post("/store", response_model=MemoryEntry, status_code=status.HTTP_201_CREATED)
async def store_memory(
    request: MemoryStoreRequest,
    principal: Principal = Depends(require_role(UserRole.OPERATOR)),
):
    """Store a new memory entry."""
    svc = get_memory_service()
    memory = await svc.store_memory(request)
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
    entry = await svc.get_memory(memory_id)
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
    # Get the memory first to verify ownership
    entry = await svc.get_memory(memory_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Memory '{memory_id}' not found")
    # Verify ownership
    if entry.agent_id and not await verify_agent_ownership(principal, entry.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this memory")

    await svc.delete_memory(memory_id)
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
    if query.agent_id and not await verify_agent_ownership(principal, query.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this agent")
    svc = get_memory_service()
    return await svc.recall_memories(query)


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
    if not await verify_agent_ownership(principal, request.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this agent")

    svc = get_memory_service()
    session = await svc.start_session(
        agent_id=request.agent_id,
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
    session = await svc.get_session(session_id)
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
    # Get session first to verify ownership
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    # Verify ownership
    if not await verify_agent_ownership(principal, session.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")

    result = await svc.end_session(session_id)
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
    return await svc.list_sessions(agent_id)


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
    # Get session first to verify ownership
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    # Verify ownership
    if not await verify_agent_ownership(principal, session.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")

    turn = await svc.add_turn(
        session_id=session_id,
        role=request.role,
        content=request.content,
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
    # Get session first to verify ownership
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    # Verify ownership
    if not await verify_agent_ownership(principal, session.agent_id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this session")

    ctx = await svc.get_context_window(session_id)
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
    return await svc.get_agent_history(agent_id, limit, min_importance)


@router.get("/missions/{mission_id}/context", response_model=list[MemoryEntry])
async def get_mission_context(
    mission_id: str = Path(..., max_length=100),
    principal: Principal = Depends(require_auth),
):
    """Get all memories associated with a mission."""
    svc = get_memory_service()
    # Get mission context and verify ownership of associated agent (if any)
    return await svc.get_mission_context(mission_id)


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
    return await svc.run_maintenance()
