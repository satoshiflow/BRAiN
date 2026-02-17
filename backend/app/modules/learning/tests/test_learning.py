"""
Tests for Real-Time Learning Loop - Sprint 7B.

Covers: PerformanceTracker, AdaptiveBehavior, ABTesting, LearningService.
"""

import sys
import os
import time

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.learning.performance_tracker import PerformanceTracker
from app.modules.learning.adaptive_behavior import AdaptiveBehavior
from app.modules.learning.ab_testing import ABTesting
from app.modules.learning.service import LearningService
from app.modules.learning.schemas import (
    AggregationWindow,
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
    LearningStrategy,
    MetricEntry,
    MetricQuery,
    MetricType,
    StrategyStatus,
)


# ============================================================================
# PerformanceTracker Tests
# ============================================================================


class TestPerformanceTracker:
    def setup_method(self):
        self.tracker = PerformanceTracker()

    def test_record_metric(self):
        entry = MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=42.5, unit="ms")
        result = self.tracker.record(entry)
        assert result.metric_id == entry.metric_id
        assert self.tracker.stats["total_recorded"] == 1

    def test_record_batch(self):
        entries = [
            MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=v)
            for v in [10, 20, 30, 40, 50]
        ]
        count = self.tracker.record_batch(entries)
        assert count == 5
        assert self.tracker.stats["total_recorded"] == 5

    def test_query_by_agent(self):
        self.tracker.record(MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=10))
        self.tracker.record(MetricEntry(agent_id="a2", metric_type=MetricType.LATENCY, value=20))

        results = self.tracker.query(MetricQuery(agent_id="a1"))
        assert len(results) == 1
        assert results[0].agent_id == "a1"

    def test_query_by_type(self):
        self.tracker.record(MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=10))
        self.tracker.record(MetricEntry(agent_id="a1", metric_type=MetricType.TOKEN_USAGE, value=500))

        results = self.tracker.query(MetricQuery(agent_id="a1", metric_type=MetricType.TOKEN_USAGE))
        assert len(results) == 1
        assert results[0].value == 500

    def test_summarize(self):
        for v in [10, 20, 30, 40, 50]:
            self.tracker.record(MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=v))

        summary = self.tracker.summarize("a1", MetricType.LATENCY)
        assert summary.count == 5
        assert summary.mean == 30.0
        assert summary.min_value == 10
        assert summary.max_value == 50
        assert summary.p50 == 30.0

    def test_summarize_empty(self):
        summary = self.tracker.summarize("unknown", MetricType.LATENCY)
        assert summary.count == 0
        assert summary.mean == 0.0

    def test_trend_computation(self):
        now = time.time()
        for i in range(10):
            self.tracker.record(MetricEntry(
                agent_id="a1",
                metric_type=MetricType.SUCCESS_RATE,
                value=0.5 + i * 0.05,  # Increasing trend
                timestamp=now + i * 60,
            ))

        summary = self.tracker.summarize("a1", MetricType.SUCCESS_RATE)
        assert summary.trend > 0  # Positive trend

    def test_aggregation(self):
        self.tracker.record(MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=100))
        self.tracker.record(MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=200))

        agg = self.tracker.get_aggregation("a1", MetricType.LATENCY, AggregationWindow.MINUTE_1)
        assert agg is not None
        assert agg.count == 2
        assert agg.mean == 150.0

    def test_list_tracked_agents(self):
        self.tracker.record(MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=1))
        self.tracker.record(MetricEntry(agent_id="a2", metric_type=MetricType.LATENCY, value=2))

        agents = self.tracker.list_tracked_agents()
        assert "a1" in agents
        assert "a2" in agents


# ============================================================================
# AdaptiveBehavior Tests
# ============================================================================


