"""
Tests for Advanced Memory Architecture - Sprint 6B

Covers: MemoryStore, ContextManager, MemoryCompressor, SelectiveRecall, MemoryService
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timedelta

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.memory.schemas import (
    CompressionRequest,
    CompressionStatus,
    MemoryEntry,
    MemoryLayer,
    MemoryQuery,
    MemoryStoreRequest,
    MemoryType,
    SessionContext,
)
from app.modules.memory.store import MemoryStore
from app.modules.memory.context import ContextManager
from app.modules.memory.compressor import MemoryCompressor
from app.modules.memory.recall import SelectiveRecall
from app.modules.memory.service import MemoryService


# ============================================================================
# MemoryStore Tests
# ============================================================================


class TestMemoryStore:
    @pytest.mark.asyncio
    async def test_store_and_get(self):
        store = MemoryStore()
        entry = MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="Hello, world!",
            agent_id="agent_1",
        )
        stored = await store.store(entry)
        assert stored.memory_id == entry.memory_id

        fetched = await store.get(entry.memory_id)
        assert fetched is not None
        assert fetched.content == "Hello, world!"
        assert fetched.access_count == 1  # get increments access

    @pytest.mark.asyncio
    async def test_delete(self):
        store = MemoryStore()
        entry = MemoryEntry(
            layer=MemoryLayer.WORKING,
            memory_type=MemoryType.OBSERVATION,
            content="test",
        )
        await store.store(entry)
        assert await store.delete(entry.memory_id) is True
        assert await store.get(entry.memory_id) is None
        assert await store.delete("nonexistent") is False

    @pytest.mark.asyncio
    async def test_query_by_agent(self):
        store = MemoryStore()
        for i in range(3):
            await store.store(MemoryEntry(
                layer=MemoryLayer.EPISODIC,
                memory_type=MemoryType.CONVERSATION,
                content=f"msg {i}",
                agent_id="agent_a",
            ))
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="other",
            agent_id="agent_b",
        ))

        results = await store.query(agent_id="agent_a")
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_query_by_layer(self):
        store = MemoryStore()
        await store.store(MemoryEntry(
            layer=MemoryLayer.WORKING,
            memory_type=MemoryType.OBSERVATION,
            content="working",
        ))
        await store.store(MemoryEntry(
            layer=MemoryLayer.SEMANTIC,
            memory_type=MemoryType.LEARNED_FACT,
            content="semantic",
        ))

        working = await store.query(layer=MemoryLayer.WORKING)
        assert len(working) == 1
        assert working[0].content == "working"

    @pytest.mark.asyncio
    async def test_query_by_importance(self):
        store = MemoryStore()
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.DECISION,
            content="important",
            importance=90.0,
        ))
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.OBSERVATION,
            content="trivial",
            importance=10.0,
        ))

        results = await store.query(min_importance=50.0)
        assert len(results) == 1
        assert results[0].content == "important"

    @pytest.mark.asyncio
    async def test_keyword_search(self):
        store = MemoryStore()
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="The mission was completed successfully",
        ))
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="Agent started processing",
        ))

        results = await store.keyword_search("mission")
        assert len(results) == 1
        assert "mission" in results[0].content.lower()

    @pytest.mark.asyncio
    async def test_session_crud(self):
        store = MemoryStore()
        session = SessionContext(agent_id="agent_1")
        await store.create_session(session)

        fetched = await store.get_session(session.session_id)
        assert fetched is not None
        assert fetched.agent_id == "agent_1"

        sessions = await store.list_sessions(agent_id="agent_1")
        assert len(sessions) == 1

        assert await store.delete_session(session.session_id) is True
        assert await store.get_session(session.session_id) is None

    @pytest.mark.asyncio
    async def test_stats(self):
        store = MemoryStore()
        await store.store(MemoryEntry(
            layer=MemoryLayer.WORKING,
            memory_type=MemoryType.OBSERVATION,
            content="test",
        ))
        stats = await store.get_stats()
        assert stats.total_memories == 1
        assert stats.working_memories == 1

    @pytest.mark.asyncio
    async def test_evict_expired(self):
        store = MemoryStore()
        await store.store(MemoryEntry(
            layer=MemoryLayer.WORKING,
            memory_type=MemoryType.OBSERVATION,
            content="expired",
            expires_at=datetime.utcnow() - timedelta(hours=1),
        ))
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="not expired",
        ))

        evicted = await store.evict_expired()
        assert evicted == 1
        stats = await store.get_stats()
        assert stats.total_memories == 1


# ============================================================================
# ContextManager Tests
# ============================================================================


class TestContextManager:
    @pytest.mark.asyncio
    async def test_session_lifecycle(self):
        store = MemoryStore()
        ctx = ContextManager(store)

        session = await ctx.start_session("agent_1", max_tokens=4000)
        assert session.agent_id == "agent_1"

        # Add turns
        turn = await ctx.add_turn(session.session_id, "user", "Hello!")
        assert turn is not None
        assert turn.role == "user"

        turn2 = await ctx.add_turn(session.session_id, "assistant", "Hi there!")
        assert turn2 is not None

        # Get context window
        window = await ctx.get_context_window(session.session_id)
        assert window is not None
        assert len(window["messages"]) == 2
        assert window["active_turns"] == 2

        # End session → promotes to episodic
        result = await ctx.end_session(session.session_id)
        assert result is not None
        assert result["promoted"] >= 1

    @pytest.mark.asyncio
    async def test_auto_compress_on_budget(self):
        store = MemoryStore()
        ctx = ContextManager(store)

        # Small budget to trigger compression
        session = await ctx.start_session("agent_1", max_tokens=200)

        # Add many turns to exceed budget
        for i in range(20):
            await ctx.add_turn(session.session_id, "user", f"Message number {i} " * 10)

        s = await store.get_session(session.session_id)
        assert s is not None
        # Compression should have happened
        assert s.compressed_turn_count > 0 or s.compressed_summary is not None

    @pytest.mark.asyncio
    async def test_context_vars(self):
        store = MemoryStore()
        ctx = ContextManager(store)

        session = await ctx.start_session("agent_1")
        await ctx.set_context_var(session.session_id, "task", "analysis")
        val = await ctx.get_context_var(session.session_id, "task")
        assert val == "analysis"

    @pytest.mark.asyncio
    async def test_cross_session_history(self):
        store = MemoryStore()
        ctx = ContextManager(store)

        # Session 1
        s1 = await ctx.start_session("agent_1")
        await ctx.add_turn(s1.session_id, "user", "First session")
        await ctx.end_session(s1.session_id)

        # Session 2
        s2 = await ctx.start_session("agent_1")

        # Get history from previous sessions
        history = await ctx.get_agent_history("agent_1")
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_replace_existing_session(self):
        store = MemoryStore()
        ctx = ContextManager(store)

        s1 = await ctx.start_session("agent_1")
        await ctx.add_turn(s1.session_id, "user", "Old session")

        # Starting new session auto-ends old one
        s2 = await ctx.start_session("agent_1")
        assert s2.session_id != s1.session_id

        # Old session should be gone
        assert await store.get_session(s1.session_id) is None


# ============================================================================
# MemoryCompressor Tests
# ============================================================================


class TestMemoryCompressor:
    @pytest.mark.asyncio
    async def test_compress_old_memories(self):
        store = MemoryStore()
        compressor = MemoryCompressor(store)

        # Store old memory
        old = MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="This is a long conversation about various topics " * 20,
            created_at=datetime.utcnow() - timedelta(hours=48),
        )
        await store.store(old)

        result = await compressor.compress_old_memories(max_age_hours=24)
        assert result.compressed_count == 1
        assert result.compression_ratio < 1.0

        # Check memory was updated
        mem = await store.get(old.memory_id)
        assert mem.compression == CompressionStatus.SUMMARIZED
        assert mem.summary is not None

    @pytest.mark.asyncio
    async def test_no_compress_recent(self):
        store = MemoryStore()
        compressor = MemoryCompressor(store)

        # Store recent memory
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="Recent content",
        ))

        result = await compressor.compress_old_memories(max_age_hours=24)
        assert result.compressed_count == 0

    @pytest.mark.asyncio
    async def test_merge_related(self):
        store = MemoryStore()
        compressor = MemoryCompressor(store)

        # Store multiple related memories
        for i in range(3):
            await store.store(MemoryEntry(
                layer=MemoryLayer.EPISODIC,
                memory_type=MemoryType.CONVERSATION,
                content=f"Mission log entry {i} for analysis",
                agent_id="agent_1",
                mission_id="mission_1",
                tags=["analysis"],
            ))

        merged = await compressor.merge_related_memories("agent_1")
        assert merged >= 1

        # Check semantic memory was created
        semantic = await store.query(layer=MemoryLayer.SEMANTIC)
        assert len(semantic) >= 1
        assert "merged" in semantic[0].tags


# ============================================================================
# SelectiveRecall Tests
# ============================================================================


class TestSelectiveRecall:
    @pytest.mark.asyncio
    async def test_keyword_recall(self):
        store = MemoryStore()
        recall = SelectiveRecall(store)

        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="The deployment was successful",
            importance=80.0,
        ))
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="Agent started processing",
            importance=40.0,
        ))

        result = await recall.recall(MemoryQuery(query="deployment"))
        assert result.total_found >= 1
        assert result.recall_strategy == "keyword"
        assert result.memories[0].content == "The deployment was successful"

    @pytest.mark.asyncio
    async def test_importance_ranking(self):
        store = MemoryStore()
        recall = SelectiveRecall(store)

        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.DECISION,
            content="Important decision A",
            importance=90.0,
            karma_score=80.0,
        ))
        await store.store(MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.OBSERVATION,
            content="Trivial observation B",
            importance=10.0,
            karma_score=20.0,
        ))

        result = await recall.recall(MemoryQuery(query="decision observation", limit=2))
        # Important memory should rank first
        assert result.memories[0].importance > result.memories[1].importance

    @pytest.mark.asyncio
    async def test_reinforcement(self):
        store = MemoryStore()
        recall = SelectiveRecall(store)

        entry = MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.CONVERSATION,
            content="Recalled memory",
            importance=50.0,
        )
        await store.store(entry)

        original_importance = entry.importance

        await recall.recall(MemoryQuery(query="recalled"))

        # Importance should be boosted after recall
        assert entry.importance > original_importance

    @pytest.mark.asyncio
    async def test_decay(self):
        store = MemoryStore()
        recall = SelectiveRecall(store)

        entry = MemoryEntry(
            layer=MemoryLayer.EPISODIC,
            memory_type=MemoryType.OBSERVATION,
            content="Old memory",
            importance=50.0,
            created_at=datetime.utcnow() - timedelta(days=7),
            agent_id="agent_1",
        )
        await store.store(entry)

        decayed = await recall.apply_decay(agent_id="agent_1")
        assert decayed >= 1
        assert entry.importance < 50.0


# ============================================================================
# MemoryService Integration Tests
# ============================================================================


class TestMemoryService:
    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete memory lifecycle: store → session → recall → compress."""
        svc = MemoryService()

        # 1. Store a memory
        entry = await svc.store_memory(MemoryStoreRequest(
            content="Important decision about architecture",
            memory_type=MemoryType.DECISION,
            agent_id="agent_1",
            importance=80.0,
            tags=["architecture"],
        ))
        assert entry.memory_id.startswith("mem_")

        # 2. Start session
        session = await svc.start_session("agent_1")
        assert session.session_id.startswith("sess_")

        # 3. Add turns
        turn = await svc.add_turn(session.session_id, "user", "What was the architecture decision?")
        assert turn is not None

        # 4. Get context window
        ctx = await svc.get_context_window(session.session_id)
        assert ctx["active_turns"] == 1

        # 5. Recall memories
        result = await svc.recall_memories(MemoryQuery(
            query="architecture",
            agent_id="agent_1",
        ))
        assert result.total_found >= 1

        # 6. End session
        end_result = await svc.end_session(session.session_id)
        assert end_result["promoted"] >= 1

        # 7. Cross-session history
        history = await svc.get_agent_history("agent_1")
        assert len(history) >= 1

    @pytest.mark.asyncio
    async def test_maintenance(self):
        svc = MemoryService()
        result = await svc.run_maintenance()
        assert "evicted" in result
        assert "decayed" in result

    @pytest.mark.asyncio
    async def test_stats(self):
        svc = MemoryService()
        await svc.store_memory(MemoryStoreRequest(
            content="test",
            memory_type=MemoryType.OBSERVATION,
        ))
        stats = await svc.get_stats()
        assert stats.total_memories == 1

    @pytest.mark.asyncio
    async def test_info(self):
        svc = MemoryService()
        info = await svc.get_info()
        assert info.name == "brain.memory"
        assert "selective_recall" in info.features

    @pytest.mark.asyncio
    async def test_mission_context(self):
        svc = MemoryService()
        await svc.store_memory(MemoryStoreRequest(
            content="Mission step 1 completed",
            memory_type=MemoryType.MISSION_OUTCOME,
            mission_id="m_123",
        ))
        await svc.store_memory(MemoryStoreRequest(
            content="Mission step 2 failed",
            memory_type=MemoryType.ERROR_PATTERN,
            mission_id="m_123",
        ))

        context = await svc.get_mission_context("m_123")
        assert len(context) == 2
