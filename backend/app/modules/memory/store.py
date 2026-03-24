"""
Memory Store - PostgreSQL persistence for BRAIN's memory system.

Layers:
    Working  → PostgreSQL (session contexts with conversation turns)
    Episodic → PostgreSQL (durable memory entries)
    Semantic → PostgreSQL with vector search support

Uses SQLAlchemy async ORM for all database operations.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from .db_adapter import DatabaseAdapter
from .schemas import (
    CompressionStatus,
    MemoryEntry,
    MemoryLayer,
    MemoryStats,
    MemoryType,
    SessionContext,
)

# EventStream integration
try:
    from mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None


class MemoryStore:
    """
    Multi-layer memory storage with PostgreSQL persistence.

    Working memory: Session contexts stored in PostgreSQL.
    Episodic memory: Memory entries stored in PostgreSQL.
    Semantic memory: Memory entries with embeddings in PostgreSQL.
    
    All data persists across restarts.
    """

    def __init__(self, event_stream: Optional["EventStream"] = None, database_url: Optional[str] = None) -> None:
        self.event_stream = event_stream
        self.database_url = database_url
        self._db: Optional[DatabaseAdapter] = None
        self._live_entries: Dict[str, MemoryEntry] = {}
        self._total_compressions = 0
        
        # Metrics (still tracked in memory for performance)
        self._total_stores = 0
        self._total_recalls = 0

        logger.info("💾 MemoryStore initialized (PostgreSQL persistence)")

    async def _get_db(self) -> DatabaseAdapter:
        """Get or initialize the database adapter."""
        if self._db is None:
            self._db = DatabaseAdapter(self.database_url)
            await self._db.initialize()
        return self._db

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    async def store(self, entry: MemoryEntry) -> MemoryEntry:
        """Store a memory entry in the appropriate layer."""
        db = await self._get_db()
        await db.store_memory(entry)
        self._live_entries[entry.memory_id] = entry
        self._total_stores += 1

        await self._emit("memory.stored", memory_id=entry.memory_id, layer=entry.layer.value)

        return entry

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID. Updates access stats."""
        return await self.get_for_tenant(memory_id, None)

    async def get_for_tenant(self, memory_id: str, tenant_id: Optional[str]) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID with optional tenant boundary."""
        db = await self._get_db()
        entry = await db.get_memory_for_tenant(memory_id, tenant_id)
        if entry:
            live = self._live_entries.get(memory_id)
            if live is not None:
                live.access_count = entry.access_count
                live.last_accessed_at = entry.last_accessed_at
                entry = live
            self._total_recalls += 1
        return entry

    async def delete(self, memory_id: str, tenant_id: Optional[str] = None) -> bool:
        """Delete a memory entry."""
        db = await self._get_db()
        deleted = await db.delete_memory(memory_id, tenant_id=tenant_id)
        
        if deleted:
            self._live_entries.pop(memory_id, None)
            await self._emit("memory.deleted", memory_id=memory_id)
        
        return deleted

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def query(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        skill_run_id: Optional[str] = None,
        layer: Optional[MemoryLayer] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        min_importance: Optional[float] = None,
        min_karma: Optional[float] = None,
        include_compressed: bool = True,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """
        Query memories with filters. Returns sorted by importance (desc).
        """
        db = await self._get_db()
        entries = await db.query_memories(
            agent_id=agent_id,
            session_id=session_id,
            mission_id=mission_id,
            skill_run_id=skill_run_id,
            layer=layer,
            memory_type=memory_type,
            tags=tags,
            tenant_id=tenant_id,
            min_importance=min_importance,
            min_karma=min_karma,
            include_compressed=include_compressed,
            limit=limit,
        )
        result: List[MemoryEntry] = []
        for entry in entries:
            live = self._live_entries.get(entry.memory_id)
            if live is None:
                self._live_entries[entry.memory_id] = entry
                result.append(entry)
                continue
            for field in (
                "summary",
                "importance",
                "karma_score",
                "access_count",
                "last_accessed_at",
                "compression",
                "expires_at",
                "tags",
                "metadata",
                "content",
            ):
                setattr(live, field, getattr(entry, field))
            result.append(live)
        return result

    async def keyword_search(self, query: str, limit: int = 10, **filters) -> List[MemoryEntry]:
        """Simple keyword search across memory content."""
        db = await self._get_db()
        matches = await db.keyword_search(query, limit=limit, **filters)
        normalized: List[MemoryEntry] = []
        for match in matches:
            live = self._live_entries.get(match.memory_id)
            normalized.append(live if live is not None else match)
        self._total_recalls += len(matches)
        return normalized

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def create_session(self, session: SessionContext) -> SessionContext:
        """Create a new session context."""
        db = await self._get_db()
        await db.create_session(session)
        
        logger.info("📝 Session created: %s (agent=%s)", session.session_id, session.agent_id)
        await self._emit("memory.session_created", session_id=session.session_id, agent_id=session.agent_id)
        return session

    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        """Get a session by ID with all its turns."""
        return await self.get_session_for_tenant(session_id, None)

    async def get_session_for_tenant(self, session_id: str, tenant_id: Optional[str]) -> Optional[SessionContext]:
        """Get a session by ID with optional tenant boundary."""
        db = await self._get_db()
        return await db.get_session(session_id, tenant_id=tenant_id)

    async def delete_session(self, session_id: str, tenant_id: Optional[str] = None) -> bool:
        """Delete a session and all its turns."""
        db = await self._get_db()
        return await db.delete_session(session_id, tenant_id=tenant_id)

    async def list_sessions(self, agent_id: Optional[str] = None, tenant_id: Optional[str] = None) -> List[SessionContext]:
        """List all sessions, optionally filtered by agent."""
        db = await self._get_db()
        return await db.list_sessions(agent_id, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    async def get_memories_by_layer(self, layer: MemoryLayer) -> List[MemoryEntry]:
        """Get all memories for a specific layer."""
        return await self.query(layer=layer, limit=10000)

    async def evict_expired(self) -> int:
        """Remove expired memories. Returns count of evicted entries."""
        db = await self._get_db()
        evicted = await db.evict_expired()
        if evicted:
            logger.info("🗑️ Evicted %d expired memories", evicted)
        return evicted

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self) -> MemoryStats:
        """Get memory system statistics."""
        return await self.get_stats_for_tenant(None)

    async def get_stats_for_tenant(self, tenant_id: Optional[str]) -> MemoryStats:
        """Get memory system statistics with optional tenant boundary."""
        db = await self._get_db()
        stats = await db.get_stats_for_tenant(tenant_id)
        
        return MemoryStats(
            total_memories=stats["total_memories"],
            working_memories=stats["working_memories"],
            episodic_memories=stats["episodic_memories"],
            semantic_memories=stats["semantic_memories"],
            active_sessions=stats["active_sessions"],
            total_compressions=self._total_compressions,
            avg_importance=stats["avg_importance"],
            avg_karma=stats["avg_karma"],
        )

    async def evict_stale_sessions(self, ttl_hours: float, tenant_id: Optional[str] = None) -> int:
        """Evict inactive sessions older than TTL."""
        db = await self._get_db()
        return await db.evict_stale_sessions(ttl_hours=ttl_hours, tenant_id=tenant_id)

    # ------------------------------------------------------------------
    # EventStream
    # ------------------------------------------------------------------

    async def _emit(self, event_type: str, **payload) -> None:
        """Emit an event to the event stream."""
        if self.event_stream is None or Event is None:
            return
        try:
            payload["timestamp"] = time.time()
            event = Event(type=event_type, source="memory_store", target=None, payload=payload)
            await self.event_stream.publish(event)
        except Exception as e:
            logger.error("[MemoryStore] Event publish failed: %s", e)
