"""
Advanced Memory Architecture - Sprint 6B

BRAIN's multi-layer memory system with cross-session persistence,
context compression, and KARMA-scored selective recall.

Memory Hierarchy:
    Working Memory   → Current mission/session state (persistent via PostgreSQL)
    Episodic Memory  → Conversation turns & mission outcomes (persistent via PostgreSQL)
    Semantic Memory   → Compressed knowledge (persistent via PostgreSQL)

PostgreSQL Persistence:
    All memory layers are now persisted to PostgreSQL, ensuring data
    survives restarts and enabling cross-session history.

Existing Integration:
    - DNA Module:        Agent configuration evolution
    - Knowledge Graph:   Semantic search via Cognee/Qdrant
    - KARMA:             Fitness scoring for memory retention
    - Tool System:       Tool usage patterns
"""

from .schemas import (
    MemoryEntry,
    MemoryLayer,
    MemoryType,
    ConversationTurn,
    SessionContext,
    MemoryQuery,
    MemoryRecallResult,
)

# Export ORM models for database operations
from .models import (
    MemoryEntryORM,
    ConversationTurnORM,
    SessionContextORM,
)

# Export database adapter
from .db_adapter import DatabaseAdapter, get_db_adapter

__all__ = [
    # Pydantic models
    "MemoryEntry",
    "MemoryLayer",
    "MemoryType",
    "ConversationTurn",
    "SessionContext",
    "MemoryQuery",
    "MemoryRecallResult",
    # ORM models
    "MemoryEntryORM",
    "ConversationTurnORM",
    "SessionContextORM",
    # Database adapter
    "DatabaseAdapter",
    "get_db_adapter",
]
