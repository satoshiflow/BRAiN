"""
Memory ORM Models - PostgreSQL persistence for BRAIN memory system.

SQLAlchemy ORM models that map to the memory tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class MemoryEntryORM(Base):
    """
    SQLAlchemy ORM model for memory entries.
    
    Maps to the 'memory_entries' table in PostgreSQL.
    """
    __tablename__ = "memory_entries"

    # Primary key using UUID
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identifiers (memory_id is the string representation)
    memory_id = Column(String(32), unique=True, nullable=False, index=True)
    
    # Layer and type
    layer = Column(String(20), nullable=False, index=True)  # working, episodic, semantic
    memory_type = Column(String(30), nullable=False, index=True)  # conversation, decision, etc.
    
    # Content
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # Context
    agent_id = Column(String(100), nullable=True, index=True)
    session_id = Column(String(32), nullable=True, index=True)
    mission_id = Column(String(100), nullable=True, index=True)
    tags = Column(ARRAY(String(50)), nullable=False, default=list)
    
    # Scoring
    importance = Column(Float, nullable=False, default=50.0)
    karma_score = Column(Float, nullable=False, default=50.0)
    access_count = Column(Integer, nullable=False, default=0)
    last_accessed_at = Column(DateTime(timezone=False), nullable=True)
    
    # Lifecycle
    compression = Column(String(20), nullable=False, default="raw")  # raw, summarized, archived
    created_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime(timezone=False), nullable=True)
    
    # Embedding for semantic search (stored as JSONB array)
    embedding = Column(JSONB, nullable=True)
    
    # Flexible metadata
    metadata = Column(JSONB, nullable=False, default=dict)

    # Indexes for common query patterns
    __table_args__ = (
        Index("idx_memory_entries_agent_layer", "agent_id", "layer"),
        Index("idx_memory_entries_agent_type", "agent_id", "memory_type"),
        Index("idx_memory_entries_created_at", "created_at"),
        Index("idx_memory_entries_importance", "importance"),
        Index("idx_memory_entries_karma", "karma_score"),
        Index("idx_memory_entries_session", "session_id"),
        Index("idx_memory_entries_mission", "mission_id"),
        Index("idx_memory_entries_expires", "expires_at"),
        # GIN index for tags array and metadata JSONB
        Index("idx_memory_entries_tags", "tags", postgresql_using="gin"),
        Index("idx_memory_entries_metadata", "metadata", postgresql_using="gin"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM model to dictionary."""
        return {
            "memory_id": self.memory_id,
            "layer": self.layer,
            "memory_type": self.memory_type,
            "content": self.content,
            "summary": self.summary,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "mission_id": self.mission_id,
            "tags": self.tags or [],
            "importance": self.importance,
            "karma_score": self.karma_score,
            "access_count": self.access_count,
            "last_accessed_at": self.last_accessed_at,
            "compression": self.compression,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "embedding": self.embedding,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntryORM":
        """Create ORM model from dictionary."""
        return cls(
            memory_id=data.get("memory_id"),
            layer=data.get("layer"),
            memory_type=data.get("memory_type"),
            content=data.get("content"),
            summary=data.get("summary"),
            agent_id=data.get("agent_id"),
            session_id=data.get("session_id"),
            mission_id=data.get("mission_id"),
            tags=data.get("tags", []),
            importance=data.get("importance", 50.0),
            karma_score=data.get("karma_score", 50.0),
            access_count=data.get("access_count", 0),
            last_accessed_at=data.get("last_accessed_at"),
            compression=data.get("compression", "raw"),
            created_at=data.get("created_at", datetime.utcnow()),
            expires_at=data.get("expires_at"),
            embedding=data.get("embedding"),
            metadata=data.get("metadata", {}),
        )


class ConversationTurnORM(Base):
    """
    SQLAlchemy ORM model for conversation turns.
    
    Maps to the 'conversation_turns' table in PostgreSQL.
    """
    __tablename__ = "conversation_turns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    turn_id = Column(String(32), unique=True, nullable=False, index=True)
    session_id = Column(String(32), ForeignKey("session_contexts.session_id", ondelete="CASCADE"), nullable=False, index=True)
    
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=False)
    metadata = Column(JSONB, nullable=False, default=dict)
    token_count = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_conversation_turns_session", "session_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "turn_id": self.turn_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
            "token_count": self.token_count,
        }


class SessionContextORM(Base):
    """
    SQLAlchemy ORM model for session contexts.
    
    Maps to the 'session_contexts' table in PostgreSQL.
    """
    __tablename__ = "session_contexts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(32), unique=True, nullable=False, index=True)
    agent_id = Column(String(100), nullable=False, index=True)
    
    started_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    last_activity_at = Column(DateTime(timezone=False), nullable=False, default=datetime.utcnow)
    
    total_tokens = Column(Integer, nullable=False, default=0)
    max_tokens = Column(Integer, nullable=False, default=8000)
    
    active_mission_id = Column(String(100), nullable=True)
    context_vars = Column(JSONB, nullable=False, default=dict)
    
    compressed_summary = Column(Text, nullable=True)
    compressed_turn_count = Column(Integer, nullable=False, default=0)

    # Relationship to conversation turns
    turns = relationship("ConversationTurnORM", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_session_contexts_agent", "agent_id"),
        Index("idx_session_contexts_started", "started_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "started_at": self.started_at,
            "last_activity_at": self.last_activity_at,
            "total_tokens": self.total_tokens,
            "max_tokens": self.max_tokens,
            "active_mission_id": self.active_mission_id,
            "context_vars": self.context_vars or {},
            "compressed_summary": self.compressed_summary,
            "compressed_turn_count": self.compressed_turn_count,
        }
