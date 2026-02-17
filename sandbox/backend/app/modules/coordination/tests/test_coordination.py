"""
Tests for Multi-Agent Coordination - Sprint 7A.

Covers: MessageBus, TaskDelegation, SharedKnowledgeBase,
ConflictResolver, CoordinationService.
"""

import sys
import os
import asyncio

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.coordination.message_bus import MessageBus
from app.modules.coordination.delegation import TaskDelegation, AgentCapabilityRecord
from app.modules.coordination.shared_knowledge import SharedKnowledgeBase
from app.modules.coordination.conflict_resolver import ConflictResolver
from app.modules.coordination.service import CoordinationService
from app.modules.coordination.schemas import (
    AgentMessage,
    ConflictReport,
    ConflictSeverity,
    CoordinationTask,
    KnowledgeEntry,
    KnowledgeQuery,
    MessagePriority,
    MessageType,
    TaskDelegationRequest,
    TaskStatus,
    VoteOption,
    VoteRequest,
)


# ============================================================================
# MessageBus Tests
# ============================================================================


class TestMessageBus:
    def setup_method(self):
        self.bus = MessageBus()

    def test_register_agent(self):
        self.bus.register_agent("agent_1")
        assert "agent_1" in self.bus.get_registered_agents()

    def test_unregister_agent(self):
        self.bus.register_agent("agent_1")
        self.bus.unregister_agent("agent_1")
        assert "agent_1" not in self.bus.get_registered_agents()

    @pytest.mark.asyncio
    async def test_send_targeted_message(self):
        self.bus.register_agent("sender")
        self.bus.register_agent("receiver")

        msg = AgentMessage(
            message_type=MessageType.NOTIFY,
            sender_id="sender",
            target_id="receiver",
            subject="Hello",
            payload={"text": "hi"},
        )
        await self.bus.send(msg)

        inbox = await self.bus.get_inbox("receiver")
        assert len(inbox) == 1
        assert inbox[0].subject == "Hello"

    @pytest.mark.asyncio
    async def test_broadcast(self):
        self.bus.register_agent("sender")
        self.bus.register_agent("a1")
        self.bus.register_agent("a2")

        msg = AgentMessage(
            message_type=MessageType.BROADCAST,
            sender_id="sender",
            subject="Announcement",
        )
        await self.bus.send(msg)

        inbox_a1 = await self.bus.get_inbox("a1")
        inbox_a2 = await self.bus.get_inbox("a2")
        assert len(inbox_a1) == 1
        assert len(inbox_a2) == 1

    @pytest.mark.asyncio
    async def test_handler_invoked(self):
        self.bus.register_agent("agent_1")
        received = []

        async def handler(msg: AgentMessage):
            received.append(msg)

        self.bus.register_handler("agent_1", MessageType.NOTIFY, handler)

        msg = AgentMessage(
            message_type=MessageType.NOTIFY,
            sender_id="other",
            target_id="agent_1",
            subject="Test",
        )
        await self.bus.send(msg)
        assert len(received) == 1
        assert received[0].subject == "Test"

    def test_stats(self):
        self.bus.register_agent("a1")
        stats = self.bus.stats
        assert stats["registered_agents"] == 1
        assert stats["total_sent"] == 0


# ============================================================================
# AgentCapabilityRecord Tests
# ============================================================================


class TestAgentCapability:
    def test_score_full_match(self):
        record = AgentCapabilityRecord("a1", ["python", "testing"])
        record.karma_score = 80.0
        score = record.score_for_task(["python", "testing"])
        assert score > 60  # High score for full match + good karma

    def test_score_no_match(self):
        record = AgentCapabilityRecord("a1", ["python"])
        score = record.score_for_task(["rust", "go"])
        assert score < 50  # Low score, no capability match

    def test_available(self):
        record = AgentCapabilityRecord("a1", ["python"])
        assert record.available is True
        record.current_tasks = 3
        assert record.available is False

    def test_success_rate(self):
        record = AgentCapabilityRecord("a1", [])
        assert record.success_rate == 0.5  # Default
        record.success_count = 8
        record.failure_count = 2
        assert record.success_rate == 0.8


# ============================================================================
# TaskDelegation Tests
# ============================================================================


