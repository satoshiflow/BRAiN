"""
Coordination Service - Unified orchestration for multi-agent coordination.

Combines MessageBus, TaskDelegation, SharedKnowledgeBase,
and ConflictResolver into a single service entry point.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger

from .conflict_resolver import ConflictResolver
from .delegation import TaskDelegation
from .message_bus import MessageBus
from .schemas import (
    AgentMessage,
    ConflictReport,
    ConflictSeverity,
    CoordinationStats,
    CoordinationTask,
    KnowledgeEntry,
    KnowledgeQuery,
    TaskDelegationRequest,
    TaskDelegationResult,
    TaskStatus,
    VoteRequest,
    VoteResult,
)
from .shared_knowledge import SharedKnowledgeBase

MODULE_VERSION = "1.0.0"


class CoordinationService:
    """Unified service for BRAIN's Multi-Agent Coordination."""

    def __init__(self) -> None:
        self.message_bus = MessageBus()
        self.delegation = TaskDelegation(self.message_bus)
        self.knowledge = SharedKnowledgeBase()
        self.conflicts = ConflictResolver()

        logger.info("🤝 CoordinationService initialized (v%s)", MODULE_VERSION)

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        max_tasks: int = 3,
        karma_score: float = 50.0,
    ) -> None:
        self.delegation.register_agent(agent_id, capabilities, max_tasks, karma_score)

    def unregister_agent(self, agent_id: str) -> None:
        self.delegation.unregister_agent(agent_id)

    def update_karma(self, agent_id: str, score: float) -> None:
        self.delegation.update_karma(agent_id, score)

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    async def send_message(self, message: AgentMessage) -> Optional[Dict]:
        return await self.message_bus.send(message)

    async def get_messages(self, agent_id: str, limit: int = 50) -> List[AgentMessage]:
        return await self.message_bus.get_inbox(agent_id, limit)

    # ------------------------------------------------------------------
    # Task delegation
    # ------------------------------------------------------------------

    async def delegate_task(self, request: TaskDelegationRequest) -> TaskDelegationResult:
        return await self.delegation.delegate(request)

    async def report_progress(self, task_id: str, agent_id: str) -> bool:
        return await self.delegation.report_progress(task_id, agent_id)

    async def report_completion(self, task_id: str, agent_id: str, result: Dict) -> bool:
        return await self.delegation.report_completion(task_id, agent_id, result)

    async def report_failure(self, task_id: str, agent_id: str, error: str) -> bool:
        return await self.delegation.report_failure(task_id, agent_id, error)

    async def get_task(self, task_id: str) -> Optional[CoordinationTask]:
        return await self.delegation.get_task(task_id)

    async def list_tasks(self, status: Optional[TaskStatus] = None) -> List[CoordinationTask]:
        return await self.delegation.list_tasks(status)

    # ------------------------------------------------------------------
    # Voting
    # ------------------------------------------------------------------

    async def initiate_vote(self, request: VoteRequest) -> VoteResult:
        return await self.delegation.initiate_vote(request)

    # ------------------------------------------------------------------
    # Shared knowledge
    # ------------------------------------------------------------------

    def contribute_knowledge(self, entry: KnowledgeEntry) -> KnowledgeEntry:
        return self.knowledge.contribute(entry)

    def query_knowledge(self, query: KnowledgeQuery) -> List[KnowledgeEntry]:
        return self.knowledge.query(query)

    def get_knowledge(self, key: str) -> Optional[KnowledgeEntry]:
        return self.knowledge.get_by_key(key)

    # ------------------------------------------------------------------
    # Conflict resolution
    # ------------------------------------------------------------------

    def report_conflict(self, conflict: ConflictReport) -> ConflictReport:
        return self.conflicts.report_conflict(conflict)

    async def resolve_conflict(
        self,
        conflict_id: str,
        agent_karma_scores: Optional[Dict[str, float]] = None,
    ) -> ConflictReport:
        return await self.conflicts.resolve(conflict_id, agent_karma_scores)

    def list_conflicts(
        self,
        resolved: Optional[bool] = None,
        severity: Optional[ConflictSeverity] = None,
    ) -> List[ConflictReport]:
        return self.conflicts.list_conflicts(resolved, severity)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> CoordinationStats:
        bus_stats = self.message_bus.stats
        del_stats = self.delegation.stats
        know_stats = self.knowledge.stats
        conf_stats = self.conflicts.stats

        return CoordinationStats(
            total_messages=bus_stats["total_sent"],
            total_tasks_delegated=del_stats["total_delegated"],
            total_tasks_completed=del_stats["total_completed"],
            total_tasks_failed=del_stats["total_failed"],
            active_tasks=del_stats["active_tasks"],
            registered_agents=del_stats["registered_agents"],
            knowledge_entries=know_stats["total_entries"],
            total_conflicts=conf_stats["total_conflicts"],
        )


# ============================================================================
# Singleton
# ============================================================================

_service: Optional[CoordinationService] = None


def get_coordination_service() -> CoordinationService:
    global _service
    if _service is None:
        _service = CoordinationService()
    return _service
