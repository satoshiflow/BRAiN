"""
Tests for Advanced Planning Engine - Sprint 8.

Covers: TaskDecomposer, DependencyGraph, ResourceAllocator,
FailureRecovery, PlanningService.
"""

import sys
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.planning.task_decomposer import TaskDecomposer
from app.modules.planning.dependency_graph import DependencyGraph
from app.modules.planning.resource_allocator import ResourceAllocator
from app.modules.planning.failure_recovery import FailureRecovery
from app.modules.planning.service import PlanningService
from app.modules.planning.schemas import (
    DecompositionRequest,
    ExecutionPlan,
    NodeStatus,
    NodeType,
    PlanNode,
    PlanStatus,
    RecoveryStrategyType,
    ResourceBudget,
    ResourceType,
)


# ============================================================================
# TaskDecomposer Tests
# ============================================================================


class TestTaskDecomposer:
    def setup_method(self):
        self.decomposer = TaskDecomposer()

    def test_template_decomposition(self):
        req = DecompositionRequest(
            task_name="llm_task",
            task_description="Process with LLM",
            agent_id="a1",
        )
        result = self.decomposer.decompose(req)
        assert len(result.plan.nodes) >= 3
        assert result.plan.status == PlanStatus.DRAFT

    def test_generic_decomposition(self):
        req = DecompositionRequest(
            task_name="unknown_task",
            task_description="Something new",
            agent_id="a1",
        )
        result = self.decomposer.decompose(req)
        assert len(result.plan.nodes) >= 3  # prepare + execute + finalize + checkpoints

    def test_checkpoint_insertion(self):
        # Register a template with enough action nodes to trigger checkpoint
        self.decomposer.register_template("checkpoint_test", [
            {"name": "s1", "action": "compute", "type": "action"},
            {"name": "s2", "action": "compute", "type": "action", "depends": ["s1"]},
            {"name": "s3", "action": "compute", "type": "action", "depends": ["s2"]},
            {"name": "s4", "action": "compute", "type": "action", "depends": ["s3"]},
        ])
        req = DecompositionRequest(
            task_name="checkpoint_test",
            task_description="Test checkpoints",
            agent_id="a1",
        )
        result = self.decomposer.decompose(req)
        checkpoint_nodes = [n for n in result.plan.nodes if n.node_type == NodeType.CHECKPOINT]
        assert len(checkpoint_nodes) >= 1

    def test_resource_estimation(self):
        req = DecompositionRequest(
            task_name="llm_task",
            task_description="LLM processing",
            agent_id="a1",
        )
        result = self.decomposer.decompose(req)
        assert result.total_estimated_tokens > 0
        assert result.total_estimated_time_ms > 0

    def test_critical_path(self):
        req = DecompositionRequest(
            task_name="data_pipeline",
            task_description="Data pipeline task",
            agent_id="a1",
        )
        result = self.decomposer.decompose(req)
        assert result.critical_path_length >= 1
        assert result.parallelism_factor >= 1.0

    def test_max_nodes_cap(self):
        req = DecompositionRequest(
            task_name="llm_task",
            task_description="Test",
            max_nodes=2,
        )
        result = self.decomposer.decompose(req)
        assert len(result.plan.nodes) <= 3  # 2 + possible checkpoint

    def test_custom_template(self):
        self.decomposer.register_template("custom_flow", [
            {"name": "step1", "action": "compute", "type": "action"},
            {"name": "step2", "action": "compute", "type": "action", "depends": ["step1"]},
        ])
        req = DecompositionRequest(
            task_name="custom_flow",
            task_description="Custom",
        )
        result = self.decomposer.decompose(req)
        names = [n.name for n in result.plan.nodes if n.node_type == NodeType.ACTION]
        assert "step1" in names
        assert "step2" in names


# ============================================================================
# DependencyGraph Tests
# ============================================================================


