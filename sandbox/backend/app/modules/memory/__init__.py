"""
Advanced Memory Architecture - Sprint 6B

BRAIN's multi-layer memory system with cross-session persistence,
context compression, and KARMA-scored selective recall.

Memory Hierarchy:
    Working Memory   → Current mission/session state (fast, volatile)
    Episodic Memory  → Conversation turns & mission outcomes (persistent)
    Semantic Memory   → Compressed knowledge (integrates with Knowledge Graph)

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

__all__ = [
    "MemoryEntry",
    "MemoryLayer",
    "MemoryType",
    "ConversationTurn",
    "SessionContext",
    "MemoryQuery",
    "MemoryRecallResult",
]