class TestAdaptiveBehavior:
    def setup_method(self):
        self.behavior = AdaptiveBehavior(exploration_rate=0.0)  # Pure exploitation for deterministic tests

    def test_register_strategy(self):
        s = LearningStrategy(name="fast_retry", agent_id="a1", domain="retry_logic")
        result = self.behavior.register_strategy(s)
        assert result.strategy_id == s.strategy_id

    def test_register_duplicate(self):
        s1 = LearningStrategy(name="fast_retry", agent_id="a1", domain="retry_logic")
        s2 = LearningStrategy(name="fast_retry", agent_id="a1", domain="retry_logic")
        self.behavior.register_strategy(s1)
        result = self.behavior.register_strategy(s2)
        assert result.strategy_id == s1.strategy_id  # Returns existing

    def test_select_strategy_exploit(self):
        s1 = LearningStrategy(name="low", agent_id="a1", domain="d", karma_score=30.0)
        s2 = LearningStrategy(name="high", agent_id="a1", domain="d", karma_score=80.0)
        s1.status = StrategyStatus.ACTIVE
        s2.status = StrategyStatus.ACTIVE
        self.behavior.register_strategy(s1)
        self.behavior.register_strategy(s2)

        selected = self.behavior.select_strategy("a1", "d")
        assert selected.name == "high"  # Higher score wins in exploit mode

    def test_select_no_strategies(self):
        assert self.behavior.select_strategy("unknown", "d") is None

    def test_record_outcome_success(self):
        s = LearningStrategy(name="s1", agent_id="a1", domain="d", karma_score=50.0)
        self.behavior.register_strategy(s)

        result = self.behavior.record_outcome(s.strategy_id, success=True)
        assert result.success_count == 1
        assert result.karma_score > 50.0  # Boosted

    def test_record_outcome_failure(self):
        s = LearningStrategy(name="s1", agent_id="a1", domain="d", karma_score=50.0)
        self.behavior.register_strategy(s)

        result = self.behavior.record_outcome(s.strategy_id, success=False)
        assert result.failure_count == 1
        assert result.karma_score < 50.0  # Penalized

    def test_auto_promotion(self):
        s = LearningStrategy(name="s1", agent_id="a1", domain="d", karma_score=70.0)
        s.status = StrategyStatus.CANDIDATE
        self.behavior.register_strategy(s)

        # Simulate 10+ successful applications
        for _ in range(12):
            s.total_applications += 1
            self.behavior.record_outcome(s.strategy_id, success=True)

        assert s.status == StrategyStatus.ACTIVE  # Auto-promoted

    def test_auto_demotion(self):
        s = LearningStrategy(name="bad", agent_id="a1", domain="d", karma_score=25.0)
        s.status = StrategyStatus.ACTIVE
        self.behavior.register_strategy(s)

        for _ in range(15):
            s.total_applications += 1
            self.behavior.record_outcome(s.strategy_id, success=False)

        assert s.status == StrategyStatus.DEMOTED

    def test_manual_promote(self):
        s = LearningStrategy(name="s1", agent_id="a1", domain="d")
        self.behavior.register_strategy(s)
        result = self.behavior.promote_strategy(s.strategy_id)
        assert result.status == StrategyStatus.PROMOTED

    def test_stats(self):
        stats = self.behavior.stats
        assert stats["total_strategies"] == 0
        assert stats["exploration_rate"] == 0.0


# ============================================================================
# ABTesting Tests
# ============================================================================


