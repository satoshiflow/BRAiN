"""
Memory Module - API Routes

FastAPI endpoints for the Advanced Memory Architecture.
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, status
from loguru import logger

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

router = APIRouter(prefix="/api/memory", tags=["memory"])


# ============================================================================
# Info & Stats
# ============================================================================


@router.get("/info", response_model=MemorySystemInfo)
async def memory_info():
    """Get memory system module information."""
    svc = get_memory_service()
    return await svc.get_info()


@router.get("/stats", response_model=MemoryStats)
async def memory_stats():
    """Get memory system statistics."""
    svc = get_memory_service()
    return await svc.get_stats()


# ============================================================================
# Memory CRUD
# ============================================================================


@router.post("/store", response_model=MemoryEntry, status_code=status.HTTP_201_CREATED)
async def store_memory(request: MemoryStoreRequest):
    """Store a new memory entry."""
    svc = get_memory_service()
    return await svc.store_memory(request)


@router.get("/entries/{memory_id}", response_model=MemoryEntry)
async def get_memory(memory_id: str):
    """Get a memory by ID."""
    svc = get_memory_service()
    entry = await svc.get_memory(memory_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Memory '{memory_id}' not found")
    return entry


@router.delete("/entries/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: str):
    """Delete a memory."""
    svc = get_memory_service()
    if not await svc.delete_memory(memory_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Memory '{memory_id}' not found")


# ============================================================================
# Recall
# ============================================================================


@router.post("/recall", response_model=MemoryRecallResult)
async def recall_memories(query: MemoryQuery):
    """
    Selective recall with KARMA-scored ranking.

    Combines keyword matching, importance scoring, recency,
    and access frequency for optimal retrieval.
    """
    svc = get_memory_service()
    return await svc.recall_memories(query)


# ============================================================================
# Sessions
# ============================================================================


@router.post("/sessions", response_model=SessionContext, status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreateRequest):
    """
    Create a new working memory session for an agent.

    If the agent already has a session, the old one is ended
    and its context is promoted to episodic memory.
    """
    svc = get_memory_service()
    return await svc.start_session(
        agent_id=request.agent_id,
        max_tokens=request.max_tokens,
        metadata=request.metadata,
    )


@router.get("/sessions/{session_id}", response_model=SessionContext)
async def get_session(session_id: str):
    """Get a session by ID."""
    svc = get_memory_service()
    session = await svc.get_session(session_id)
    if not session:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    return session


@router.delete("/sessions/{session_id}")
async def end_session(session_id: str):
    """
    End a session. Important context is promoted to episodic memory.
    """
    svc = get_memory_service()
    result = await svc.end_session(session_id)
    if not result:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    return result


@router.get("/sessions", response_model=list[SessionContext])
async def list_sessions(agent_id: Optional[str] = Query(None)):
    """List active sessions, optionally filtered by agent."""
    svc = get_memory_service()
    return await svc.list_sessions(agent_id)


# ============================================================================
# Conversation turns
# ============================================================================


@router.post("/sessions/{session_id}/turns", response_model=ConversationTurn)
async def add_turn(session_id: str, request: SessionAddTurnRequest):
    """
    Add a conversation turn to a session.

    Auto-compresses oldest turns when token budget is near limit.
    """
    svc = get_memory_service()
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
async def get_context_window(session_id: str):
    """
    Get the current context window for a session.

    Returns compressed summary + recent turns, ready for LLM consumption.
    """
    svc = get_memory_service()
    ctx = await svc.get_context_window(session_id)
    if not ctx:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Session '{session_id}' not found")
    return ctx


# ============================================================================
# Cross-session
# ============================================================================


@router.get("/agents/{agent_id}/history", response_model=list[MemoryEntry])
async def get_agent_history(
    agent_id: str,
    limit: int = Query(20, ge=1, le=100),
    min_importance: float = Query(30.0, ge=0.0, le=100.0),
):
    """Get an agent's cross-session memory history."""
    svc = get_memory_service()
    return await svc.get_agent_history(agent_id, limit, min_importance)


@router.get("/missions/{mission_id}/context", response_model=list[MemoryEntry])
async def get_mission_context(mission_id: str):
    """Get all memories associated with a mission."""
    svc = get_memory_service()
    return await svc.get_mission_context(mission_id)


# ============================================================================
# Compression & Maintenance
# ============================================================================


@router.post("/compress", response_model=CompressionResult)
async def compress_memories(request: CompressionRequest):
    """
    Compress old memories to reduce storage and improve retrieval.
    """
    svc = get_memory_service()
    return await svc.compress_old(
        max_age_hours=request.max_age_hours,
        target_ratio=request.target_ratio,
        agent_id=request.agent_id,
    )


@router.post("/merge/{agent_id}")
async def merge_memories(
    agent_id: str,
    memory_type: Optional[MemoryType] = Query(None),
):
    """
    Merge related episodic memories into semantic knowledge.
    """
    svc = get_memory_service()
    count = await svc.merge_memories(agent_id, memory_type)
    return {"merged": count, "agent_id": agent_id}


@router.post("/maintenance")
async def run_maintenance():
    """
    Run memory maintenance: evict expired, apply importance decay.
    """
    svc = get_memory_service()
    return await svc.run_maintenance()
