"""
Coordination Module - Pydantic Models

Models for agent messaging, task delegation, shared knowledge,
and conflict resolution.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Message Types
# ============================================================================


class MessageType(str, Enum):
    """Types of inter-agent messages."""
    REQUEST = "request"          # Ask another agent to do something
    RESPONSE = "response"        # Reply to a request
    BROADCAST = "broadcast"      # Inform all agents
    NOTIFY = "notify"            # One-way notification
    DELEGATE = "delegate"        # Task delegation from supervisor
    VOTE_REQUEST = "vote_request"  # Request a vote
    VOTE_CAST = "vote_cast"      # Cast a vote
    CONFLICT = "conflict"        # Conflict report


class MessagePriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoteOption(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"


class ConflictSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ============================================================================
# Agent Message
# ============================================================================


class AgentMessage(BaseModel):
    """A message between agents."""
    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:12]}")
    message_type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL

    # Routing
    sender_id: str
    target_id: Optional[str] = Field(None, description="None = broadcast")
    reply_to: Optional[str] = Field(None, description="message_id this replies to")

    # Content
    subject: str = Field("", description="Short subject line")
    payload: Dict[str, Any] = Field(default_factory=dict)

    # Metadata
    timestamp: float = Field(default_factory=time.time)
    ttl_seconds: Optional[float] = Field(None, description="Time-to-live; None=forever")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        return (time.time() - self.timestamp) > self.ttl_seconds


# ============================================================================
# Task Delegation
# ============================================================================


class CoordinationTask(BaseModel):
    """A task that can be delegated to an agent."""
    task_id: str = Field(default_factory=lambda: f"ctask_{uuid.uuid4().hex[:10]}")
    name: str
    description: str = ""
    required_capabilities: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timeout_seconds: float = Field(300.0, gt=0)
    max_retries: int = Field(1, ge=0)

    # Assignment
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    assigned_at: Optional[datetime] = None
    delegated_by: Optional[str] = None

    # Result
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    completed_at: Optional[datetime] = None
    attempts: int = Field(0, ge=0)

    # Mission link
    mission_id: Optional[str] = None


class TaskDelegationRequest(BaseModel):
    """Request to delegate a task to the best-suited agent."""
    task_name: str
    description: str = ""
    required_capabilities: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: MessagePriority = MessagePriority.NORMAL
    timeout_seconds: float = 300.0
    preferred_agent_id: Optional[str] = None
    mission_id: Optional[str] = None


class TaskDelegationResult(BaseModel):
    """Result of a delegation decision."""
    task_id: str
    assigned_to: Optional[str] = None
    reason: str = ""
    success: bool = True
    alternatives: List[str] = Field(default_factory=list, description="Other candidate agent IDs")


# ============================================================================
# Voting / Consensus
# ============================================================================


class VoteRequest(BaseModel):
    """Request for agents to vote on a proposal."""
    vote_id: str = Field(default_factory=lambda: f"vote_{uuid.uuid4().hex[:10]}")
    proposal: str
    options: List[VoteOption] = Field(
        default_factory=lambda: [VoteOption.APPROVE, VoteOption.REJECT, VoteOption.ABSTAIN]
    )
    context: Dict[str, Any] = Field(default_factory=dict)
    voter_ids: List[str] = Field(default_factory=list)
    deadline_seconds: float = Field(60.0, gt=0)
    required_majority: float = Field(0.5, ge=0.0, le=1.0)
    initiated_by: str = ""
    created_at: float = Field(default_factory=time.time)


class VoteCast(BaseModel):
    """A single vote from an agent."""
    vote_id: str
    voter_id: str
    choice: VoteOption
    reason: str = ""
    timestamp: float = Field(default_factory=time.time)


class VoteResult(BaseModel):
    """Aggregated result of a vote."""
    vote_id: str
    proposal: str
    outcome: VoteOption  # winning option
    approved: bool
    votes: Dict[str, VoteOption] = Field(default_factory=dict)  # voter_id → choice
    approve_count: int = 0
    reject_count: int = 0
    abstain_count: int = 0
    total_eligible: int = 0
    quorum_reached: bool = False


# ============================================================================
# Conflict Resolution
# ============================================================================


class ConflictReport(BaseModel):
    """Report of a conflict between agents."""
    conflict_id: str = Field(default_factory=lambda: f"conf_{uuid.uuid4().hex[:10]}")
    severity: ConflictSeverity = ConflictSeverity.MEDIUM
    agent_ids: List[str] = Field(..., description="Agents involved in conflict")
    description: str
    context: Dict[str, Any] = Field(default_factory=dict)
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Shared Knowledge
# ============================================================================


class KnowledgeEntry(BaseModel):
    """An entry in the shared knowledge base."""
    entry_id: str = Field(default_factory=lambda: f"know_{uuid.uuid4().hex[:10]}")
    key: str = Field(..., description="Knowledge key (e.g. 'project.database_schema')")
    value: Any
    contributed_by: str = Field(..., description="Agent ID that contributed this")
    confidence: float = Field(0.8, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    access_count: int = Field(0, ge=0)


class KnowledgeQuery(BaseModel):
    """Query the shared knowledge base."""
    key_pattern: Optional[str] = None
    tags: Optional[List[str]] = None
    min_confidence: Optional[float] = None
    contributed_by: Optional[str] = None
    limit: int = Field(50, ge=1, le=500)


# ============================================================================
# API Models
# ============================================================================


class CoordinationInfo(BaseModel):
    name: str = "brain.coordination"
    version: str = "1.0.0"
    description: str = "Multi-Agent Coordination System - Sprint 7A"
    features: List[str] = Field(default_factory=lambda: [
        "agent_messaging",
        "task_delegation",
        "voting_consensus",
        "shared_knowledge",
        "conflict_resolution",
        "supervisor_integration",
    ])


class CoordinationStats(BaseModel):
    total_messages: int = 0
    total_tasks_delegated: int = 0
    total_tasks_completed: int = 0
    total_tasks_failed: int = 0
    total_votes: int = 0
    total_conflicts: int = 0
    active_tasks: int = 0
    knowledge_entries: int = 0
    registered_agents: int = 0
