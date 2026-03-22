"""
Memory Service - Orchestrates Store, Context, Compressor, Recall.

Unified entry point for all memory operations.
"""

from __future__ import annotations

import os
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
            tenant_id=request.tenant_id,
            layer=request.layer,
            memory_type=request.memory_type,
            content=request.content,
            agent_id=request.agent_id,
            session_id=request.session_id,
            mission_id=request.mission_id,
            skill_run_id=request.skill_run_id,
            importance=request.importance,
            tags=request.tags,
            metadata=getattr(request, "metadata", {}),
        )
        return await self.store.store(entry)

    async def get_memory(self, memory_id: str) -> Optional[MemoryEntry]:
        return await self.store.get(memory_id)

    async def get_memory_for_tenant(self, memory_id: str, tenant_id: Optional[str]) -> Optional[MemoryEntry]:
        return await self.store.get_for_tenant(memory_id, tenant_id)

    async def delete_memory(self, memory_id: str, tenant_id: Optional[str] = None) -> bool:
        return await self.store.delete(memory_id, tenant_id=tenant_id)

    async def recall_memories(self, query: MemoryQuery) -> MemoryRecallResult:
        """Execute KARMA-scored selective recall."""
        return await self.recall.recall(query)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def start_session(
        self,
        agent_id: str,
        tenant_id: Optional[str] = None,
        max_tokens: int = 8000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionContext:
        return await self.context.start_session(agent_id, max_tokens, metadata, tenant_id=tenant_id)

    async def end_session(self, session_id: str, tenant_id: Optional[str] = None) -> Optional[Dict]:
        return await self.context.end_session(session_id, tenant_id=tenant_id)

    async def get_session(self, session_id: str, tenant_id: Optional[str] = None) -> Optional[SessionContext]:
        return await self.store.get_session_for_tenant(session_id, tenant_id)

    async def list_sessions(self, agent_id: Optional[str] = None, tenant_id: Optional[str] = None) -> List[SessionContext]:
        return await self.store.list_sessions(agent_id, tenant_id=tenant_id)

    async def add_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConversationTurn]:
        return await self.context.add_turn(session_id, role, content, metadata, tenant_id=tenant_id)

    async def get_context_window(self, session_id: str, tenant_id: Optional[str] = None) -> Optional[Dict]:
        return await self.context.get_context_window(session_id, tenant_id=tenant_id)

    async def set_context_var(self, session_id: str, key: str, value: Any, tenant_id: Optional[str] = None) -> bool:
        return await self.context.set_context_var(session_id, key, value, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Cross-session
    # ------------------------------------------------------------------

    async def get_agent_history(
        self,
        agent_id: str,
        tenant_id: Optional[str] = None,
        limit: int = 20,
        min_importance: float = 30.0,
    ) -> List[MemoryEntry]:
        return await self.context.get_agent_history(agent_id, limit, min_importance, tenant_id=tenant_id)

    async def get_mission_context(self, mission_id: str, tenant_id: Optional[str] = None) -> List[MemoryEntry]:
        return await self.context.get_mission_context(mission_id, tenant_id=tenant_id)

    async def get_skill_run_context(self, skill_run_id: str, tenant_id: Optional[str] = None) -> List[MemoryEntry]:
        return await self.store.query(skill_run_id=skill_run_id, tenant_id=tenant_id, limit=100)

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
        return await self.run_maintenance_for_tenant(None)

    async def run_maintenance_for_tenant(self, tenant_id: Optional[str]) -> Dict:
        """Run memory maintenance with optional tenant boundary."""
        evicted = await self.evict_expired()
        decayed = await self.apply_decay()
        session_ttl_hours = float(os.getenv("MEMORY_SESSION_TTL_HOURS", "24"))
        stale_sessions = await self.store.evict_stale_sessions(session_ttl_hours, tenant_id=tenant_id)
        return {
            "evicted": evicted,
            "decayed": decayed,
            "stale_sessions": stale_sessions,
            "session_ttl_hours": session_ttl_hours,
        }

    # ------------------------------------------------------------------
    # Stats & info
    # ------------------------------------------------------------------

    async def get_stats(self) -> MemoryStats:
        return await self.store.get_stats()

    async def get_stats_for_tenant(self, tenant_id: Optional[str]) -> MemoryStats:
        return await self.store.get_stats_for_tenant(tenant_id)

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
