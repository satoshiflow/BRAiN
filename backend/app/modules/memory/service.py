"""
Memory Service - Orchestrates Store, Context, Compressor, Recall.

Unified entry point for all memory operations.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from .compressor import MemoryCompressor
from .context import ContextManager
from .recall import SelectiveRecall
from .schemas import (
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
    SessionContext,
)
from .store import MemoryStore

MODULE_VERSION = "1.0.0"

# EventStream (optional)
try:
    from mission_control_core.core import EventStream
except ImportError:
    EventStream = None


class MemoryService:
    """
    Unified service for BRAIN's Advanced Memory Architecture.
    """

    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self.store = MemoryStore(event_stream=event_stream)
        self.context = ContextManager(self.store)
        self.compressor = MemoryCompressor(self.store)
        self.recall = SelectiveRecall(self.store)

        logger.info("🧠 MemoryService initialized (v%s)", MODULE_VERSION)

    # ------------------------------------------------------------------
    # Memory storage
    # ------------------------------------------------------------------

    async def store_memory(self, request: MemoryStoreRequest) -> MemoryEntry:
        """Store a memory entry."""
        entry = MemoryEntry(
            layer=request.layer,
            memory_type=request.memory_type,
            content=request.content,
            agent_id=request.agent_id,
            session_id=request.session_id,
            mission_id=request.mission_id,
            importance=request.importance,
            tags=request.tags,
            metadata=request.metadata,
        )
        return await self.store.store(entry)

    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        return await self.store.get(memory_id)

    async def delete_memory(self, memory_id: str) -> bool:
        return await self.store.delete(memory_id)

    async def recall_memories(self, query: MemoryQuery) -> MemoryRecallResult:
        """Execute KARMA-scored selective recall."""
        return await self.recall.recall(query)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def start_session(
        self,
        agent_id: str,
        max_tokens: int = 8000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionContext:
        return await self.context.start_session(agent_id, max_tokens, metadata)

    async def end_session(self, session_id: str) -> Optional[Dict]:
        return await self.context.end_session(session_id)

    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        return await self.store.get_session(session_id)

    async def list_sessions(self, agent_id: Optional[str] = None) -> List[SessionContext]:
        return await self.store.list_sessions(agent_id)

    async def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConversationTurn]:
        return await self.context.add_turn(session_id, role, content, metadata)

    async def get_context_window(self, session_id: str) -> Optional[Dict]:
        return await self.context.get_context_window(session_id)

    async def set_context_var(self, session_id: str, key: str, value: Any) -> bool:
        return await self.context.set_context_var(session_id, key, value)

    # ------------------------------------------------------------------
    # Cross-session
    # ------------------------------------------------------------------

    async def get_agent_history(
        self,
        agent_id: str,
        limit: int = 20,
        min_importance: float = 30.0,
    ) -> List[MemoryEntry]:
        return await self.context.get_agent_history(agent_id, limit, min_importance)

    async def get_mission_context(self, mission_id: str) -> List[MemoryEntry]:
        return await self.context.get_mission_context(mission_id)

    # ------------------------------------------------------------------
    # Compression & maintenance
    # ------------------------------------------------------------------

    async def compress_old(
        self,
        max_age_hours: float = 24.0,
        target_ratio: float = 0.3,
        agent_id: Optional[str] = None,
    ) -> CompressionResult:
        return await self.compressor.compress_old_memories(
            max_age_hours, target_ratio, agent_id,
        )

    async def merge_memories(
        self,
        agent_id: str,
        memory_type: Optional[MemoryType] = None,
    ) -> int:
        return await self.compressor.merge_related_memories(agent_id, memory_type)

    async def apply_decay(self, agent_id: Optional[str] = None) -> int:
        return await self.recall.apply_decay(agent_id)

    async def evict_expired(self) -> int:
        return await self.store.evict_expired()

    async def run_maintenance(self) -> Dict:
        """Run all maintenance tasks."""
        evicted = await self.evict_expired()
        decayed = await self.apply_decay()
        return {
            "evicted": evicted,
            "decayed": decayed,
        }

    # ------------------------------------------------------------------
    # Stats & info
    # ------------------------------------------------------------------

    async def get_stats(self) -> MemoryStats:
        return await self.store.get_stats()

    async def get_info(self) -> MemorySystemInfo:
        return MemorySystemInfo()


# ============================================================================
# Singleton
# ============================================================================

_service: Optional[MemoryService] = None


def get_memory_service(event_stream: Optional["EventStream"] = None) -> MemoryService:
    global _service
    if _service is None:
        _service = MemoryService(event_stream=event_stream)
    return _service