class TestTaskDelegation:
    def setup_method(self):
        self.bus = MessageBus()
        self.delegation = TaskDelegation(self.bus)

    @pytest.mark.asyncio
    async def test_delegate_no_agents(self):
        req = TaskDelegationRequest(
            task_name="test_task",
            required_capabilities=["python"],
        )
        result = await self.delegation.delegate(req)
        assert result.success is False
        assert "No available agents" in result.reason

    @pytest.mark.asyncio
    async def test_delegate_success(self):
        self.delegation.register_agent("agent_1", ["python", "testing"])

        req = TaskDelegationRequest(
            task_name="run_tests",
            required_capabilities=["python"],
        )
        result = await self.delegation.delegate(req)
        assert result.success is True
        assert result.assigned_to == "agent_1"

    @pytest.mark.asyncio
    async def test_delegate_preferred_agent(self):
        self.delegation.register_agent("a1", ["python"])
        self.delegation.register_agent("a2", ["python"])

        req = TaskDelegationRequest(
            task_name="task",
            required_capabilities=["python"],
            preferred_agent_id="a2",
        )
        result = await self.delegation.delegate(req)
        assert result.assigned_to == "a2"  # Preferred gets bonus

    @pytest.mark.asyncio
    async def test_task_lifecycle(self):
        self.delegation.register_agent("a1", ["python"])

        req = TaskDelegationRequest(task_name="task")
        result = await self.delegation.delegate(req)
        task_id = result.task_id

        # Progress
        ok = await self.delegation.report_progress(task_id, "a1")
        assert ok is True

        # Completion
        ok = await self.delegation.report_completion(task_id, "a1", {"output": "done"})
        assert ok is True

        task = await self.delegation.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_task_failure_and_retry(self):
        self.delegation.register_agent("a1", ["python"])

        req = TaskDelegationRequest(task_name="flaky_task")
        result = await self.delegation.delegate(req)
        task_id = result.task_id

        # First failure → retry (default max_retries=1, so this should set to FAILED)
        ok = await self.delegation.report_failure(task_id, "a1", "timeout")
        assert ok is True

        task = await self.delegation.get_task(task_id)
        assert task.status == TaskStatus.FAILED


# ============================================================================
# SharedKnowledgeBase Tests
# ============================================================================


class TestSharedKnowledge:
    def setup_method(self):
        self.kb = SharedKnowledgeBase()

    def test_contribute_and_get(self):
        entry = KnowledgeEntry(
            key="project.database",
            value="PostgreSQL 15",
            contributed_by="architect",
            confidence=0.9,
            tags=["infrastructure"],
        )
        self.kb.contribute(entry)

        result = self.kb.get_by_key("project.database")
        assert result is not None
        assert result.value == "PostgreSQL 15"

    def test_update_existing(self):
        e1 = KnowledgeEntry(key="config.port", value=8000, contributed_by="ops", confidence=0.7)
        self.kb.contribute(e1)

        e2 = KnowledgeEntry(key="config.port", value=8080, contributed_by="ops", confidence=0.9)
        self.kb.contribute(e2)

        result = self.kb.get_by_key("config.port")
        assert result.value == 8080
        assert result.confidence == 0.9

    def test_query_by_tags(self):
        self.kb.contribute(KnowledgeEntry(
            key="db.host", value="localhost", contributed_by="ops", tags=["infra"],
        ))
        self.kb.contribute(KnowledgeEntry(
            key="app.name", value="BRAiN", contributed_by="dev", tags=["app"],
        ))

        results = self.kb.query(KnowledgeQuery(tags=["infra"]))
        assert len(results) == 1
        assert results[0].key == "db.host"

    def test_query_by_pattern(self):
        self.kb.contribute(KnowledgeEntry(key="db.host", value="x", contributed_by="a"))
        self.kb.contribute(KnowledgeEntry(key="db.port", value="y", contributed_by="a"))
        self.kb.contribute(KnowledgeEntry(key="app.name", value="z", contributed_by="a"))

        results = self.kb.query(KnowledgeQuery(key_pattern="db.*"))
        assert len(results) == 2

    def test_remove(self):
        entry = KnowledgeEntry(key="tmp", value="x", contributed_by="a")
        self.kb.contribute(entry)
        assert self.kb.remove(entry.entry_id) is True
        assert self.kb.get_by_key("tmp") is None

    def test_stats(self):
        self.kb.contribute(KnowledgeEntry(key="k1", value="v1", contributed_by="a1"))
        stats = self.kb.stats
        assert stats["total_entries"] == 1
        assert stats["unique_contributors"] == 1


