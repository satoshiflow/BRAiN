"""
Memory Module - Pydantic Models

Data models for BRAIN's multi-layer memory system.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class MemoryLayer(str, Enum):
    """Which memory layer stores this entry."""
    WORKING = "working"      # Current session/mission state (volatile)
    EPISODIC = "episodic"    # Conversation turns, outcomes (persistent)
    SEMANTIC = "semantic"    # Compressed knowledge, abstractions (persistent)


class MemoryType(str, Enum):
    """Classification of memory content."""
    CONVERSATION = "conversation"    # Chat turn
    MISSION_OUTCOME = "mission_outcome"  # Mission result
    DECISION = "decision"            # Agent decision + rationale
    OBSERVATION = "observation"      # System event observation
    LEARNED_FACT = "learned_fact"    # Compressed/summarized knowledge
    TOOL_USAGE = "tool_usage"        # Tool execution pattern
    ERROR_PATTERN = "error_pattern"  # Failure pattern


class CompressionStatus(str, Enum):
    """Whether a memory has been compressed."""
    RAW = "raw"              # Original, uncompressed
    SUMMARIZED = "summarized"  # Compressed via summarization
    ARCHIVED = "archived"    # Moved to long-term storage


# ============================================================================
# Core Models
# ============================================================================


class ConversationTurn(BaseModel):
    """A single turn in a conversation."""
    turn_id: str = Field(default_factory=lambda: f"turn_{uuid.uuid4().hex[:10]}")
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    token_count: int = Field(0, ge=0, description="Estimated token count")


class MemoryEntry(BaseModel):
    """A single memory record in BRAIN's memory system."""
    memory_id: str = Field(default_factory=lambda: f"mem_{uuid.uuid4().hex[:12]}")
    layer: MemoryLayer
    memory_type: MemoryType
    content: str = Field(..., description="Primary content of the memory")
    summary: Optional[str] = Field(None, description="Compressed summary (if summarized)")

    # Context
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    mission_id: Optional[str] = None
    tags: List[str] = Field(default_factory=list)

    # Scoring
    importance: float = Field(
        50.0, ge=0.0, le=100.0,
        description="How important this memory is (0=trivial, 100=critical)"
    )
    karma_score: float = Field(
        50.0, ge=0.0, le=100.0,
        description="KARMA-derived quality/relevance score"
    )
    access_count: int = Field(0, ge=0, description="Times recalled")
    last_accessed_at: Optional[datetime] = None

    # Lifecycle
    compression: CompressionStatus = Field(CompressionStatus.RAW)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = Field(
        None, description="When this memory should be evicted (None=never)"
    )

    # Embedding (for semantic search)
    embedding: Optional[List[float]] = Field(
        None, description="Vector embedding for similarity search"
    )

    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionContext(BaseModel):
    """
    Working memory for an active session.

    Holds the conversation history, current mission state,
    and accumulated context for the current interaction.
    """
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:10]}")
    agent_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: datetime = Field(default_factory=datetime.utcnow)

    # Conversation
    turns: List[ConversationTurn] = Field(default_factory=list)
    total_tokens: int = Field(0, ge=0, description="Total tokens in session")
    max_tokens: int = Field(8000, description="Context window budget")

    # State
    active_mission_id: Optional[str] = None
    context_vars: Dict[str, Any] = Field(
        default_factory=dict,
        description="Key-value state accumulated during session"
    )

    # Summary of compressed older turns
    compressed_summary: Optional[str] = Field(
        None,
        description="Summary of turns that were compressed to save tokens"
    )
    compressed_turn_count: int = Field(
        0, description="Number of turns that have been compressed"
    )


# ============================================================================
# Query & Result Models
# ============================================================================


class MemoryQuery(BaseModel):
    """Query for selective recall."""
    query: str = Field(..., description="Natural language query or keyword")
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    mission_id: Optional[str] = None
    layer: Optional[MemoryLayer] = None
    memory_type: Optional[MemoryType] = None
    tags: Optional[List[str]] = None
    min_importance: Optional[float] = None
    min_karma: Optional[float] = None
    limit: int = Field(10, ge=1, le=100)
    include_compressed: bool = Field(True, description="Include summarized memories")


class MemoryRecallResult(BaseModel):
    """Result of a memory recall operation."""
    memories: List[MemoryEntry]
    total_found: int
    query_time_ms: float = 0.0
    recall_strategy: str = Field("keyword", description="Strategy used: keyword, semantic, hybrid")


# ============================================================================
# Compression Models
# ============================================================================


class CompressionRequest(BaseModel):
    """Request to compress memories."""
    session_id: Optional[str] = None
    agent_id: Optional[str] = None
    max_age_hours: float = Field(24.0, description="Compress memories older than N hours")
    target_ratio: float = Field(
        0.3, ge=0.1, le=0.9,
        description="Target compression ratio (0.3 = 30% of original size)"
    )


class CompressionResult(BaseModel):
    """Result of a compression operation."""
    compressed_count: int
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    summaries_created: int


# ============================================================================
# API Models
# ============================================================================


class MemoryStoreRequest(BaseModel):
    """Request to store a memory."""
    content: str
    memory_type: MemoryType
    layer: MemoryLayer = MemoryLayer.EPISODIC
    agent_id: Optional[str] = None
    session_id: Optional[str] = None
    mission_id: Optional[str] = None
    importance: float = Field(50.0, ge=0.0, le=100.0)
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    """Request to create a new session."""
    agent_id: str
    max_tokens: int = Field(8000, ge=1000, le=128000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionAddTurnRequest(BaseModel):
    """Request to add a conversation turn."""
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MemorySystemInfo(BaseModel):
    """Memory system module information."""
    name: str = "brain.memory"
    version: str = "1.0.0"
    description: str = "Advanced Memory Architecture - Sprint 6B"
    layers: List[str] = Field(default_factory=lambda: ["working", "episodic", "semantic"])
    features: List[str] = Field(default_factory=lambda: [
        "session_context",
        "cross_session_persistence",
        "context_compression",
        "selective_recall",
        "karma_scoring",
        "importance_decay",
    ])


class MemoryStats(BaseModel):
    """Memory system statistics."""
    total_memories: int = 0
    working_memories: int = 0
    episodic_memories: int = 0
    semantic_memories: int = 0
    active_sessions: int = 0
    total_compressions: int = 0
    avg_importance: float = 0.0
    avg_karma: float = 0.0
