"""
ExecutionGraph Orchestrator (Sprint 8.2)

DAG-based orchestrator for autonomous business pipeline.
Executes nodes in dependency order with rollback support.
"""

from typing import Dict, List, Set, Optional, Type
from collections import defaultdict
import time
from loguru import logger

from backend.app.modules.autonomous_pipeline.schemas import (
    ExecutionGraphSpec,
    ExecutionGraphResult,
    ExecutionNodeResult,
    ExecutionNodeStatus,
)
from backend.app.modules.autonomous_pipeline.execution_node import (
    ExecutionNode,
    ExecutionContext,
    ExecutionNodeError,
    RollbackError,
)

# Sprint 9: Governor integration (optional)
try:
    from backend.app.modules.autonomous_pipeline.governor import (
        ExecutionGovernor,
        BudgetExceededException,
        ApprovalRequiredException,
    )
    from backend.app.modules.autonomous_pipeline.governor_schemas import (
        GovernorDecisionType,
    )
    GOVERNOR_AVAILABLE = True
except ImportError:
    GOVERNOR_AVAILABLE = False


class ExecutionGraphError(Exception):
    """Raised when graph construction or execution fails."""
    pass


class CyclicDependencyError(ExecutionGraphError):
    """Raised when graph contains cycles."""
    pass


