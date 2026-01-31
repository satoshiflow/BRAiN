"""
A/B Testing - Experiment framework with statistical evaluation.

Compares two strategy variants (control vs treatment) by splitting
traffic and measuring outcomes. Uses a Z-test for proportions to
determine statistical significance.

Workflow:
    1. Create experiment with control + treatment variants
    2. Start experiment (status → RUNNING)
    3. Record samples via assign_variant + record_result
    4. Evaluate when min_samples reached
    5. Auto-conclude or manually conclude
"""

from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from .schemas import (
    Experiment,
    ExperimentStatus,
    ExperimentVariant,
)


class ABTesting:
    """
    A/B experiment manager.

    Runs experiments that compare control vs treatment variants
    using statistical testing.
    """

    def __init__(self) -> None:
        self._experiments: Dict[str, Experiment] = {}
        self._total_samples = 0

        logger.info("🧪 ABTesting framework initialized")

    # ------------------------------------------------------------------
    # Experiment lifecycle
    # ------------------------------------------------------------------

    def create_experiment(self, experiment: Experiment) -> Experiment:
        """Create a new A/B experiment."""
        self._experiments[experiment.experiment_id] = experiment
        logger.info("🧪 Experiment created: '%s' (%s)", experiment.name, experiment.experiment_id)
        return experiment

    def start_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Start an experiment (DRAFT → RUNNING)."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.DRAFT:
            return None
        exp.status = ExperimentStatus.RUNNING
        logger.info("▶️ Experiment started: '%s'", exp.name)
        return exp

    def pause_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Pause a running experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return None
        exp.status = ExperimentStatus.PAUSED
        return exp

    def cancel_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Cancel an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        exp.status = ExperimentStatus.CANCELLED
        return exp

    # ------------------------------------------------------------------
    # Traffic assignment
    # ------------------------------------------------------------------

    def assign_variant(self, experiment_id: str) -> Optional[ExperimentVariant]:
        """
        Assign a variant to a new sample using traffic weights.

        Returns the assigned variant, or None if experiment not running.
        """
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return None

        # Weighted random assignment
        total_weight = exp.control.traffic_weight + exp.treatment.traffic_weight
        if random.random() < (exp.control.traffic_weight / total_weight):
            return exp.control
        return exp.treatment

    # ------------------------------------------------------------------
    # Result recording
    # ------------------------------------------------------------------

    def record_result(
        self,
        experiment_id: str,
        variant_id: str,
        success: bool,
        metric_value: float = 0.0,
    ) -> bool:
        """Record a result for a variant in an experiment."""
        exp = self._experiments.get(experiment_id)
        if not exp or exp.status != ExperimentStatus.RUNNING:
            return False

        variant = None
        if exp.control.variant_id == variant_id:
            variant = exp.control
        elif exp.treatment.variant_id == variant_id:
            variant = exp.treatment

        if not variant:
            return False

        variant.sample_count += 1
        if success:
            variant.success_count += 1
        variant.total_metric_value += metric_value
        self._total_samples += 1

        # Auto-evaluate if both variants have min samples
        if (exp.control.sample_count >= exp.min_samples
                and exp.treatment.sample_count >= exp.min_samples):
            self._evaluate(exp)

        return True

    # ------------------------------------------------------------------
    # Statistical evaluation
    # ------------------------------------------------------------------

    def _evaluate(self, exp: Experiment) -> None:
        """Evaluate experiment using Z-test for proportions."""
        c = exp.control
        t = exp.treatment

        if c.sample_count == 0 or t.sample_count == 0:
            return

        p_c = c.success_rate
        p_t = t.success_rate
        n_c = c.sample_count
        n_t = t.sample_count

        # Pooled proportion
        p_pool = (c.success_count + t.success_count) / (n_c + n_t)

        if p_pool == 0 or p_pool == 1:
            return  # Can't compute z-score

        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_c + 1 / n_t))
        if se == 0:
            return

        # Z-score
        z = (p_t - p_c) / se

        # Two-tailed p-value approximation
        p_value = 2 * (1 - self._normal_cdf(abs(z)))

        exp.p_value = round(p_value, 6)
        exp.effect_size = round(p_t - p_c, 4)

        # Significance check
        alpha = 1 - exp.confidence_level
        if p_value < alpha:
            # Statistically significant
            if p_t > p_c:
                exp.winner = t.variant_id
            else:
                exp.winner = c.variant_id

            exp.status = ExperimentStatus.COMPLETED
            exp.completed_at = datetime.utcnow()
            logger.info(
                "🏆 Experiment '%s' completed: winner=%s (p=%.4f, effect=%.4f)",
                exp.name,
                "treatment" if exp.winner == t.variant_id else "control",
                p_value,
                exp.effect_size,
            )

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Approximate standard normal CDF using error function."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def evaluate_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Manually trigger evaluation."""
        exp = self._experiments.get(experiment_id)
        if not exp:
            return None
        self._evaluate(exp)
        return exp

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        return self._experiments.get(experiment_id)

    def list_experiments(
        self,
        agent_id: Optional[str] = None,
        status: Optional[ExperimentStatus] = None,
    ) -> List[Experiment]:
        exps = list(self._experiments.values())
        if agent_id:
            exps = [e for e in exps if e.agent_id == agent_id]
        if status:
            exps = [e for e in exps if e.status == status]
        return exps

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    @property
    def stats(self) -> Dict:
        running = sum(1 for e in self._experiments.values() if e.status == ExperimentStatus.RUNNING)
        completed = sum(1 for e in self._experiments.values() if e.status == ExperimentStatus.COMPLETED)
        return {
            "total_experiments": len(self._experiments),
            "running": running,
            "completed": completed,
            "total_samples": self._total_samples,
        }