# ============================================================================
# ConflictResolver Tests
# ============================================================================


class TestConflictResolver:
    def setup_method(self):
        self.resolver = ConflictResolver()

    def test_report_conflict(self):
        conflict = ConflictReport(
            agent_ids=["a1", "a2"],
            description="Resource contention on GPU",
            severity=ConflictSeverity.MEDIUM,
        )
        result = self.resolver.report_conflict(conflict)
        assert result.conflict_id == conflict.conflict_id

    @pytest.mark.asyncio
    async def test_resolve_critical(self):
        conflict = ConflictReport(
            agent_ids=["a1", "a2"],
            description="Safety violation",
            severity=ConflictSeverity.CRITICAL,
        )
        self.resolver.report_conflict(conflict)
        result = await self.resolver.resolve(conflict.conflict_id)
        assert "ESCALATED" in result.resolution
        assert result.resolved_at is not None

    @pytest.mark.asyncio
    async def test_resolve_karma(self):
        conflict = ConflictReport(
            agent_ids=["a1", "a2"],
            description="Task overlap",
            severity=ConflictSeverity.MEDIUM,
        )
        self.resolver.report_conflict(conflict)
        result = await self.resolver.resolve(
            conflict.conflict_id,
            agent_karma_scores={"a1": 80.0, "a2": 60.0},
        )
        assert "a1" in result.resolution  # Higher karma wins

    @pytest.mark.asyncio
    async def test_resolve_low(self):
        conflict = ConflictReport(
            agent_ids=["first", "second"],
            description="Minor preference",
            severity=ConflictSeverity.LOW,
        )
        self.resolver.report_conflict(conflict)
        result = await self.resolver.resolve(conflict.conflict_id)
        assert "first" in result.resolution  # First-come wins

    def test_list_unresolved(self):
        c = ConflictReport(agent_ids=["a1"], description="test", severity=ConflictSeverity.LOW)
        self.resolver.report_conflict(c)
        unresolved = self.resolver.list_conflicts(resolved=False)
        assert len(unresolved) == 1

    def test_stats(self):
        stats = self.resolver.stats
        assert stats["total_conflicts"] == 0
        assert stats["resolved"] == 0


# ============================================================================
# CoordinationService Integration Tests
# ============================================================================


class TestCoordinationService:
    def setup_method(self):
        self.svc = CoordinationService()

    @pytest.mark.asyncio
    async def test_full_delegation_workflow(self):
        self.svc.register_agent("worker", ["coding", "testing"], karma_score=75.0)

        result = await self.svc.delegate_task(TaskDelegationRequest(
            task_name="write_tests",
            required_capabilities=["coding"],
        ))
        assert result.success is True
        assert result.assigned_to == "worker"

        await self.svc.report_progress(result.task_id, "worker")
        await self.svc.report_completion(result.task_id, "worker", {"tests": 5})

        task = await self.svc.get_task(result.task_id)
        assert task.status == TaskStatus.COMPLETED

    def test_knowledge_workflow(self):
        self.svc.contribute_knowledge(KnowledgeEntry(
            key="api.version", value="2.0", contributed_by="architect",
        ))
        entry = self.svc.get_knowledge("api.version")
        assert entry is not None
        assert entry.value == "2.0"

    @pytest.mark.asyncio
    async def test_conflict_workflow(self):
        conflict = self.svc.report_conflict(ConflictReport(
            agent_ids=["a1", "a2"],
            description="GPU contention",
            severity=ConflictSeverity.MEDIUM,
        ))
        resolved = await self.svc.resolve_conflict(conflict.conflict_id)
        assert resolved.resolution is not None

    def test_stats(self):
        stats = self.svc.get_stats()
        assert stats.total_messages == 0
        assert stats.registered_agents == 0