class ExecutionGraph:
    """
    DAG-based execution orchestrator.

    Features:
    - Dependency resolution via topological sort
    - Dry-run support (simulation without side effects)
    - Automatic rollback on failure
    - Stop-on-first-error mode
    - Comprehensive audit trail
    """

    def __init__(self, spec: ExecutionGraphSpec, governor: Optional['ExecutionGovernor'] = None):
        """
        Initialize execution graph.

        Args:
            spec: Graph specification with nodes and dependencies
            governor: Optional execution governor for budget/policy enforcement (Sprint 9)

        Raises:
            ExecutionGraphError: If graph is invalid
            CyclicDependencyError: If graph contains cycles
        """
        self.spec = spec
        self.graph_id = spec.graph_id
        self.business_intent_id = spec.business_intent_id

        # Sprint 9: Governor integration
        self.governor = governor

        # Build dependency graph
        self.nodes: Dict[str, ExecutionNode] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.execution_order: List[str] = []

        # Execution state
        self.completed_nodes: Set[str] = set()
        self.failed_nodes: Set[str] = set()
        self.node_results: Dict[str, ExecutionNodeResult] = {}
        self.skipped_nodes: Set[str] = set()  # Sprint 9: Degraded nodes

        # Build graph
        self._build_graph()

    def _build_graph(self):
        """
        Build execution graph from spec.

        Raises:
            ExecutionGraphError: If graph construction fails
            CyclicDependencyError: If cycles detected
        """
        logger.info(f"[{self.graph_id}] Building execution graph with {len(self.spec.nodes)} nodes")

        # Extract dependencies
        for node_spec in self.spec.nodes:
            self.dependencies[node_spec.node_id] = node_spec.depends_on

        # Validate all dependencies exist
        all_node_ids = {node.node_id for node in self.spec.nodes}
        for node_id, deps in self.dependencies.items():
            for dep in deps:
                if dep not in all_node_ids:
                    raise ExecutionGraphError(
                        f"Node {node_id} depends on non-existent node: {dep}"
                    )

        # Compute topological sort (execution order)
        self.execution_order = self._topological_sort()

        logger.info(
            f"[{self.graph_id}] Execution order: {' → '.join(self.execution_order)}"
        )

    def _topological_sort(self) -> List[str]:
        """
        Compute topological sort of nodes (Kahn's algorithm).

        Returns:
            List of node IDs in execution order

        Raises:
            CyclicDependencyError: If graph contains cycles
        """
        # Count incoming edges for each node
        in_degree = {node_id: 0 for node_id in self.dependencies.keys()}
        for deps in self.dependencies.values():
            for dep in deps:
                in_degree[dep] += 1

        # Queue of nodes with no incoming edges
        queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # Take node with no dependencies
            node_id = queue.pop(0)
            result.append(node_id)

            # Remove edges from this node
            for dependent in self.dependencies.get(node_id, []):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If we didn't process all nodes, there's a cycle
        if len(result) != len(self.dependencies):
            raise CyclicDependencyError(
                f"Graph contains cyclic dependencies. Processed {len(result)}/{len(self.dependencies)} nodes."
            )

        return result

    async def execute(self) -> ExecutionGraphResult:
        """
        Execute the graph.

        Returns:
            ExecutionGraphResult with all node results

        Raises:
            ExecutionGraphError: If execution fails critically
        """
        start_time = time.time()

        # Sprint 9: Start governor (if available)
        if self.governor:
            self.governor.start_execution()

        # Create execution context
        context = ExecutionContext(
            graph_id=self.graph_id,
            business_intent_id=self.business_intent_id,
            dry_run=self.spec.dry_run,
        )

        # Emit graph start event
        context.emit_audit_event({
            "event_type": "execution_graph_started",
            "graph_id": self.graph_id,
            "business_intent_id": self.business_intent_id,
            "dry_run": self.spec.dry_run,
            "node_count": len(self.spec.nodes),
            "execution_order": self.execution_order,
            "governor_enabled": self.governor is not None,
        })

        logger.info(
            f"[{self.graph_id}] Starting graph execution "
            f"(dry_run={self.spec.dry_run}, nodes={len(self.execution_order)}, "
            f"governor={'enabled' if self.governor else 'disabled'})"
        )

        # Execute nodes in order
        success = True
        error_message: Optional[str] = None

        try:
            for node_id in self.execution_order:
                node_spec = self._get_node_spec(node_id)

                # Sprint 9: Check governor before execution
                if self.governor and GOVERNOR_AVAILABLE:
                    try:
                        decision = self.governor.check_node_execution(
                            node_spec,
                            is_dry_run=self.spec.dry_run
                        )

                        # Handle degradation (skip node)
                        if decision.decision_type == GovernorDecisionType.DEGRADE:
                            self.skipped_nodes.add(node_id)
                            logger.warning(
                                f"[{self.graph_id}] Node {node_id} SKIPPED (degraded): "
                                f"{decision.deny_reason}"
                            )
                            context.emit_audit_event({
                                "event_type": "execution_graph_node_degraded",
                                "node_id": node_id,
                                "reason": decision.deny_reason,
                            })
                            continue  # Skip this node

                        # Handle denial
                        if decision.decision_type == GovernorDecisionType.DENY:
                            self.failed_nodes.add(node_id)
                            error_message = f"Node {node_id} denied by governor: {decision.deny_reason}"
                            logger.error(f"[{self.graph_id}] {error_message}")
                            success = False
                            break

                        # Handle approval requirement
                        if decision.decision_type == GovernorDecisionType.REQUIRE_APPROVAL:
                            self.failed_nodes.add(node_id)
                            error_message = f"Node {node_id} requires approval: {decision.deny_reason}"
                            logger.error(f"[{self.graph_id}] {error_message}")
                            success = False
                            break

                    except (BudgetExceededException, ApprovalRequiredException) as e:
                        # Budget exceeded or approval required
                        self.failed_nodes.add(node_id)
                        error_message = f"Node {node_id} blocked by governor: {e}"
                        logger.error(f"[{self.graph_id}] {error_message}")
                        success = False
                        break

                # Instantiate node executor
                node = self._instantiate_node(node_spec)

                try:
                    # Execute node
                    logger.info(f"[{self.graph_id}] Executing node: {node_id}")
                    node_start = time.time()
                    result = await node.execute_node(context)
                    node_duration = time.time() - node_start

                    self.node_results[node_id] = result
                    self.completed_nodes.add(node_id)

                    # Sprint 9: Record execution in governor
                    if self.governor:
                        # TODO: Track external calls properly
                        external_calls = 0
                        if node_spec.node_type.value in ['dns', 'odoo_module']:
                            external_calls = 1
                        self.governor.record_node_execution(
                            node_id,
                            duration_seconds=node_duration,
                            external_calls=external_calls
                        )

                    logger.info(
                        f"[{self.graph_id}] Node {node_id} completed successfully "
                        f"(duration={result.duration_seconds:.2f}s)"
                    )

                except ExecutionNodeError as e:
                    # Node execution failed
                    self.failed_nodes.add(node_id)
                    error_message = f"Node {node_id} failed: {e}"

                    logger.error(f"[{self.graph_id}] {error_message}")

                    # Emit failure event
                    context.emit_audit_event({
                        "event_type": "execution_graph_node_failed",
                        "node_id": node_id,
                        "error": str(e),
                        "critical": node_spec.critical,
                    })

                    # Stop on first error (if configured)
                    if self.spec.stop_on_first_error or node_spec.critical:
                        success = False
                        break

        except Exception as e:
            # Critical error during execution
            success = False
            error_message = f"Critical graph execution error: {e}"
            logger.error(f"[{self.graph_id}] {error_message}")

        # Rollback on failure (if configured)
        if not success and self.spec.auto_rollback:
            await self._rollback_completed_nodes(context)

        # Calculate final status
        duration_seconds = time.time() - start_time

        if success and len(self.completed_nodes) == len(self.execution_order):
            final_status = ExecutionNodeStatus.COMPLETED
        elif len(self.failed_nodes) > 0:
            final_status = ExecutionNodeStatus.FAILED
        else:
            final_status = ExecutionNodeStatus.PARTIAL

        # Emit graph completion event
        context.emit_audit_event({
            "event_type": "execution_graph_completed",
            "graph_id": self.graph_id,
            "status": final_status.value,
            "completed_nodes": len(self.completed_nodes),
            "failed_nodes": len(self.failed_nodes),
            "duration_seconds": duration_seconds,
        })

        logger.info(
            f"[{self.graph_id}] Graph execution finished: "
            f"status={final_status.value}, "
            f"completed={len(self.completed_nodes)}, "
            f"failed={len(self.failed_nodes)}, "
            f"duration={duration_seconds:.2f}s"
        )

        # Build result
        return ExecutionGraphResult(
            graph_id=self.graph_id,
            business_intent_id=self.business_intent_id,
            status=final_status,
            success=(final_status == ExecutionNodeStatus.COMPLETED),
            node_results=list(self.node_results.values()),
            completed_nodes=list(self.completed_nodes),
            failed_nodes=list(self.failed_nodes),
            execution_order=self.execution_order,
            duration_seconds=duration_seconds,
            was_dry_run=self.spec.dry_run,
            artifacts=context.artifacts,
            audit_events=context.audit_events,
            error=error_message,
        )

    async def _rollback_completed_nodes(self, context: ExecutionContext):
        """
        Rollback all completed nodes in reverse order.

        Args:
            context: Execution context
        """
        logger.warning(
            f"[{self.graph_id}] Starting rollback of {len(self.completed_nodes)} completed nodes"
        )

        # Emit rollback start event
        context.emit_audit_event({
            "event_type": "execution_graph_rollback_started",
            "graph_id": self.graph_id,
            "nodes_to_rollback": list(self.completed_nodes),
        })

        # Rollback in reverse execution order
        rollback_order = [
            node_id for node_id in reversed(self.execution_order)
            if node_id in self.completed_nodes
        ]

        rollback_success_count = 0
        rollback_failure_count = 0

        for node_id in rollback_order:
            node_spec = self._get_node_spec(node_id)
            node = self._instantiate_node(node_spec)

            try:
                logger.warning(f"[{self.graph_id}] Rolling back node: {node_id}")
                await node.rollback_node(context)
                rollback_success_count += 1

            except RollbackError as e:
                rollback_failure_count += 1
                logger.error(f"[{self.graph_id}] Rollback failed for node {node_id}: {e}")

            except NotImplementedError:
                logger.warning(
                    f"[{self.graph_id}] Node {node_id} does not support rollback (not ROLLBACKABLE)"
                )

        # Emit rollback completion event
        context.emit_audit_event({
            "event_type": "execution_graph_rollback_completed",
            "graph_id": self.graph_id,
            "rollback_success": rollback_success_count,
            "rollback_failures": rollback_failure_count,
        })

        logger.info(
            f"[{self.graph_id}] Rollback finished: "
            f"success={rollback_success_count}, failures={rollback_failure_count}"
        )

    def _get_node_spec(self, node_id: str):
        """Get node spec by ID."""
        for node_spec in self.spec.nodes:
            if node_spec.node_id == node_id:
                return node_spec
        raise ExecutionGraphError(f"Node spec not found: {node_id}")

    def _instantiate_node(self, node_spec) -> ExecutionNode:
        """
        Instantiate node executor from spec.

        Args:
            node_spec: ExecutionNodeSpec

        Returns:
            Instantiated ExecutionNode

        Raises:
            ExecutionGraphError: If instantiation fails
        """
        # For now, we return a placeholder
        # In the actual implementation, this would:
        # 1. Import the executor class dynamically
        # 2. Instantiate it with executor_params
        # 3. Return the instance

        # Placeholder implementation:
        # from backend.app.modules.autonomous_pipeline.nodes import WebGenesisNode
        # return WebGenesisNode(node_spec)

        # For Sprint 8.2, we'll just raise an error if called
        # (will be implemented when we create actual node executors in S8.3-S8.5)
        raise NotImplementedError(
            f"Node executor instantiation not yet implemented for: {node_spec.executor_class}"
        )


# Singleton pattern for testing
_execution_graphs: Dict[str, ExecutionGraph] = {}


def create_execution_graph(
    spec: ExecutionGraphSpec,
    governor: Optional['ExecutionGovernor'] = None
) -> ExecutionGraph:
    """
    Create and register execution graph.

    Args:
        spec: Graph specification
        governor: Optional execution governor (Sprint 9)

    Returns:
        ExecutionGraph instance

    Raises:
        ExecutionGraphError: If graph construction fails
    """
    graph = ExecutionGraph(spec, governor=governor)
    _execution_graphs[spec.graph_id] = graph
    return graph


def get_execution_graph(graph_id: str) -> Optional[ExecutionGraph]:
    """Get execution graph by ID."""
    return _execution_graphs.get(graph_id)
