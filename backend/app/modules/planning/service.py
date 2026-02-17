"""
Planning Service - Unified orchestration for the Advanced Planning Engine.

Combines TaskDecomposer, DependencyGraph, ResourceAllocator,
and FailureRecovery into a single service.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from .dependency_graph import DependencyGraph
from .failure_recovery import FailureRecovery, RecoveryAction
from .resource_allocator import ResourceAllocator
from .schemas import (
    DecompositionRequest,
    DecompositionResult,
    ExecutionPlan,
    NodeStatus,
    PlanNode,
    PlanningStats,
    PlanStatus,
    ResourceType,
)
from .task_decomposer import TaskDecomposer

MODULE_VERSION = "1.0.0"


class PlanningService:
    """Unified service for BRAIN's Advanced Planning Engine."""

    def __init__(self) -> None:
        self.decomposer = TaskDecomposer()
        self.allocator = ResourceAllocator()
        self.recovery = FailureRecovery()

        # Plan storage
        self._plans: Dict[str, ExecutionPlan] = {}
        self._graphs: Dict[str, DependencyGraph] = {}

        logger.info("📋 PlanningService initialized (v%s)", MODULE_VERSION)

    # ------------------------------------------------------------------
    # Plan creation
    # ------------------------------------------------------------------

    def decompose_task(self, request: DecompositionRequest) -> DecompositionResult:
        """Decompose a task and create an execution plan."""
        result = self.decomposer.decompose(request)
        plan = result.plan

        # Store plan and build graph
        self._plans[plan.plan_id] = plan
        self._graphs[plan.plan_id] = DependencyGraph(plan.nodes)

        # Allocate budgets
        self.allocator.allocate_from_plan(plan)

        return result

    def create_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Create a plan from pre-built nodes."""
        plan.total_nodes = len(plan.nodes)
        self._plans[plan.plan_id] = plan
        self._graphs[plan.plan_id] = DependencyGraph(plan.nodes)
        self.allocator.allocate_from_plan(plan)
        return plan

    # ------------------------------------------------------------------
    # Plan queries
    # ------------------------------------------------------------------

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        return self._plans.get(plan_id)

    def list_plans(self, status: Optional[PlanStatus] = None) -> List[ExecutionPlan]:
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        return plans

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_plan(self, plan_id: str) -> List[str]:
        """Validate a plan's dependency graph. Returns errors."""
        graph = self._graphs.get(plan_id)
        if not graph:
            return [f"Plan '{plan_id}' not found"]

        errors = graph.validate()
        if not errors:
            plan = self._plans[plan_id]
            plan.status = PlanStatus.VALIDATED

        return errors

    # ------------------------------------------------------------------
    # Execution control
    # ------------------------------------------------------------------

    def start_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Start executing a plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        if plan.status not in (PlanStatus.DRAFT, PlanStatus.VALIDATED, PlanStatus.READY):
            return None

        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.utcnow()

        # Mark root nodes as READY
        graph = self._graphs.get(plan_id)
        if graph:
            for nid in graph.get_root_nodes():
                node = self._get_node(plan_id, nid)
                if node:
                    node.status = NodeStatus.READY

        return plan

    def get_ready_nodes(self, plan_id: str) -> List[PlanNode]:
        """Get nodes ready for execution (all deps satisfied)."""
        plan = self._plans.get(plan_id)
        graph = self._graphs.get(plan_id)
        if not plan or not graph:
            return []

        completed = {
            n.node_id for n in plan.nodes
            if n.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED)
        }
        ready_ids = graph.get_ready_nodes(completed)

        return [
            n for n in plan.nodes
            if n.node_id in ready_ids
        ]

    def start_node(self, plan_id: str, node_id: str) -> Optional[PlanNode]:
        """Mark a node as running."""
        node = self._get_node(plan_id, node_id)
        if not node:
            return None

        node.status = NodeStatus.RUNNING
        node.started_at = datetime.utcnow()

        # Reserve resources
        self.allocator.reserve_for_node(plan_id, node)
        return node

    def complete_node(
        self,
        plan_id: str,
        node_id: str,
        result: Dict,
        actual_resources: Optional[Dict[ResourceType, float]] = None,
    ) -> Optional[PlanNode]:
        """Mark a node as completed with results."""
        plan = self._plans.get(plan_id)
        node = self._get_node(plan_id, node_id)
        if not plan or not node:
            return None

        node.status = NodeStatus.COMPLETED
        node.result = result
        node.completed_at = datetime.utcnow()
        plan.completed_nodes += 1

        # Consume actual resources
        if actual_resources:
            self.allocator.consume_node_actual(plan_id, node, actual_resources)
        else:
            self.allocator.release_node_reservation(plan_id, node)

        # Check plan completion
        self._check_plan_completion(plan_id)

        return node

    async def fail_node(self, plan_id: str, node_id: str, error: str) -> Optional[RecoveryAction]:
        """Handle node failure with recovery."""
        plan = self._plans.get(plan_id)
        node = self._get_node(plan_id, node_id)
        if not plan or not node:
            return None

        node.error = error
        self.allocator.release_node_reservation(plan_id, node)

        # Attempt recovery
        node_map = {n.node_id: n for n in plan.nodes}
        action = await self.recovery.recover(node, error, node_map)

        node.status = action.next_status
        if action.next_status == NodeStatus.FAILED:
            plan.failed_nodes += 1
            self._check_plan_completion(plan_id)

        return action

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def get_critical_path(self, plan_id: str) -> Optional[Dict]:
        """Get the critical path of a plan."""
        graph = self._graphs.get(plan_id)
        if not graph:
            return None

        path, total_time = graph.critical_path()
        plan = self._plans[plan_id]
        path_nodes = [n for n in plan.nodes if n.node_id in path]

        return {
            "path": [{"node_id": n.node_id, "name": n.name} for n in path_nodes],
            "total_estimated_time_ms": total_time,
            "length": len(path),
        }

    def get_parallel_groups(self, plan_id: str) -> Optional[List[List[str]]]:
        """Get parallel execution groups."""
        graph = self._graphs.get(plan_id)
        if not graph:
            return None
        return graph.get_parallel_groups()

    def get_resource_utilization(self, plan_id: str) -> Dict[str, float]:
        return self.allocator.get_utilization(plan_id)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_node(self, plan_id: str, node_id: str) -> Optional[PlanNode]:
        plan = self._plans.get(plan_id)
        if not plan:
            return None
        for node in plan.nodes:
            if node.node_id == node_id:
                return node
        return None

    def _check_plan_completion(self, plan_id: str) -> None:
        """Check if a plan is fully completed or failed."""
        plan = self._plans.get(plan_id)
        if not plan or plan.status != PlanStatus.EXECUTING:
            return

        terminal = sum(
            1 for n in plan.nodes
            if n.status in (NodeStatus.COMPLETED, NodeStatus.SKIPPED, NodeStatus.FAILED)
        )

        if terminal == plan.total_nodes:
            if plan.failed_nodes > 0 and any(
                n.status == NodeStatus.FAILED and not n.optional for n in plan.nodes
            ):
                plan.status = PlanStatus.FAILED
            else:
                plan.status = PlanStatus.COMPLETED
            plan.completed_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> PlanningStats:
        plans = list(self._plans.values())
        return PlanningStats(
            total_plans=len(plans),
            active_plans=sum(1 for p in plans if p.status == PlanStatus.EXECUTING),
            completed_plans=sum(1 for p in plans if p.status == PlanStatus.COMPLETED),
            failed_plans=sum(1 for p in plans if p.status == PlanStatus.FAILED),
            total_nodes_executed=sum(p.completed_nodes for p in plans),
            total_recoveries=self.recovery.stats["total_recoveries"],
            resource_utilization={},
        )


# ============================================================================
# Singleton
# ============================================================================

_service: Optional[PlanningService] = None


def get_planning_service() -> PlanningService:
    global _service
    if _service is None:
        _service = PlanningService()
    return _service
