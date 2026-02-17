"""
Planning Module - Pydantic schemas.

Models for task decomposition, dependency graphs, resource budgets,
execution plans, and failure recovery.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class PlanStatus(str, Enum):
    """Lifecycle of an execution plan."""
    DRAFT = "draft"
    VALIDATED = "validated"
    READY = "ready"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERING = "recovering"


class NodeStatus(str, Enum):
    """Lifecycle of a plan node (sub-task)."""
    PENDING = "pending"
    BLOCKED = "blocked"       # Waiting on dependencies
    READY = "ready"           # All deps satisfied
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"       # Skipped due to optional/conditional


class NodeType(str, Enum):
    """Types of plan nodes."""
    ACTION = "action"         # Concrete executable step
    DECISION = "decision"     # Branching point
    PARALLEL = "parallel"     # Fan-out parallel execution
    BARRIER = "barrier"       # Sync point (wait for all)
    CHECKPOINT = "checkpoint" # Save state for recovery


class RecoveryStrategyType(str, Enum):
    """Types of failure recovery."""
    RETRY = "retry"
    ROLLBACK = "rollback"
    SKIP = "skip"
    ALTERNATIVE = "alternative"
    DETOX = "detox"           # BRAIN Detox system integration
    ESCALATE = "escalate"     # Escalate to supervisor


class ResourceType(str, Enum):
    """Types of allocatable resources."""
    LLM_TOKENS = "llm_tokens"
    COMPUTE_TIME = "compute_time"
    API_CALLS = "api_calls"
    MEMORY_MB = "memory_mb"
    COST_USD = "cost_usd"


# ============================================================================
# Plan node models
# ============================================================================


class PlanNode(BaseModel):
    """A single node (sub-task) in an execution plan."""
    node_id: str = Field(default_factory=lambda: f"node_{uuid.uuid4().hex[:10]}")
    name: str
    description: str = ""
    node_type: NodeType = NodeType.ACTION

    # Execution
    agent_id: Optional[str] = None          # Assigned agent
    action: str = ""                        # Action identifier
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: NodeStatus = NodeStatus.PENDING

    # Dependencies (node_ids that must complete before this)
    depends_on: List[str] = Field(default_factory=list)

    # Resource requirements
    estimated_tokens: int = 0
    estimated_time_ms: int = 0
    estimated_cost: float = 0.0

    # Recovery
    recovery_strategy: RecoveryStrategyType = RecoveryStrategyType.RETRY
    max_retries: int = 2
    retry_count: int = 0

    # Conditional execution
    condition: Optional[str] = None         # Expression to evaluate
    optional: bool = False                  # Can be skipped on failure

    # Results
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds() * 1000
        return None


class ResourceBudget(BaseModel):
    """Resource budget for a plan."""
    budget_id: str = Field(default_factory=lambda: f"bud_{uuid.uuid4().hex[:10]}")
    resource_type: ResourceType
    allocated: float
    consumed: float = 0.0
    reserved: float = 0.0  # Reserved for running nodes

    @property
    def available(self) -> float:
        return max(0.0, self.allocated - self.consumed - self.reserved)

    @property
    def utilization(self) -> float:
        return self.consumed / self.allocated if self.allocated > 0 else 0.0

    def can_afford(self, amount: float) -> bool:
        return self.available >= amount

    def consume(self, amount: float) -> bool:
        if not self.can_afford(amount):
            return False
        self.consumed += amount
        return True

    def reserve(self, amount: float) -> bool:
        if self.available < amount:
            return False
        self.reserved += amount
        return True

    def release_reservation(self, amount: float) -> None:
        self.reserved = max(0.0, self.reserved - amount)


class RecoveryStrategy(BaseModel):
    """Configuration for failure recovery."""
    strategy_type: RecoveryStrategyType
    max_retries: int = 3
    backoff_base: float = 1.0           # Seconds
    backoff_max: float = 60.0
    alternative_node_id: Optional[str] = None  # For ALTERNATIVE strategy
    detox_cooldown_ms: int = 5000       # For DETOX strategy
    escalate_to: Optional[str] = None   # Agent ID for ESCALATE


# ============================================================================
# Execution plan
# ============================================================================


class ExecutionPlan(BaseModel):
    """A complete execution plan with nodes and resources."""
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:12]}")
    name: str
    description: str = ""
    agent_id: str = ""                    # Owning agent
    mission_id: Optional[str] = None      # Associated mission

    # Plan structure
    nodes: List[PlanNode] = Field(default_factory=list)
    root_node_ids: List[str] = Field(default_factory=list)  # Entry points

    # Resources
    budgets: List[ResourceBudget] = Field(default_factory=list)

    # Recovery
    global_recovery: RecoveryStrategyType = RecoveryStrategyType.RETRY
    checkpoint_interval: int = 3          # Checkpoint every N completed nodes

    # Status
    status: PlanStatus = PlanStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Metrics
    total_nodes: int = 0
    completed_nodes: int = 0
    failed_nodes: int = 0

    @property
    def progress(self) -> float:
        return self.completed_nodes / self.total_nodes if self.total_nodes > 0 else 0.0


class DecompositionRequest(BaseModel):
    """Request to decompose a task into sub-tasks."""
    task_name: str
    task_description: str
    agent_id: str = ""
    mission_id: Optional[str] = None
    max_depth: int = 3
    max_nodes: int = 20
    available_capabilities: List[str] = Field(default_factory=list)
    resource_constraints: Dict[str, float] = Field(default_factory=dict)


class DecompositionResult(BaseModel):
    """Result of task decomposition."""
    plan: ExecutionPlan
    decomposition_depth: int
    total_estimated_tokens: int = 0
    total_estimated_time_ms: int = 0
    total_estimated_cost: float = 0.0
    critical_path_length: int = 0
    parallelism_factor: float = 1.0


# ============================================================================
# API models
# ============================================================================


class PlanningInfo(BaseModel):
    name: str = "Advanced Planning Engine"
    version: str = "1.0.0"
    module: str = "planning"
    sprint: str = "8"
    features: List[str] = Field(default_factory=lambda: [
        "task_decomposition",
        "dependency_graphs",
        "resource_allocation",
        "failure_recovery",
        "detox_integration",
        "critical_path_analysis",
    ])


class PlanningStats(BaseModel):
    total_plans: int = 0
    active_plans: int = 0
    completed_plans: int = 0
    failed_plans: int = 0
    total_nodes_executed: int = 0
    total_recoveries: int = 0
    resource_utilization: Dict[str, float] = Field(default_factory=dict)
