"""
Task Delegation - Supervisor-mediated task assignment to agents.

Flow:
    1. Delegation request arrives (from Supervisor or mission system)
    2. Find agents with matching capabilities
    3. Score candidates (KARMA + availability + success rate)
    4. Assign to best candidate
    5. Track task lifecycle (assigned → in_progress → completed/failed)
    6. Report result back via MessageBus
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger

from .message_bus import MessageBus
from .schemas import (
    AgentMessage,
    CoordinationTask,
    MessagePriority,
    MessageType,
    TaskDelegationRequest,
    TaskDelegationResult,
    TaskStatus,
    VoteCast,
    VoteOption,
    VoteRequest,
    VoteResult,
)


class AgentCapabilityRecord:
    """Tracks an agent's capabilities and performance for delegation."""

    def __init__(self, agent_id: str, capabilities: List[str]) -> None:
        self.agent_id = agent_id
        self.capabilities = set(capabilities)
        self.karma_score: float = 50.0
        self.current_tasks: int = 0
        self.max_tasks: int = 3
        self.success_count: int = 0
        self.failure_count: int = 0
        self.avg_completion_ms: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    @property
    def available(self) -> bool:
        return self.current_tasks < self.max_tasks

    def score_for_task(self, required_capabilities: List[str]) -> float:
        """
        Score this agent for a task.

        Score = capability_match(40%) + karma(25%) + success_rate(20%) + availability(15%)
        """
        # Capability match
        if required_capabilities:
            req_set = set(required_capabilities)
            match_ratio = len(self.capabilities & req_set) / len(req_set)
        else:
            match_ratio = 1.0

        # Availability (inverse of load)
        load = self.current_tasks / max(self.max_tasks, 1)
        avail = 1.0 - load

        score = (
            match_ratio * 40.0
            + (self.karma_score / 100.0) * 25.0
            + self.success_rate * 20.0
            + avail * 15.0
        )
        return score