class TestABTesting:
    def setup_method(self):
        self.ab = ABTesting()

    def _make_experiment(self) -> Experiment:
        return Experiment(
            name="Test Prompt Format",
            agent_id="a1",
            control=ExperimentVariant(name="control", strategy_id="s1", traffic_weight=0.5),
            treatment=ExperimentVariant(name="treatment", strategy_id="s2", traffic_weight=0.5),
            min_samples=5,
        )

    def test_create_experiment(self):
        exp = self._make_experiment()
        result = self.ab.create_experiment(exp)
        assert result.status == ExperimentStatus.DRAFT

    def test_start_experiment(self):
        exp = self._make_experiment()
        self.ab.create_experiment(exp)
        result = self.ab.start_experiment(exp.experiment_id)
        assert result.status == ExperimentStatus.RUNNING

    def test_assign_variant(self):
        exp = self._make_experiment()
        self.ab.create_experiment(exp)
        self.ab.start_experiment(exp.experiment_id)

        variant = self.ab.assign_variant(exp.experiment_id)
        assert variant is not None
        assert variant.variant_id in (exp.control.variant_id, exp.treatment.variant_id)

    def test_record_result(self):
        exp = self._make_experiment()
        self.ab.create_experiment(exp)
        self.ab.start_experiment(exp.experiment_id)

        ok = self.ab.record_result(exp.experiment_id, exp.control.variant_id, success=True)
        assert ok is True
        assert exp.control.sample_count == 1
        assert exp.control.success_count == 1

    def test_experiment_auto_conclude(self):
        exp = self._make_experiment()
        exp.min_samples = 5
        self.ab.create_experiment(exp)
        self.ab.start_experiment(exp.experiment_id)

        # Control: 2/5 success (40%)
        for i in range(5):
            self.ab.record_result(exp.experiment_id, exp.control.variant_id, success=(i < 2))

        # Treatment: 5/5 success (100%)
        for _ in range(5):
            self.ab.record_result(exp.experiment_id, exp.treatment.variant_id, success=True)

        # Should have auto-evaluated
        assert exp.p_value is not None
        if exp.status == ExperimentStatus.COMPLETED:
            assert exp.winner == exp.treatment.variant_id

    def test_pause_experiment(self):
        exp = self._make_experiment()
        self.ab.create_experiment(exp)
        self.ab.start_experiment(exp.experiment_id)
        result = self.ab.pause_experiment(exp.experiment_id)
        assert result.status == ExperimentStatus.PAUSED

    def test_cancel_experiment(self):
        exp = self._make_experiment()
        self.ab.create_experiment(exp)
        result = self.ab.cancel_experiment(exp.experiment_id)
        assert result.status == ExperimentStatus.CANCELLED

    def test_list_experiments(self):
        exp = self._make_experiment()
        self.ab.create_experiment(exp)
        exps = self.ab.list_experiments(agent_id="a1")
        assert len(exps) == 1

    def test_stats(self):
        stats = self.ab.stats
        assert stats["total_experiments"] == 0


# ============================================================================
# LearningService Integration Tests
# ============================================================================


class TestLearningService:
    def setup_method(self):
        self.svc = LearningService(exploration_rate=0.0)

    def test_metric_and_strategy_workflow(self):
        # Record metrics
        self.svc.record_metric(MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=100))
        self.svc.record_metric(MetricEntry(agent_id="a1", metric_type=MetricType.LATENCY, value=200))

        summary = self.svc.summarize_metric("a1", MetricType.LATENCY)
        assert summary.count == 2
        assert summary.mean == 150.0

        # Register and select strategy
        s = LearningStrategy(name="aggressive_cache", agent_id="a1", domain="caching")
        s.status = StrategyStatus.ACTIVE
        self.svc.register_strategy(s)

        selected = self.svc.select_strategy("a1", "caching")
        assert selected.name == "aggressive_cache"

        # Record outcome
        result = self.svc.record_outcome(s.strategy_id, success=True)
        assert result.success_count == 1

    def test_experiment_workflow(self):
        exp = Experiment(
            name="Cache Strategy Test",
            agent_id="a1",
            control=ExperimentVariant(name="no_cache", strategy_id="s1"),
            treatment=ExperimentVariant(name="with_cache", strategy_id="s2"),
            min_samples=3,
        )
        self.svc.create_experiment(exp)
        self.svc.start_experiment(exp.experiment_id)

        variant = self.svc.assign_variant(exp.experiment_id)
        assert variant is not None

        ok = self.svc.record_experiment_result(exp.experiment_id, variant.variant_id, success=True)
        assert ok is True

    def test_stats(self):
        stats = self.svc.get_stats()
        assert stats.total_metrics_recorded == 0
        assert stats.total_strategies == 0
        assert stats.total_experiments == 0