class TestDependencyGraph:
    def _make_chain(self) -> list:
        n1 = PlanNode(node_id="n1", name="first")
        n2 = PlanNode(node_id="n2", name="second", depends_on=["n1"])
        n3 = PlanNode(node_id="n3", name="third", depends_on=["n2"])
        return [n1, n2, n3]

    def _make_diamond(self) -> list:
        n1 = PlanNode(node_id="n1", name="start")
        n2 = PlanNode(node_id="n2", name="left", depends_on=["n1"])
        n3 = PlanNode(node_id="n3", name="right", depends_on=["n1"])
        n4 = PlanNode(node_id="n4", name="end", depends_on=["n2", "n3"])
        return [n1, n2, n3, n4]

    def test_topological_sort_chain(self):
        graph = DependencyGraph(self._make_chain())
        order = graph.topological_sort()
        assert order == ["n1", "n2", "n3"]

    def test_topological_sort_diamond(self):
        graph = DependencyGraph(self._make_diamond())
        order = graph.topological_sort()
        assert order.index("n1") < order.index("n2")
        assert order.index("n1") < order.index("n3")
        assert order.index("n2") < order.index("n4")
        assert order.index("n3") < order.index("n4")

    def test_no_cycle(self):
        graph = DependencyGraph(self._make_chain())
        assert graph.has_cycle() is False

    def test_validate_clean(self):
        graph = DependencyGraph(self._make_chain())
        errors = graph.validate()
        assert len(errors) == 0

    def test_root_nodes(self):
        graph = DependencyGraph(self._make_diamond())
        roots = graph.get_root_nodes()
        assert roots == ["n1"]

    def test_leaf_nodes(self):
        graph = DependencyGraph(self._make_diamond())
        leaves = graph.get_leaf_nodes()
        assert leaves == ["n4"]

    def test_ready_nodes(self):
        nodes = self._make_diamond()
        graph = DependencyGraph(nodes)

        # Initially only n1 is ready
        ready = graph.get_ready_nodes(completed=set())
        assert "n1" in ready

        # After n1 completes, n2 and n3 are ready
        nodes[0].status = NodeStatus.COMPLETED
        ready = graph.get_ready_nodes(completed={"n1"})
        assert set(ready) == {"n2", "n3"}

    def test_parallel_groups(self):
        graph = DependencyGraph(self._make_diamond())
        groups = graph.get_parallel_groups()
        assert len(groups) == 3  # [n1], [n2, n3], [n4]
        assert len(groups[1]) == 2  # n2, n3 in parallel

    def test_critical_path(self):
        nodes = self._make_chain()
        for n in nodes:
            n.estimated_time_ms = 100
        graph = DependencyGraph(nodes)
        path, total = graph.critical_path()
        assert len(path) == 3
        assert total == 300

    def test_downstream(self):
        graph = DependencyGraph(self._make_diamond())
        downstream = graph.get_downstream("n1")
        assert downstream == {"n2", "n3", "n4"}

    def test_upstream(self):
        graph = DependencyGraph(self._make_diamond())
        upstream = graph.get_upstream("n4")
        assert upstream == {"n1", "n2", "n3"}


# ============================================================================
# ResourceAllocator Tests
# ============================================================================


class TestResourceAllocator:
    def setup_method(self):
        self.allocator = ResourceAllocator()

    def test_allocate_and_consume(self):
        budget = ResourceBudget(resource_type=ResourceType.LLM_TOKENS, allocated=1000)
        self.allocator.allocate_budget("plan1", budget)

        assert self.allocator.can_afford("plan1", ResourceType.LLM_TOKENS, 500) is True
        assert self.allocator.consume("plan1", ResourceType.LLM_TOKENS, 500) is True
        assert budget.consumed == 500
        assert budget.available == 500

    def test_budget_exceeded(self):
        budget = ResourceBudget(resource_type=ResourceType.LLM_TOKENS, allocated=100)
        self.allocator.allocate_budget("plan1", budget)

        assert self.allocator.can_afford("plan1", ResourceType.LLM_TOKENS, 200) is False
        assert self.allocator.consume("plan1", ResourceType.LLM_TOKENS, 200) is False

    def test_no_budget_unlimited(self):
        assert self.allocator.can_afford("unknown", ResourceType.LLM_TOKENS, 99999) is True

    def test_reserve_and_release(self):
        budget = ResourceBudget(resource_type=ResourceType.LLM_TOKENS, allocated=1000)
        self.allocator.allocate_budget("plan1", budget)

        node = PlanNode(node_id="n1", name="test", estimated_tokens=500)
        assert self.allocator.reserve_for_node("plan1", node) is True
        assert budget.reserved == 500
        assert budget.available == 500  # 1000 - 0 consumed - 500 reserved

        self.allocator.release_node_reservation("plan1", node)
        assert budget.reserved == 0

    def test_utilization(self):
        budget = ResourceBudget(resource_type=ResourceType.LLM_TOKENS, allocated=1000)
        self.allocator.allocate_budget("plan1", budget)
        self.allocator.consume("plan1", ResourceType.LLM_TOKENS, 800)

        util = self.allocator.get_utilization("plan1")
        assert util["llm_tokens"] == 0.8

    def test_budget_health(self):
        budget = ResourceBudget(resource_type=ResourceType.LLM_TOKENS, allocated=100)
        self.allocator.allocate_budget("plan1", budget)

        self.allocator.consume("plan1", ResourceType.LLM_TOKENS, 85)
        health = self.allocator.check_budget_health("plan1")
        assert health["llm_tokens"] == "WARNING"

        self.allocator.consume("plan1", ResourceType.LLM_TOKENS, 11)
        health = self.allocator.check_budget_health("plan1")
        assert health["llm_tokens"] == "CRITICAL"


# ============================================================================
# FailureRecovery Tests
# ============================================================================


