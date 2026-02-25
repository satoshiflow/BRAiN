"""
Learning Module - Pydantic schemas.

Models for performance metrics, adaptive strategies,
A/B experiments, and learning state.
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


class MetricType(str, Enum):
    """Types of trackable metrics."""
    ACCURACY = "accuracy"            # Model accuracy (0-1)
    LATENCY = "latency"              # Response time (ms)
    SUCCESS_RATE = "success_rate"    # Success ratio (0-1)
    TOKEN_USAGE = "token_usage"      # LLM tokens consumed
    QUALITY_SCORE = "quality_score"  # Output quality (0-100)
    THROUGHPUT = "throughput"        # Tasks per minute
    ERROR_RATE = "error_rate"        # Error ratio (0-1)
    KARMA_DELTA = "karma_delta"      # KARMA score change
    COST = "cost"                    # Resource cost
    CUSTOM = "custom"


class AggregationWindow(str, Enum):
    """Time windows for metric aggregation."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    HOUR_1 = "1h"
    HOUR_6 = "6h"
    DAY_1 = "1d"


class StrategyStatus(str, Enum):
    """Lifecycle of a learning strategy."""
    CANDIDATE = "candidate"    # New, untested
    ACTIVE = "active"          # Currently in use
    EVALUATING = "evaluating"  # Under A/B test
    PROMOTED = "promoted"      # Won test, now default
    DEMOTED = "demoted"        # Lost test, archived
    RETIRED = "retired"        # No longer viable


class ExperimentStatus(str, Enum):
    """A/B experiment lifecycle."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# ============================================================================
# Metric models
# ============================================================================


class MetricEntry(BaseModel):
    """A single metric data point."""
    metric_id: str = Field(default_factory=lambda: f"met_{uuid.uuid4().hex[:12]}")
    agent_id: str
    metric_type: MetricType
    value: float
    unit: str = ""
    tags: Dict[str, str] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    context: Dict[str, Any] = Field(default_factory=dict)


class MetricAggregation(BaseModel):
    """Aggregated metric over a time window."""
    agent_id: str
    metric_type: MetricType
    window: AggregationWindow
    count: int = 0
    sum_value: float = 0.0
    min_value: float = float("inf")
    max_value: float = float("-inf")
    window_start: float = 0.0
    window_end: float = 0.0

    @property
    def mean(self) -> float:
        return self.sum_value / self.count if self.count > 0 else 0.0

    def add(self, value: float) -> None:
        self.count += 1
        self.sum_value += value
        if value < self.min_value:
            self.min_value = value
        if value > self.max_value:
            self.max_value = value


class MetricQuery(BaseModel):
    """Query for metrics."""
    agent_id: Optional[str] = None
    metric_type: Optional[MetricType] = None
    tags: Optional[Dict[str, str]] = None
    since: Optional[float] = None
    until: Optional[float] = None
    limit: int = 100


class MetricSummary(BaseModel):
    """Summary stats for a metric type."""
    metric_type: MetricType
    agent_id: str
    count: int
    mean: float
    min_value: float
    max_value: float
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    trend: float = 0.0  # Positive = improving, negative = degrading


# ============================================================================
# Learning strategy models
# ============================================================================


class LearningStrategy(BaseModel):
    """An adaptive behavior strategy with scoring."""
    strategy_id: str = Field(default_factory=lambda: f"strat_{uuid.uuid4().hex[:12]}")
    name: str
    description: str = ""
    agent_id: str
    domain: str = "general"  # e.g., "llm_prompting", "task_routing", "retry_logic"

    # Strategy parameters (the "knobs" to tune)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Performance tracking
    status: StrategyStatus = StrategyStatus.CANDIDATE
    karma_score: float = 50.0
    success_count: int = 0
    failure_count: int = 0
    total_applications: int = 0

    # Adaptive weights
    exploration_weight: float = 0.3  # Exploration vs exploitation
    confidence: float = 0.0          # How confident we are in this strategy

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

    @property
    def score(self) -> float:
        """Composite score: karma (40%) + success (35%) + confidence (25%)."""
        return (
            self.karma_score / 100.0 * 0.4
            + self.success_rate * 0.35
            + self.confidence * 0.25
        )


# ============================================================================
# A/B Testing models
# ============================================================================


class ExperimentVariant(BaseModel):
    """A variant in an A/B experiment."""
    variant_id: str = Field(default_factory=lambda: f"var_{uuid.uuid4().hex[:8]}")
    name: str
    strategy_id: str
    traffic_weight: float = 0.5  # 0-1, fraction of traffic

    # Results
    sample_count: int = 0
    success_count: int = 0
    total_metric_value: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.success_count / self.sample_count if self.sample_count > 0 else 0.0

    @property
    def mean_metric(self) -> float:
        return self.total_metric_value / self.sample_count if self.sample_count > 0 else 0.0


class Experiment(BaseModel):
    """An A/B experiment comparing strategy variants."""
    experiment_id: str = Field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:12]}")
    name: str
    description: str = ""
    agent_id: str
    domain: str = "general"

    # Variants
    control: ExperimentVariant
    treatment: ExperimentVariant

    # Configuration
    metric_type: MetricType = MetricType.SUCCESS_RATE
    min_samples: int = 30        # Minimum samples before concluding
    confidence_level: float = 0.95
    status: ExperimentStatus = ExperimentStatus.DRAFT

    # Results
    winner: Optional[str] = None  # variant_id of winner
    p_value: Optional[float] = None
    effect_size: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


# ============================================================================
# API models
# ============================================================================


class LearningInfo(BaseModel):
    """Module info response."""
    name: str = "Real-Time Learning Loop"
    version: str = "1.0.0"
    module: str = "learning"
    sprint: str = "7B"
    features: List[str] = Field(default_factory=lambda: [
        "performance_tracking",
        "adaptive_behavior",
        "ab_testing",
        "karma_integration",
        "online_learning",
    ])


class LearningStats(BaseModel):
    """Module statistics."""
    total_metrics_recorded: int = 0
    total_strategies: int = 0
    active_strategies: int = 0
    total_experiments: int = 0
    running_experiments: int = 0
