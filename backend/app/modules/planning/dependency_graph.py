"""
Dependency Graph - DAG operations for execution plans.

Provides:
- Topological ordering for execution sequencing
- Cycle detection (plans must be acyclic)
- Critical path computation
- Ready-node detection (all deps satisfied)
- Parallel group identification
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Dict, List, Optional, Set, Tuple

from loguru import logger

from .schemas import NodeStatus, PlanNode


class DependencyGraph:
    """
    Directed Acyclic Graph for plan node dependencies.

    Built from PlanNode.depends_on relationships.
    """

    def __init__(self, nodes: List[PlanNode]) -> None:
        self._nodes: Dict[str, PlanNode] = {n.node_id: n for n in nodes}
        # Forward edges: node → set of nodes it depends on
        self._deps: Dict[str, Set[str]] = defaultdict(set)
        # Reverse edges: node → set of nodes that depend on it
        self._dependents: Dict[str, Set[str]] = defaultdict(set)

        for node in nodes:
            for dep_id in node.depends_on:
                if dep_id in self._nodes:
                    self._deps[node.node_id].add(dep_id)
                    self._dependents[dep_id].add(node.node_id)

        logger.debug("DependencyGraph built: %d nodes, %d edges",
                      len(self._nodes), sum(len(d) for d in self._deps.values()))

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def has_cycle(self) -> bool:
        """Detect cycles using Kahn's algorithm."""
        in_degree = {nid: len(self._deps.get(nid, set())) for nid in self._nodes}
        queue = deque(nid for nid, deg in in_degree.items() if deg == 0)
        visited = 0

        while queue:
            nid = queue.popleft()
            visited += 1
            for dep_id in self._dependents.get(nid, set()):
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    queue.append(dep_id)

        return visited != len(self._nodes)

    def validate(self) -> List[str]:
        """Validate the graph. Returns list of error messages."""
        errors = []

        if self.has_cycle():
            errors.append("Graph contains a cycle")

        # Check for missing dependency references
        for nid, deps in self._deps.items():
            for dep in deps:
                if dep not in self._nodes:
                    errors.append(f"Node '{nid}' depends on missing node '{dep}'")

        # Check for orphans (no deps and no dependents, except roots)
        root_ids = self.get_root_nodes()
        for nid in self._nodes:
            if nid not in root_ids and not self._deps.get(nid) and not self._dependents.get(nid):
                errors.append(f"Node '{nid}' is disconnected from the graph")

        return errors

    # ------------------------------------------------------------------
    # Ordering
    # ------------------------------------------------------------------

    def topological_sort(self) -> List[str]:
        """Return nodes in topological order (Kahn's algorithm)."""
        in_degree = {nid: len(self._deps.get(nid, set())) for nid in self._nodes}
        queue = deque(sorted(nid for nid, deg in in_degree.items() if deg == 0))
        result = []

        while queue:
            nid = queue.popleft()
            result.append(nid)
            for dep_id in sorted(self._dependents.get(nid, set())):
                in_degree[dep_id] -= 1
                if in_degree[dep_id] == 0:
                    queue.append(dep_id)

        return result

    # ------------------------------------------------------------------
    # Node queries
    # ------------------------------------------------------------------

    def get_root_nodes(self) -> List[str]:
        """Get nodes with no dependencies (entry points)."""
        return [nid for nid in self._nodes if not self._deps.get(nid)]

    def get_leaf_nodes(self) -> List[str]:
        """Get nodes with no dependents (exit points)."""
        return [nid for nid in self._nodes if not self._dependents.get(nid)]

    def get_ready_nodes(self, completed: Set[str]) -> List[str]:
        """
        Get nodes whose dependencies are all in the completed set.

        These nodes can be executed next.
        """
        ready = []
        for nid, node in self._nodes.items():
            if node.status not in (NodeStatus.PENDING, NodeStatus.BLOCKED, NodeStatus.READY):
                continue
            deps = self._deps.get(nid, set())
            if deps.issubset(completed):
                ready.append(nid)
        return ready

    def get_parallel_groups(self) -> List[List[str]]:
        """
        Identify groups of nodes that can execute in parallel.

        Returns layers where each layer contains nodes that
        can run concurrently (same topological depth).
        """
        topo = self.topological_sort()
        if not topo:
            return []

        # Compute depth for each node
        depth: Dict[str, int] = {}
        for nid in topo:
            deps = self._deps.get(nid, set())
            if not deps:
                depth[nid] = 0
            else:
                depth[nid] = 1 + max(depth.get(d, 0) for d in deps)

        # Group by depth
        groups: Dict[int, List[str]] = defaultdict(list)
        for nid, d in depth.items():
            groups[d].append(nid)

        return [groups[d] for d in sorted(groups.keys())]

    # ------------------------------------------------------------------
    # Critical path
    # ------------------------------------------------------------------

    def critical_path(self) -> Tuple[List[str], int]:
        """
        Compute the critical path (longest weighted path).

        Weight = estimated_time_ms per node.
        Returns (path_node_ids, total_time_ms).
        """
        topo = self.topological_sort()
        if not topo:
            return [], 0

        dist: Dict[str, int] = {}
        prev: Dict[str, Optional[str]] = {}

        for nid in topo:
            node = self._nodes[nid]
            weight = node.estimated_time_ms or 1

            deps = self._deps.get(nid, set())
            if not deps:
                dist[nid] = weight
                prev[nid] = None
            else:
                best_dep = max(deps, key=lambda d: dist.get(d, 0))
                dist[nid] = dist.get(best_dep, 0) + weight
                prev[nid] = best_dep

        # Find the node with max distance
        if not dist:
            return [], 0

        end_node = max(dist, key=dist.get)

        # Trace back
        path = []
        current: Optional[str] = end_node
        while current is not None:
            path.append(current)
            current = prev.get(current)
        path.reverse()

        return path, dist[end_node]

    # ------------------------------------------------------------------
    # Subgraph
    # ------------------------------------------------------------------

    def get_downstream(self, node_id: str) -> Set[str]:
        """Get all nodes transitively dependent on the given node."""
        visited: Set[str] = set()
        queue = deque([node_id])

        while queue:
            nid = queue.popleft()
            for dep in self._dependents.get(nid, set()):
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
        return visited

    def get_upstream(self, node_id: str) -> Set[str]:
        """Get all transitive dependencies of the given node."""
        visited: Set[str] = set()
        queue = deque([node_id])

        while queue:
            nid = queue.popleft()
            for dep in self._deps.get(nid, set()):
                if dep not in visited:
                    visited.add(dep)
                    queue.append(dep)
        return visited