class TestFailureRecovery:
    def setup_method(self):
        self.recovery = FailureRecovery()

    @pytest.mark.asyncio
    async def test_retry_success(self):
        node = PlanNode(
            node_id="n1", name="test",
            recovery_strategy=RecoveryStrategyType.RETRY,
            max_retries=3,
        )
        action = await self.recovery.recover(node, "timeout")
        assert action.success is True
        assert action.next_status == NodeStatus.PENDING
        assert node.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        node = PlanNode(
            node_id="n1", name="test",
            recovery_strategy=RecoveryStrategyType.RETRY,
            max_retries=2, retry_count=2,
        )
        action = await self.recovery.recover(node, "timeout")
        assert action.success is False
        assert action.next_status == NodeStatus.FAILED

    @pytest.mark.asyncio
    async def test_skip_optional(self):
        node = PlanNode(
            node_id="n1", name="test",
            recovery_strategy=RecoveryStrategyType.SKIP,
            optional=True,
        )
        action = await self.recovery.recover(node, "error")
        assert action.success is True
        assert action.next_status == NodeStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_skip_non_optional(self):
        node = PlanNode(
            node_id="n1", name="test",
            recovery_strategy=RecoveryStrategyType.SKIP,
            optional=False,
        )
        action = await self.recovery.recover(node, "error")
        assert action.success is False
        assert action.next_status == NodeStatus.FAILED

    @pytest.mark.asyncio
    async def test_detox_cooldown(self):
        node = PlanNode(
            node_id="n1", name="test",
            recovery_strategy=RecoveryStrategyType.DETOX,
            agent_id="agent_1", max_retries=3,
        )
        action = await self.recovery.recover(node, "overload")
        assert action.success is True
        assert action.retry_after_ms > 0
        assert self.recovery.is_in_cooldown("agent_1") is True

    @pytest.mark.asyncio
    async def test_escalate(self):
        node = PlanNode(
            node_id="n1", name="test",
            recovery_strategy=RecoveryStrategyType.ESCALATE,
        )
        action = await self.recovery.recover(node, "critical error")
        assert action.success is True
        assert action.next_status == NodeStatus.BLOCKED

    @pytest.mark.asyncio
    async def test_rollback(self):
        dep = PlanNode(node_id="dep1", name="dep", status=NodeStatus.COMPLETED)
        node = PlanNode(
            node_id="n1", name="test",
            recovery_strategy=RecoveryStrategyType.ROLLBACK,
            depends_on=["dep1"],
        )
        nodes = {"dep1": dep, "n1": node}
        action = await self.recovery.recover(node, "error", nodes)
        assert action.success is True
        assert dep.status == NodeStatus.PENDING  # Rolled back

    def test_stats(self):
        stats = self.recovery.stats
        assert stats["total_recoveries"] == 0


# ============================================================================
# PlanningService Integration Tests
# ============================================================================


class TestPlanningService:
    def setup_method(self):
        self.svc = PlanningService()

    def test_decompose_and_validate(self):
        req = DecompositionRequest(
            task_name="llm_task",
            task_description="Process data",
            agent_id="a1",
        )
        result = self.svc.decompose_task(req)
        plan_id = result.plan.plan_id

        errors = self.svc.validate_plan(plan_id)
        assert len(errors) == 0

        plan = self.svc.get_plan(plan_id)
        assert plan.status == PlanStatus.VALIDATED

    def test_start_plan(self):
        req = DecompositionRequest(task_name="llm_task", task_description="Test")
        result = self.svc.decompose_task(req)
        plan_id = result.plan.plan_id

        plan = self.svc.start_plan(plan_id)
        assert plan.status == PlanStatus.EXECUTING

        ready = self.svc.get_ready_nodes(plan_id)
        assert len(ready) > 0

    def test_node_lifecycle(self):
        req = DecompositionRequest(task_name="llm_task", task_description="Test")
        result = self.svc.decompose_task(req)
        plan_id = result.plan.plan_id

        self.svc.start_plan(plan_id)
        ready = self.svc.get_ready_nodes(plan_id)
        node = ready[0]

        # Start node
        started = self.svc.start_node(plan_id, node.node_id)
        assert started.status == NodeStatus.RUNNING

        # Complete node
        completed = self.svc.complete_node(plan_id, node.node_id, {"output": "done"})
        assert completed.status == NodeStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_node_failure_recovery(self):
        req = DecompositionRequest(task_name="llm_task", task_description="Test")
        result = self.svc.decompose_task(req)
        plan_id = result.plan.plan_id

        self.svc.start_plan(plan_id)
        ready = self.svc.get_ready_nodes(plan_id)
        node = ready[0]
        self.svc.start_node(plan_id, node.node_id)

        action = await self.svc.fail_node(plan_id, node.node_id, "timeout")
        assert action is not None
        assert action.strategy == RecoveryStrategyType.RETRY

    def test_critical_path_analysis(self):
        req = DecompositionRequest(task_name="data_pipeline", task_description="Pipeline")
        result = self.svc.decompose_task(req)
        plan_id = result.plan.plan_id

        cp = self.svc.get_critical_path(plan_id)
        assert cp is not None
        assert cp["length"] >= 1

    def test_parallel_groups(self):
        req = DecompositionRequest(task_name="llm_task", task_description="Test")
        result = self.svc.decompose_task(req)
        plan_id = result.plan.plan_id

        groups = self.svc.get_parallel_groups(plan_id)
        assert groups is not None
        assert len(groups) >= 1

    def test_stats(self):
        stats = self.svc.get_stats()
        assert stats.total_plans == 0
