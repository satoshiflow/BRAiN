"""
Coordination Module - API Routes

FastAPI endpoints for Multi-Agent Coordination.
"""

from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status, Depends
from loguru import logger

from app.core.auth_deps import require_auth, get_current_principal, Principal

from .schemas import (
    AgentMessage,
    ConflictReport,
    ConflictSeverity,
    CoordinationInfo,
    CoordinationStats,
    KnowledgeEntry,
    KnowledgeQuery,
    TaskDelegationRequest,
    TaskDelegationResult,
    TaskStatus,
    VoteRequest,
    VoteResult,
)
from .service import get_coordination_service

router = APIRouter(
    prefix="/api/coordination",
    tags=["coordination"],
    dependencies=[Depends(require_auth)]
)


# ============================================================================
# Info & Stats
# ============================================================================


@router.get("/info", response_model=CoordinationInfo)
async def coordination_info():
    """Get coordination module information."""
    return CoordinationInfo()


@router.get("/stats", response_model=CoordinationStats)
async def coordination_stats():
    """Get coordination statistics."""
    svc = get_coordination_service()
    return svc.get_stats()


# ============================================================================
# Agent Registration
# ============================================================================


@router.post("/agents/register", status_code=status.HTTP_201_CREATED)
async def register_agent(
    agent_id: str,
    capabilities: List[str],
    max_tasks: int = Query(3, ge=1, le=20),
    karma_score: float = Query(50.0, ge=0.0, le=100.0),
):
    """Register an agent for coordination."""
    svc = get_coordination_service()
    svc.register_agent(agent_id, capabilities, max_tasks, karma_score)
    return {"registered": agent_id, "capabilities": capabilities}


@router.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str):
    """Unregister an agent."""
    svc = get_coordination_service()
    svc.unregister_agent(agent_id)
    return {"unregistered": agent_id}


# ============================================================================
# Messaging
# ============================================================================


@router.post("/messages/send")
async def send_message(message: AgentMessage):
    """Send a message between agents."""
    svc = get_coordination_service()
    response = await svc.send_message(message)
    return {"sent": True, "message_id": message.message_id, "response": response}


@router.get("/messages/{agent_id}", response_model=List[AgentMessage])
async def get_messages(agent_id: str, limit: int = Query(50, ge=1, le=200)):
    """Get messages from an agent's inbox."""
    svc = get_coordination_service()
    return await svc.get_messages(agent_id, limit)


# ============================================================================
# Task Delegation
# ============================================================================


@router.post("/tasks/delegate", response_model=TaskDelegationResult)
async def delegate_task(request: TaskDelegationRequest):
    """Delegate a task to the best-suited agent."""
    svc = get_coordination_service()
    return await svc.delegate_task(request)


@router.get("/tasks/{task_id}")
async def get_task(task_id: str):
    """Get task details."""
    svc = get_coordination_service()
    task = await svc.get_task(task_id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Task '{task_id}' not found")
    return task


@router.get("/tasks", response_model=List)
async def list_tasks(task_status: Optional[TaskStatus] = Query(None)):
    """List tasks, optionally filtered by status."""
    svc = get_coordination_service()
    return await svc.list_tasks(task_status)


@router.post("/tasks/{task_id}/progress")
async def report_progress(task_id: str, agent_id: str):
    """Report task progress."""
    svc = get_coordination_service()
    if not await svc.report_progress(task_id, agent_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found or not assigned to agent")
    return {"status": "in_progress"}


@router.post("/tasks/{task_id}/complete")
async def report_completion(task_id: str, agent_id: str, result: Dict):
    """Report task completion."""
    svc = get_coordination_service()
    if not await svc.report_completion(task_id, agent_id, result):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found or not assigned to agent")
    return {"status": "completed"}


@router.post("/tasks/{task_id}/fail")
async def report_failure(task_id: str, agent_id: str, error: str):
    """Report task failure."""
    svc = get_coordination_service()
    if not await svc.report_failure(task_id, agent_id, error):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found or not assigned to agent")
    return {"status": "failed"}


# ============================================================================
# Voting
# ============================================================================


@router.post("/votes", response_model=VoteResult)
async def initiate_vote(request: VoteRequest):
    """Initiate a vote among agents."""
    svc = get_coordination_service()
    return await svc.initiate_vote(request)


# ============================================================================
# Shared Knowledge
# ============================================================================


@router.post("/knowledge", response_model=KnowledgeEntry, status_code=status.HTTP_201_CREATED)
async def contribute_knowledge(entry: KnowledgeEntry):
    """Contribute knowledge to the shared base."""
    svc = get_coordination_service()
    return svc.contribute_knowledge(entry)


@router.post("/knowledge/query", response_model=List[KnowledgeEntry])
async def query_knowledge(query: KnowledgeQuery):
    """Query the shared knowledge base."""
    svc = get_coordination_service()
    return svc.query_knowledge(query)


@router.get("/knowledge/{key:path}")
async def get_knowledge(key: str):
    """Get knowledge by key."""
    svc = get_coordination_service()
    entry = svc.get_knowledge(key)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Knowledge key '{key}' not found")
    return entry


# ============================================================================
# Conflict Resolution
# ============================================================================


@router.post("/conflicts", response_model=ConflictReport, status_code=status.HTTP_201_CREATED)
async def report_conflict(conflict: ConflictReport):
    """Report a conflict between agents."""
    svc = get_coordination_service()
    return svc.report_conflict(conflict)


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictReport)
async def resolve_conflict(conflict_id: str):
    """Resolve a conflict using Constitution-based strategy."""
    svc = get_coordination_service()
    try:
        return await svc.resolve_conflict(conflict_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))


@router.get("/conflicts", response_model=List[ConflictReport])
async def list_conflicts(
    resolved: Optional[bool] = Query(None),
    severity: Optional[ConflictSeverity] = Query(None),
):
    """List conflicts."""
    svc = get_coordination_service()
    return svc.list_conflicts(resolved, severity)