class TaskDelegation:
    """
    Manages task delegation to agents with capability-based matching.
    """

    def __init__(self, message_bus: MessageBus) -> None:
        self.message_bus = message_bus

        # Agent registry
        self._agents: Dict[str, AgentCapabilityRecord] = {}

        # Active tasks
        self._tasks: Dict[str, CoordinationTask] = {}

        # Metrics
        self._total_delegated = 0
        self._total_completed = 0
        self._total_failed = 0

        logger.info("📋 TaskDelegation initialized")

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        max_tasks: int = 3,
        karma_score: float = 50.0,
    ) -> None:
        record = AgentCapabilityRecord(agent_id, capabilities)
        record.max_tasks = max_tasks
        record.karma_score = karma_score
        self._agents[agent_id] = record
        self.message_bus.register_agent(agent_id)
        logger.info("Agent registered for delegation: %s (caps=%s)", agent_id, capabilities)

    def unregister_agent(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def update_karma(self, agent_id: str, score: float) -> None:
        if agent_id in self._agents:
            self._agents[agent_id].karma_score = max(0.0, min(100.0, score))

    # ------------------------------------------------------------------
    # Delegation
    # ------------------------------------------------------------------

    async def delegate(self, request: TaskDelegationRequest) -> TaskDelegationResult:
        """
        Delegate a task to the best-suited agent.

        Steps:
        1. Find agents with matching capabilities
        2. Score and rank candidates
        3. Assign to top candidate
        4. Notify via MessageBus
        """
        task = CoordinationTask(
            name=request.task_name,
            description=request.description,
            required_capabilities=request.required_capabilities,
            payload=request.payload,
            priority=request.priority,
            timeout_seconds=request.timeout_seconds,
            mission_id=request.mission_id,
        )

        # Find and score candidates
        candidates = self._find_candidates(
            request.required_capabilities,
            request.preferred_agent_id,
        )

        if not candidates:
            logger.warning("No available agents for task '%s'", request.task_name)
            self._tasks[task.task_id] = task
            return TaskDelegationResult(
                task_id=task.task_id,
                success=False,
                reason="No available agents with required capabilities",
            )

        # Assign to best candidate
        best_id, best_score = candidates[0]
        task.assigned_to = best_id
        task.assigned_at = datetime.utcnow()
        task.status = TaskStatus.ASSIGNED

        self._agents[best_id].current_tasks += 1
        self._tasks[task.task_id] = task
        self._total_delegated += 1

        # Notify agent via MessageBus
        await self.message_bus.send(AgentMessage(
            message_type=MessageType.DELEGATE,
            sender_id="coordination",
            target_id=best_id,
            subject=f"Task: {task.name}",
            payload={
                "task_id": task.task_id,
                "name": task.name,
                "description": task.description,
                "payload": task.payload,
                "timeout_seconds": task.timeout_seconds,
            },
            priority=task.priority,
        ))

        logger.info(
            "📋 Delegated '%s' → %s (score=%.1f)",
            task.name, best_id, best_score,
        )

        return TaskDelegationResult(
            task_id=task.task_id,
            assigned_to=best_id,
            reason=f"Best candidate (score={best_score:.1f})",
            success=True,
            alternatives=[aid for aid, _ in candidates[1:4]],
        )

    def _find_candidates(
        self,
        capabilities: List[str],
        preferred: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """Find and rank agents for a task."""
        scored = []
        for agent_id, record in self._agents.items():
            if not record.available:
                continue
            score = record.score_for_task(capabilities)
            # Bonus for preferred agent
            if preferred and agent_id == preferred:
                score += 10.0
            if score > 0:
                scored.append((agent_id, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    async def report_progress(self, task_id: str, agent_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.assigned_to != agent_id:
            return False
        task.status = TaskStatus.IN_PROGRESS
        return True

    async def report_completion(
        self,
        task_id: str,
        agent_id: str,
        result: Dict,
    ) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.assigned_to != agent_id:
            return False

        task.status = TaskStatus.COMPLETED
        task.result = result
        task.completed_at = datetime.utcnow()
        task.attempts += 1

        if agent_id in self._agents:
            self._agents[agent_id].current_tasks = max(0, self._agents[agent_id].current_tasks - 1)
            self._agents[agent_id].success_count += 1

        self._total_completed += 1
        logger.info("✅ Task '%s' completed by %s", task.name, agent_id)
        return True

    async def report_failure(
        self,
        task_id: str,
        agent_id: str,
        error: str,
    ) -> bool:
        task = self._tasks.get(task_id)
        if not task or task.assigned_to != agent_id:
            return False

        task.attempts += 1
        task.error = error

        if agent_id in self._agents:
            self._agents[agent_id].current_tasks = max(0, self._agents[agent_id].current_tasks - 1)
            self._agents[agent_id].failure_count += 1

        # Retry if possible
        if task.attempts < task.max_retries:
            task.status = TaskStatus.PENDING
            task.assigned_to = None
            logger.info("🔄 Task '%s' retry %d/%d", task.name, task.attempts, task.max_retries)
        else:
            task.status = TaskStatus.FAILED
            self._total_failed += 1
            logger.warning("❌ Task '%s' failed after %d attempts", task.name, task.attempts)

        return True

    async def get_task(self, task_id: str) -> Optional[CoordinationTask]:
        return self._tasks.get(task_id)

    async def list_tasks(self, status: Optional[TaskStatus] = None) -> List[CoordinationTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return tasks

    # ------------------------------------------------------------------
    # Voting / Consensus
    # ------------------------------------------------------------------

    async def initiate_vote(self, request: VoteRequest) -> VoteResult:
        """
        Initiate a vote among registered agents.

        Sends vote requests via MessageBus, collects responses,
        and determines the outcome.
        """
        voter_ids = request.voter_ids or list(self._agents.keys())
        votes: Dict[str, VoteOption] = {}

        # Send vote requests
        for voter_id in voter_ids:
            msg = AgentMessage(
                message_type=MessageType.VOTE_REQUEST,
                sender_id=request.initiated_by or "coordination",
                target_id=voter_id,
                subject=request.proposal,
                payload={
                    "vote_id": request.vote_id,
                    "proposal": request.proposal,
                    "options": [o.value for o in request.options],
                    "context": request.context,
                },
                ttl_seconds=request.deadline_seconds,
                priority=MessagePriority.HIGH,
            )
            response = await self.message_bus.send(msg)

            if response and "choice" in response:
                try:
                    votes[voter_id] = VoteOption(response["choice"])
                except ValueError:
                    votes[voter_id] = VoteOption.ABSTAIN
            else:
                votes[voter_id] = VoteOption.ABSTAIN

        # Count votes
        approve = sum(1 for v in votes.values() if v == VoteOption.APPROVE)
        reject = sum(1 for v in votes.values() if v == VoteOption.REJECT)
        abstain = sum(1 for v in votes.values() if v == VoteOption.ABSTAIN)
        total = len(voter_ids)

        # Determine outcome
        non_abstain = approve + reject
        approved = (approve / non_abstain) >= request.required_majority if non_abstain > 0 else False
        outcome = VoteOption.APPROVE if approved else VoteOption.REJECT

        return VoteResult(
            vote_id=request.vote_id,
            proposal=request.proposal,
            outcome=outcome,
            approved=approved,
            votes=votes,
            approve_count=approve,
            reject_count=reject,
            abstain_count=abstain,
            total_eligible=total,
            quorum_reached=(non_abstain / total) >= 0.5 if total > 0 else False,
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def stats(self) -> Dict:
        active = sum(1 for t in self._tasks.values() if t.status in (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS))
        return {
            "total_delegated": self._total_delegated,
            "total_completed": self._total_completed,
            "total_failed": self._total_failed,
            "active_tasks": active,
            "registered_agents": len(self._agents),
        }
