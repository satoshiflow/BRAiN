"""
Task Decomposer - Multi-step task breakdown.

Breaks complex tasks into a DAG of sub-tasks with:
- Automatic dependency detection (sequential, parallel, barrier)
- Resource estimation per node
- Capability-based agent assignment suggestions
- Checkpoint insertion for recovery
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from loguru import logger

from .schemas import (
    DecompositionRequest,
    DecompositionResult,
    ExecutionPlan,
    NodeStatus,
    NodeType,
    PlanNode,
    PlanStatus,
    RecoveryStrategyType,
    ResourceBudget,
    ResourceType,
)


# Default resource estimates per action type
DEFAULT_ESTIMATES: Dict[str, Dict[str, int]] = {
    "llm_call": {"tokens": 1000, "time_ms": 3000, "cost_cents": 2},
    "api_call": {"tokens": 0, "time_ms": 500, "cost_cents": 0},
    "compute": {"tokens": 0, "time_ms": 2000, "cost_cents": 1},
    "io_operation": {"tokens": 0, "time_ms": 1000, "cost_cents": 0},
    "default": {"tokens": 500, "time_ms": 1000, "cost_cents": 1},
}


class TaskDecomposer:
    """
    Decomposes complex tasks into execution plan DAGs.

    Uses pattern-based decomposition (not LLM-based) to create
    deterministic, reproducible plans.
    """

    def __init__(self) -> None:
        self._templates: Dict[str, List[Dict[str, Any]]] = {}
        self._total_decompositions = 0
        self._register_default_templates()

        logger.info("🔨 TaskDecomposer initialized")

    # ------------------------------------------------------------------
    # Template registration
    # ------------------------------------------------------------------

    def register_template(self, task_pattern: str, steps: List[Dict[str, Any]]) -> None:
        """Register a decomposition template for a task pattern."""
        self._templates[task_pattern] = steps

    def _register_default_templates(self) -> None:
        """Register built-in decomposition templates."""
        self._templates["llm_task"] = [
            {"name": "prepare_context", "action": "io_operation", "type": "action"},
            {"name": "execute_llm_call", "action": "llm_call", "type": "action", "depends": ["prepare_context"]},
            {"name": "validate_output", "action": "compute", "type": "action", "depends": ["execute_llm_call"]},
        ]
        self._templates["multi_agent_task"] = [
            {"name": "analyze_task", "action": "llm_call", "type": "action"},
            {"name": "delegate_subtasks", "action": "api_call", "type": "parallel", "depends": ["analyze_task"]},
            {"name": "collect_results", "action": "compute", "type": "barrier", "depends": ["delegate_subtasks"]},
            {"name": "synthesize", "action": "llm_call", "type": "action", "depends": ["collect_results"]},
        ]
        self._templates["data_pipeline"] = [
            {"name": "fetch_data", "action": "api_call", "type": "action"},
            {"name": "transform_data", "action": "compute", "type": "action", "depends": ["fetch_data"]},
            {"name": "validate_data", "action": "compute", "type": "action", "depends": ["transform_data"]},
            {"name": "store_results", "action": "io_operation", "type": "action", "depends": ["validate_data"]},
        ]

    # ------------------------------------------------------------------
    # Decomposition
    # ------------------------------------------------------------------

    def decompose(self, request: DecompositionRequest) -> DecompositionResult:
        """
        Decompose a task into an execution plan.

        Uses template matching first, then falls back to generic decomposition.
        """
        self._total_decompositions += 1

        # Try template match
        template = self._find_template(request.task_name, request.task_description)

        if template:
            nodes = self._apply_template(template, request)
        else:
            nodes = self._generic_decompose(request)

        # Cap at max_nodes
        nodes = nodes[: request.max_nodes]

        # Insert checkpoints
        nodes = self._insert_checkpoints(nodes, interval=3)

        # Build plan
        root_ids = [n.node_id for n in nodes if not n.depends_on]
        plan = ExecutionPlan(
            name=f"Plan: {request.task_name}",
            description=request.task_description,
            agent_id=request.agent_id,
            mission_id=request.mission_id,
            nodes=nodes,
            root_node_ids=root_ids,
            status=PlanStatus.DRAFT,
            total_nodes=len(nodes),
        )

        # Allocate resource budgets
        plan.budgets = self._estimate_budgets(nodes, request.resource_constraints)

        # Compute result metrics
        total_tokens = sum(n.estimated_tokens for n in nodes)
        total_time = sum(n.estimated_time_ms for n in nodes)
        total_cost = sum(n.estimated_cost for n in nodes)

        result = DecompositionResult(
            plan=plan,
            decomposition_depth=self._compute_depth(nodes),
            total_estimated_tokens=total_tokens,
            total_estimated_time_ms=total_time,
            total_estimated_cost=total_cost,
            critical_path_length=self._critical_path_length(nodes),
            parallelism_factor=len(nodes) / max(1, self._critical_path_length(nodes)),
        )

        logger.info(
            "🔨 Decomposed '%s' into %d nodes (critical_path=%d, parallelism=%.1f)",
            request.task_name, len(nodes), result.critical_path_length, result.parallelism_factor,
        )
        return result

    # ------------------------------------------------------------------
    # Template matching
    # ------------------------------------------------------------------

    def _find_template(self, task_name: str, description: str) -> Optional[List[Dict]]:
        """Find a matching template by task name or description keywords."""
        name_lower = task_name.lower()
        desc_lower = description.lower()

        for pattern, steps in self._templates.items():
            if pattern in name_lower or pattern in desc_lower:
                return steps
        return None

    def _apply_template(self, template: List[Dict], request: DecompositionRequest) -> List[PlanNode]:
        """Apply a template to create plan nodes."""
        nodes: List[PlanNode] = []
        id_map: Dict[str, str] = {}  # template_name → node_id

        for step in template:
            node = PlanNode(
                name=step["name"],
                description=f"{step['name']} for {request.task_name}",
                node_type=NodeType(step.get("type", "action")),
                action=step.get("action", "default"),
                agent_id=request.agent_id,
            )

            # Map dependencies
            for dep_name in step.get("depends", []):
                if dep_name in id_map:
                    node.depends_on.append(id_map[dep_name])

            # Estimate resources
            est = DEFAULT_ESTIMATES.get(step.get("action", "default"), DEFAULT_ESTIMATES["default"])
            node.estimated_tokens = est["tokens"]
            node.estimated_time_ms = est["time_ms"]
            node.estimated_cost = est["cost_cents"] / 100.0

            id_map[step["name"]] = node.node_id
            nodes.append(node)

        return nodes

    # ------------------------------------------------------------------
    # Generic decomposition
    # ------------------------------------------------------------------

    def _generic_decompose(self, request: DecompositionRequest) -> List[PlanNode]:
        """Generic 3-phase decomposition: prepare → execute → finalize."""
        nodes = []

        prepare = PlanNode(
            name="prepare",
            description=f"Prepare context for: {request.task_name}",
            node_type=NodeType.ACTION,
            action="io_operation",
            agent_id=request.agent_id,
            estimated_tokens=200,
            estimated_time_ms=500,
        )
        nodes.append(prepare)

        execute = PlanNode(
            name="execute",
            description=f"Execute: {request.task_name}",
            node_type=NodeType.ACTION,
            action="llm_call",
            agent_id=request.agent_id,
            depends_on=[prepare.node_id],
            estimated_tokens=1000,
            estimated_time_ms=3000,
            estimated_cost=0.02,
        )
        nodes.append(execute)

        finalize = PlanNode(
            name="finalize",
            description=f"Finalize: {request.task_name}",
            node_type=NodeType.ACTION,
            action="compute",
            agent_id=request.agent_id,
            depends_on=[execute.node_id],
            estimated_tokens=0,
            estimated_time_ms=500,
        )
        nodes.append(finalize)

        return nodes

    # ------------------------------------------------------------------
    # Checkpoints & metrics
    # ------------------------------------------------------------------

    def _insert_checkpoints(self, nodes: List[PlanNode], interval: int = 3) -> List[PlanNode]:
        """Insert checkpoint nodes at regular intervals."""
        result = []
        action_count = 0

        for node in nodes:
            result.append(node)
            if node.node_type == NodeType.ACTION:
                action_count += 1
                if action_count % interval == 0:
                    cp = PlanNode(
                        name=f"checkpoint_{action_count}",
                        description="Save execution state",
                        node_type=NodeType.CHECKPOINT,
                        depends_on=[node.node_id],
                        estimated_time_ms=100,
                    )
                    result.append(cp)

        return result

    def _compute_depth(self, nodes: List[PlanNode]) -> int:
        """Compute max dependency depth."""
        node_map = {n.node_id: n for n in nodes}
        cache: Dict[str, int] = {}

        def depth(nid: str) -> int:
            if nid in cache:
                return cache[nid]
            node = node_map.get(nid)
            if not node or not node.depends_on:
                cache[nid] = 0
                return 0
            d = 1 + max(depth(dep) for dep in node.depends_on if dep in node_map)
            cache[nid] = d
            return d

        return max((depth(n.node_id) for n in nodes), default=0)

    def _critical_path_length(self, nodes: List[PlanNode]) -> int:
        """Compute critical path length (longest chain of dependencies)."""
        return self._compute_depth(nodes) + 1

    def _estimate_budgets(
        self,
        nodes: List[PlanNode],
        constraints: Dict[str, float],
    ) -> List[ResourceBudget]:
        """Estimate resource budgets with 20% headroom."""
        total_tokens = sum(n.estimated_tokens for n in nodes)
        total_time = sum(n.estimated_time_ms for n in nodes)
        total_cost = sum(n.estimated_cost for n in nodes)

        headroom = 1.2  # 20% buffer

        budgets = []
        if total_tokens > 0:
            budgets.append(ResourceBudget(
                resource_type=ResourceType.LLM_TOKENS,
                allocated=constraints.get("llm_tokens", total_tokens * headroom),
            ))
        if total_time > 0:
            budgets.append(ResourceBudget(
                resource_type=ResourceType.COMPUTE_TIME,
                allocated=constraints.get("compute_time", total_time * headroom),
            ))
        if total_cost > 0:
            budgets.append(ResourceBudget(
                resource_type=ResourceType.COST_USD,
                allocated=constraints.get("cost_usd", total_cost * headroom),
            ))

        return budgets

    @property
    def stats(self) -> Dict:
        return {
            "total_decompositions": self._total_decompositions,
            "registered_templates": len(self._templates),
        }
