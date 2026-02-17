"""
Resource Allocator - Budget and capacity management for execution plans.

Tracks resource consumption across plans and nodes, enforces budgets,
and provides utilization reporting.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from loguru import logger

from .schemas import (
    ExecutionPlan,
    PlanNode,
    ResourceBudget,
    ResourceType,
)


class ResourceAllocator:
    """
    Manages resource budgets for execution plans.

    Each plan has budgets per resource type. Nodes consume
    from these budgets as they execute.
    """

    def __init__(self) -> None:
        # plan_id → {resource_type → ResourceBudget}
        self._budgets: Dict[str, Dict[ResourceType, ResourceBudget]] = defaultdict(dict)
        self._total_allocations = 0
        self._total_consumed = 0

        logger.info("💰 ResourceAllocator initialized")

    # ------------------------------------------------------------------
    # Budget management
    # ------------------------------------------------------------------

    def allocate_budget(self, plan_id: str, budget: ResourceBudget) -> ResourceBudget:
        """Allocate a resource budget for a plan."""
        self._budgets[plan_id][budget.resource_type] = budget
        self._total_allocations += 1
        return budget

    def allocate_from_plan(self, plan: ExecutionPlan) -> List[ResourceBudget]:
        """Allocate all budgets defined in a plan."""
        for budget in plan.budgets:
            self.allocate_budget(plan.plan_id, budget)
        return plan.budgets

    def get_budget(self, plan_id: str, resource_type: ResourceType) -> Optional[ResourceBudget]:
        return self._budgets.get(plan_id, {}).get(resource_type)

    def get_plan_budgets(self, plan_id: str) -> List[ResourceBudget]:
        return list(self._budgets.get(plan_id, {}).values())

    # ------------------------------------------------------------------
    # Consumption
    # ------------------------------------------------------------------

    def can_afford(self, plan_id: str, resource_type: ResourceType, amount: float) -> bool:
        """Check if a plan can afford a resource consumption."""
        budget = self.get_budget(plan_id, resource_type)
        if budget is None:
            return True  # No budget = unlimited
        return budget.can_afford(amount)

    def consume(self, plan_id: str, resource_type: ResourceType, amount: float) -> bool:
        """Consume resources from a plan's budget."""
        budget = self.get_budget(plan_id, resource_type)
        if budget is None:
            return True  # No budget = unlimited
        ok = budget.consume(amount)
        if ok:
            self._total_consumed += 1
        else:
            logger.warning("Budget exceeded: plan=%s, type=%s, requested=%.2f, available=%.2f",
                          plan_id, resource_type.value, amount, budget.available)
        return ok

    def reserve_for_node(self, plan_id: str, node: PlanNode) -> bool:
        """Reserve estimated resources for a node before execution."""
        reservations = self._node_resource_map(node)
        for rtype, amount in reservations.items():
            budget = self.get_budget(plan_id, rtype)
            if budget and not budget.reserve(amount):
                # Rollback previous reservations
                for prev_type in reservations:
                    if prev_type == rtype:
                        break
                    prev_budget = self.get_budget(plan_id, prev_type)
                    if prev_budget:
                        prev_budget.release_reservation(reservations[prev_type])
                return False
        return True

    def release_node_reservation(self, plan_id: str, node: PlanNode) -> None:
        """Release reserved resources after node completion."""
        reservations = self._node_resource_map(node)
        for rtype, amount in reservations.items():
            budget = self.get_budget(plan_id, rtype)
            if budget:
                budget.release_reservation(amount)

    def consume_node_actual(self, plan_id: str, node: PlanNode, actual: Dict[ResourceType, float]) -> None:
        """Consume actual resources and release reservation."""
        self.release_node_reservation(plan_id, node)
        for rtype, amount in actual.items():
            self.consume(plan_id, rtype, amount)

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_utilization(self, plan_id: str) -> Dict[str, float]:
        """Get utilization ratios for all budget types."""
        budgets = self._budgets.get(plan_id, {})
        return {
            rtype.value: budget.utilization
            for rtype, budget in budgets.items()
        }

    def check_budget_health(self, plan_id: str) -> Dict[str, str]:
        """Check budget health: OK / WARNING (>80%) / CRITICAL (>95%)."""
        result = {}
        for rtype, budget in self._budgets.get(plan_id, {}).items():
            util = budget.utilization
            if util > 0.95:
                result[rtype.value] = "CRITICAL"
            elif util > 0.80:
                result[rtype.value] = "WARNING"
            else:
                result[rtype.value] = "OK"
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _node_resource_map(node: PlanNode) -> Dict[ResourceType, float]:
        """Map node estimates to resource types."""
        resources = {}
        if node.estimated_tokens > 0:
            resources[ResourceType.LLM_TOKENS] = float(node.estimated_tokens)
        if node.estimated_time_ms > 0:
            resources[ResourceType.COMPUTE_TIME] = float(node.estimated_time_ms)
        if node.estimated_cost > 0:
            resources[ResourceType.COST_USD] = node.estimated_cost
        return resources

    @property
    def stats(self) -> Dict:
        return {
            "total_allocations": self._total_allocations,
            "total_consumed": self._total_consumed,
            "tracked_plans": len(self._budgets),
        }
