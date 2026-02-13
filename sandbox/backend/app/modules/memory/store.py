"""
Memory Store - Multi-layer persistence for BRAIN's memory system.

Layers:
    Working  → In-memory dict (volatile, per-session)
    Episodic → In-memory with optional Redis persistence
    Semantic → In-memory with optional Qdrant vector search

Future: PostgreSQL for durable episodic, Qdrant for semantic embeddings.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from .schemas import (
    CompressionStatus,
    MemoryEntry,
    MemoryLayer,
    MemoryType,
    MemoryStats,
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
    Multi-layer memory storage.

    Working memory is volatile (lost on restart).
    Episodic and semantic memories are persistent (in-memory for now,
    future: PostgreSQL + Qdrant).
    """

    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self.event_stream = event_stream

        # Storage by layer
        self._memories: Dict[str, MemoryEntry] = {}  # memory_id → entry
        self._sessions: Dict[str, SessionContext] = {}  # session_id → context

        # Indexes for fast lookup
        self._by_agent: Dict[str, List[str]] = {}      # agent_id → [memory_id]
        self._by_session: Dict[str, List[str]] = {}     # session_id → [memory_id]
        self._by_mission: Dict[str, List[str]] = {}     # mission_id → [memory_id]
        self._by_layer: Dict[MemoryLayer, List[str]] = {
            MemoryLayer.WORKING: [],
            MemoryLayer.EPISODIC: [],
            MemoryLayer.SEMANTIC: [],
        }

        # Metrics
        self._total_stores = 0
        self._total_recalls = 0
        self._total_compressions = 0

        logger.info("💾 MemoryStore initialized")

    # ------------------------------------------------------------------
    # Store
    # ------------------------------------------------------------------

    async def store(self, entry: MemoryEntry) -> MemoryEntry:
        """Store a memory entry in the appropriate layer."""
        self._memories[entry.memory_id] = entry
        self._by_layer[entry.layer].append(entry.memory_id)

        if entry.agent_id:
            self._by_agent.setdefault(entry.agent_id, []).append(entry.memory_id)
        if entry.session_id:
            self._by_session.setdefault(entry.session_id, []).append(entry.memory_id)
        if entry.mission_id:
            self._by_mission.setdefault(entry.mission_id, []).append(entry.memory_id)

        self._total_stores += 1

        await self._emit("memory.stored", memory_id=entry.memory_id, layer=entry.layer.value)

        return entry

    async def get(self, memory_id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory by ID. Updates access stats."""
        entry = self._memories.get(memory_id)
        if entry:
            entry.access_count += 1
            entry.last_accessed_at = datetime.utcnow()
            self._total_recalls += 1
        return entry

    async def delete(self, memory_id: str) -> bool:
        entry = self._memories.pop(memory_id, None)
        if not entry:
            return False

        # Clean indexes
        self._by_layer[entry.layer] = [
            m for m in self._by_layer[entry.layer] if m != memory_id
        ]
        if entry.agent_id and entry.agent_id in self._by_agent:
            self._by_agent[entry.agent_id] = [
                m for m in self._by_agent[entry.agent_id] if m != memory_id
            ]
        if entry.session_id and entry.session_id in self._by_session:
            self._by_session[entry.session_id] = [
                m for m in self._by_session[entry.session_id] if m != memory_id
            ]
        if entry.mission_id and entry.mission_id in self._by_mission:
            self._by_mission[entry.mission_id] = [
                m for m in self._by_mission[entry.mission_id] if m != memory_id
            ]

        await self._emit("memory.deleted", memory_id=memory_id)
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    async def query(
        self,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        layer: Optional[MemoryLayer] = None,
        memory_type: Optional[MemoryType] = None,
        tags: Optional[List[str]] = None,
        min_importance: Optional[float] = None,
        min_karma: Optional[float] = None,
        include_compressed: bool = True,
        limit: int = 50,
    ) -> List[MemoryEntry]:
        """
        Query memories with filters. Returns sorted by importance (desc).
        """
        # Start with candidate set
        if session_id and session_id in self._by_session:
            candidates = [self._memories[m] for m in self._by_session[session_id] if m in self._memories]
        elif agent_id and agent_id in self._by_agent:
            candidates = [self._memories[m] for m in self._by_agent[agent_id] if m in self._memories]
        elif mission_id and mission_id in self._by_mission:
            candidates = [self._memories[m] for m in self._by_mission[mission_id] if m in self._memories]
        elif layer:
            candidates = [self._memories[m] for m in self._by_layer[layer] if m in self._memories]
        else:
            candidates = list(self._memories.values())

        # Apply filters
        results = candidates

        if layer:
            results = [m for m in results if m.layer == layer]
        if memory_type:
            results = [m for m in results if m.memory_type == memory_type]
        if agent_id:
            results = [m for m in results if m.agent_id == agent_id]
        if tags:
            tag_set = set(tags)
            results = [m for m in results if tag_set & set(m.tags)]
        if min_importance is not None:
            results = [m for m in results if m.importance >= min_importance]
        if min_karma is not None:
            results = [m for m in results if m.karma_score >= min_karma]
        if not include_compressed:
            results = [m for m in results if m.compression == CompressionStatus.RAW]

        # Sort by importance descending, then recency
        results.sort(key=lambda m: (m.importance, m.created_at.timestamp()), reverse=True)

        return results[:limit]

    async def keyword_search(self, query: str, limit: int = 10, **filters) -> List[MemoryEntry]:
        """Simple keyword search across memory content."""
        q = query.lower()
        candidates = await self.query(limit=1000, **filters)
        matches = []

        for mem in candidates:
            text = f"{mem.content} {mem.summary or ''}".lower()
            if q in text:
                matches.append(mem)
                if len(matches) >= limit:
                    break

        self._total_recalls += len(matches)
        return matches

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def create_session(self, session: SessionContext) -> SessionContext:
        self._sessions[session.session_id] = session
        logger.info("📝 Session created: %s (agent=%s)", session.session_id, session.agent_id)
        await self._emit("memory.session_created", session_id=session.session_id, agent_id=session.agent_id)
        return session

    async def get_session(self, session_id: str) -> Optional[SessionContext]:
        return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        if session_id not in self._sessions:
            return False
        del self._sessions[session_id]
        return True

    async def list_sessions(self, agent_id: Optional[str] = None) -> List[SessionContext]:
        sessions = list(self._sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        return sessions

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    async def get_memories_by_layer(self, layer: MemoryLayer) -> List[MemoryEntry]:
        ids = self._by_layer.get(layer, [])
        return [self._memories[m] for m in ids if m in self._memories]

    async def evict_expired(self) -> int:
        """Remove expired memories. Returns count of evicted entries."""
        now = datetime.utcnow()
        to_delete = [
            m_id for m_id, m in self._memories.items()
            if m.expires_at and m.expires_at <= now
        ]
        for m_id in to_delete:
            await self.delete(m_id)
        if to_delete:
            logger.info("🗑️ Evicted %d expired memories", len(to_delete))
        return len(to_delete)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def get_stats(self) -> MemoryStats:
        memories = list(self._memories.values())
        importances = [m.importance for m in memories] if memories else [0.0]
        karmas = [m.karma_score for m in memories] if memories else [0.0]

        return MemoryStats(
            total_memories=len(memories),
            working_memories=len(self._by_layer[MemoryLayer.WORKING]),
            episodic_memories=len(self._by_layer[MemoryLayer.EPISODIC]),
            semantic_memories=len(self._by_layer[MemoryLayer.SEMANTIC]),
            active_sessions=len(self._sessions),
            total_compressions=self._total_compressions,
            avg_importance=sum(importances) / len(importances),
            avg_karma=sum(karmas) / len(karmas),
        )

    # ------------------------------------------------------------------
    # EventStream
    # ------------------------------------------------------------------

    async def _emit(self, event_type: str, **payload) -> None:
        if self.event_stream is None or Event is None:
            return
        try:
            payload["timestamp"] = time.time()
            event = Event(type=event_type, source="memory_store", target=None, payload=payload)
            await self.event_stream.publish(event)
        except Exception as e:
            logger.error("[MemoryStore] Event publish failed: %s", e)
