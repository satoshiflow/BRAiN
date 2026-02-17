"""
Advanced Planning Engine - Sprint 8

Multi-step task decomposition, dependency graphs, resource allocation,
and failure recovery with Detox integration.

Architecture:
    TaskDecomposer     → Break complex tasks into sub-tasks
    DependencyGraph    → DAG with topological ordering and critical path
    ResourceAllocator  → Budget, capacity, and token management
    FailureRecovery    → Detox-integrated recovery strategies
    PlanningService    → Unified orchestration layer
"""

from .schemas import (
    PlanNode,
    PlanStatus,
    ExecutionPlan,
    ResourceBudget,
    RecoveryStrategy,
)

__all__ = [
    "PlanNode",
    "PlanStatus",
    "ExecutionPlan",
    "ResourceBudget",
    "RecoveryStrategy",
]
