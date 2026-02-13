"""
Failure Recovery - Detox-integrated recovery strategies.

When a plan node fails, the recovery system:
1. Classifies the failure (transient vs permanent)
2. Selects recovery strategy based on node configuration
3. Executes recovery (retry, rollback, skip, alternative, detox)
4. Updates plan state and metrics

Detox integration:
    BRAIN's Detox system provides "cooling down" periods for
    agents/resources that are overloaded or failing repeatedly.
    The recovery system triggers Detox cooldowns when appropriate.
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, List, Optional

from loguru import logger

from .schemas import (
    NodeStatus,
    PlanNode,
    RecoveryStrategy,
    RecoveryStrategyType,
)


class RecoveryAction:
    """Result of a recovery attempt."""

    def __init__(
        self,
        node_id: str,
        strategy: RecoveryStrategyType,
        success: bool,
        message: str,
        next_status: NodeStatus,
        retry_after_ms: int = 0,
    ):
        self.node_id = node_id
        self.strategy = strategy
        self.success = success
        self.message = message
        self.next_status = next_status
        self.retry_after_ms = retry_after_ms
        self.timestamp = datetime.utcnow()


class FailureRecovery:
    """
    Manages failure recovery for plan nodes.

    Each recovery strategy has specific behavior:
    - RETRY: Re-execute with exponential backoff
    - ROLLBACK: Undo completed nodes in reverse order
    - SKIP: Mark node as skipped (only if optional)
    - ALTERNATIVE: Switch to an alternative node
    - DETOX: Trigger cooldown period before retry
    - ESCALATE: Escalate to supervisor
    """

    def __init__(self) -> None:
        # Detox cooldown tracker: agent_id → cooldown_until timestamp
        self._detox_cooldowns: Dict[str, float] = {}
        self._total_recoveries = 0
        self._successful_recoveries = 0

        logger.info("🔧 FailureRecovery initialized")

    # ------------------------------------------------------------------
    # Recovery execution
    # ------------------------------------------------------------------

    async def recover(
        self,
        node: PlanNode,
        error: str,
        plan_nodes: Optional[Dict[str, PlanNode]] = None,
    ) -> RecoveryAction:
        """
        Execute recovery for a failed node.

        Returns a RecoveryAction describing what happened and
        what state the node should transition to.
        """
        self._total_recoveries += 1
        strategy = node.recovery_strategy

        if strategy == RecoveryStrategyType.RETRY:
            return await self._recover_retry(node, error)
        elif strategy == RecoveryStrategyType.ROLLBACK:
            return await self._recover_rollback(node, error, plan_nodes or {})
        elif strategy == RecoveryStrategyType.SKIP:
            return await self._recover_skip(node, error)
        elif strategy == RecoveryStrategyType.ALTERNATIVE:
            return await self._recover_alternative(node, error, plan_nodes or {})
        elif strategy == RecoveryStrategyType.DETOX:
            return await self._recover_detox(node, error)
        elif strategy == RecoveryStrategyType.ESCALATE:
            return await self._recover_escalate(node, error)
        else:
            return RecoveryAction(
                node_id=node.node_id,
                strategy=strategy,
                success=False,
                message=f"Unknown recovery strategy: {strategy}",
                next_status=NodeStatus.FAILED,
            )

    # ------------------------------------------------------------------
    # Strategy implementations
    # ------------------------------------------------------------------

    async def _recover_retry(self, node: PlanNode, error: str) -> RecoveryAction:
        """Retry with exponential backoff."""
        if node.retry_count >= node.max_retries:
            return RecoveryAction(
                node_id=node.node_id,
                strategy=RecoveryStrategyType.RETRY,
                success=False,
                message=f"Max retries ({node.max_retries}) exhausted: {error}",
                next_status=NodeStatus.FAILED,
            )

        node.retry_count += 1
        backoff_ms = int(min(1000 * (2 ** (node.retry_count - 1)), 60000))

        self._successful_recoveries += 1
        return RecoveryAction(
            node_id=node.node_id,
            strategy=RecoveryStrategyType.RETRY,
            success=True,
            message=f"Retry {node.retry_count}/{node.max_retries} after {backoff_ms}ms",
            next_status=NodeStatus.PENDING,
            retry_after_ms=backoff_ms,
        )

    async def _recover_rollback(
        self,
        node: PlanNode,
        error: str,
        plan_nodes: Dict[str, PlanNode],
    ) -> RecoveryAction:
        """Rollback: mark upstream completed nodes for re-execution."""
        # Find completed upstream nodes
        upstream_completed = []
        for dep_id in node.depends_on:
            dep_node = plan_nodes.get(dep_id)
            if dep_node and dep_node.status == NodeStatus.COMPLETED:
                upstream_completed.append(dep_id)

        # Reset upstream nodes to PENDING
        for uid in upstream_completed:
            plan_nodes[uid].status = NodeStatus.PENDING
            plan_nodes[uid].result = None

        self._successful_recoveries += 1
        return RecoveryAction(
            node_id=node.node_id,
            strategy=RecoveryStrategyType.ROLLBACK,
            success=True,
            message=f"Rolled back {len(upstream_completed)} upstream nodes",
            next_status=NodeStatus.PENDING,
        )

    async def _recover_skip(self, node: PlanNode, error: str) -> RecoveryAction:
        """Skip: only for optional nodes."""
        if not node.optional:
            return RecoveryAction(
                node_id=node.node_id,
                strategy=RecoveryStrategyType.SKIP,
                success=False,
                message=f"Cannot skip non-optional node: {error}",
                next_status=NodeStatus.FAILED,
            )

        self._successful_recoveries += 1
        return RecoveryAction(
            node_id=node.node_id,
            strategy=RecoveryStrategyType.SKIP,
            success=True,
            message="Node skipped (optional)",
            next_status=NodeStatus.SKIPPED,
        )

    async def _recover_alternative(
        self,
        node: PlanNode,
        error: str,
        plan_nodes: Dict[str, PlanNode],
    ) -> RecoveryAction:
        """Switch to an alternative node if configured."""
        # Look for a node named "{node.name}_alt" as a convention
        alt_id = None
        for nid, n in plan_nodes.items():
            if n.name == f"{node.name}_alt":
                alt_id = nid
                break

        if not alt_id:
            return RecoveryAction(
                node_id=node.node_id,
                strategy=RecoveryStrategyType.ALTERNATIVE,
                success=False,
                message=f"No alternative node found for '{node.name}'",
                next_status=NodeStatus.FAILED,
            )

        # Activate alternative
        alt_node = plan_nodes[alt_id]
        alt_node.status = NodeStatus.READY

        self._successful_recoveries += 1
        return RecoveryAction(
            node_id=node.node_id,
            strategy=RecoveryStrategyType.ALTERNATIVE,
            success=True,
            message=f"Switched to alternative node '{alt_node.name}'",
            next_status=NodeStatus.SKIPPED,
        )

    async def _recover_detox(self, node: PlanNode, error: str) -> RecoveryAction:
        """Trigger Detox cooldown before retry."""
        agent_id = node.agent_id or "system"
        cooldown_ms = 5000  # Default 5s

        # Set cooldown
        self._detox_cooldowns[agent_id] = time.time() + cooldown_ms / 1000.0

        if node.retry_count >= node.max_retries:
            return RecoveryAction(
                node_id=node.node_id,
                strategy=RecoveryStrategyType.DETOX,
                success=False,
                message=f"Detox: max retries exhausted after cooldown",
                next_status=NodeStatus.FAILED,
            )

        node.retry_count += 1
        self._successful_recoveries += 1
        return RecoveryAction(
            node_id=node.node_id,
            strategy=RecoveryStrategyType.DETOX,
            success=True,
            message=f"Detox cooldown {cooldown_ms}ms for agent '{agent_id}', then retry {node.retry_count}/{node.max_retries}",
            next_status=NodeStatus.PENDING,
            retry_after_ms=cooldown_ms,
        )

    async def _recover_escalate(self, node: PlanNode, error: str) -> RecoveryAction:
        """Escalate to supervisor."""
        self._successful_recoveries += 1
        return RecoveryAction(
            node_id=node.node_id,
            strategy=RecoveryStrategyType.ESCALATE,
            success=True,
            message=f"Escalated to supervisor: {error}",
            next_status=NodeStatus.BLOCKED,
        )

    # ------------------------------------------------------------------
    # Detox queries
    # ------------------------------------------------------------------

    def is_in_cooldown(self, agent_id: str) -> bool:
        """Check if an agent is in Detox cooldown."""
        until = self._detox_cooldowns.get(agent_id, 0)
        return time.time() < until

    def get_cooldown_remaining_ms(self, agent_id: str) -> int:
        """Get remaining cooldown in ms."""
        until = self._detox_cooldowns.get(agent_id, 0)
        remaining = until - time.time()
        return max(0, int(remaining * 1000))

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def stats(self) -> Dict:
        return {
            "total_recoveries": self._total_recoveries,
            "successful_recoveries": self._successful_recoveries,
            "recovery_rate": (
                self._successful_recoveries / self._total_recoveries
                if self._total_recoveries > 0
                else 0.0
            ),
            "agents_in_cooldown": sum(1 for a in self._detox_cooldowns if self.is_in_cooldown(a)),
        }
