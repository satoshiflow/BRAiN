"""
Learning Service - Unified orchestration for the Real-Time Learning Loop.

Combines PerformanceTracker, AdaptiveBehavior, and ABTesting.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger

from .ab_testing import ABTesting
from .adaptive_behavior import AdaptiveBehavior
from .performance_tracker import PerformanceTracker
from .schemas import (
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
    LearningStats,
    LearningStrategy,
    MetricEntry,
    MetricQuery,
    MetricSummary,
    MetricType,
    StrategyStatus,
)

MODULE_VERSION = "1.0.0"


class LearningService:
    """Unified service for BRAIN's Real-Time Learning Loop."""

    def __init__(self, exploration_rate: float = 0.2) -> None:
        self.tracker = PerformanceTracker()
        self.behavior = AdaptiveBehavior(exploration_rate)
        self.ab_testing = ABTesting()

        logger.info("🎓 LearningService initialized (v%s)", MODULE_VERSION)

    # ------------------------------------------------------------------
    # Metrics
    # ------------------------------------------------------------------

    def record_metric(self, entry: MetricEntry) -> MetricEntry:
        return self.tracker.record(entry)

    def query_metrics(self, query: MetricQuery) -> List[MetricEntry]:
        return self.tracker.query(query)

    def summarize_metric(
        self, agent_id: str, metric_type: MetricType, since: Optional[float] = None,
    ) -> MetricSummary:
        return self.tracker.summarize(agent_id, metric_type, since)

    def get_agent_metrics(self, agent_id: str) -> Dict[str, MetricSummary]:
        return self.tracker.get_agent_metrics(agent_id)

    # ------------------------------------------------------------------
    # Strategies
    # ------------------------------------------------------------------

    def register_strategy(self, strategy: LearningStrategy) -> LearningStrategy:
        return self.behavior.register_strategy(strategy)

    def select_strategy(self, agent_id: str, domain: str) -> Optional[LearningStrategy]:
        return self.behavior.select_strategy(agent_id, domain)

    def record_outcome(
        self, strategy_id: str, success: bool, metric_value: Optional[float] = None,
    ) -> Optional[LearningStrategy]:
        return self.behavior.record_outcome(strategy_id, success, metric_value)

    def get_strategies(
        self, agent_id: str, domain: Optional[str] = None, status: Optional[StrategyStatus] = None,
    ) -> List[LearningStrategy]:
        return self.behavior.get_strategies(agent_id, domain, status)

    # ------------------------------------------------------------------
    # A/B Testing
    # ------------------------------------------------------------------

    def create_experiment(self, experiment: Experiment) -> Experiment:
        return self.ab_testing.create_experiment(experiment)

    def start_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self.ab_testing.start_experiment(experiment_id)

    def assign_variant(self, experiment_id: str) -> Optional[ExperimentVariant]:
        return self.ab_testing.assign_variant(experiment_id)

    def record_experiment_result(
        self, experiment_id: str, variant_id: str, success: bool, metric_value: float = 0.0,
    ) -> bool:
        return self.ab_testing.record_result(experiment_id, variant_id, success, metric_value)

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self.ab_testing.get_experiment(experiment_id)

    def list_experiments(
        self, agent_id: Optional[str] = None, status: Optional[ExperimentStatus] = None,
    ) -> List[Experiment]:
        return self.ab_testing.list_experiments(agent_id, status)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> LearningStats:
        t = self.tracker.stats
        b = self.behavior.stats
        a = self.ab_testing.stats
        return LearningStats(
            total_metrics_recorded=t["total_recorded"],
            total_strategies=b["total_strategies"],
            active_strategies=b["active_strategies"],
            total_experiments=a["total_experiments"],
            running_experiments=a["running"],
            total_adaptations=b["total_adaptations"],
        )


# ============================================================================
# Singleton
# ============================================================================

_service: Optional[LearningService] = None


def get_learning_service() -> LearningService:
    global _service
    if _service is None:
        _service = LearningService()
    return _service
