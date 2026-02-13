"""
Governor Manifest Shadowing Engine (Phase 2).

Evaluates shadow manifests in dry-run mode to assess safety before activation.

Key Features:
- Parallel evaluation (active vs shadow)
- Divergence tracking (mode, budget)
- Explosion detection (would-have-blocked count)
- Activation gate decision
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from loguru import logger

from app.modules.governor.manifest.schemas import (
    GovernorManifest,
    ShadowDecisionComparison,
    ShadowReport,
    ActivationGateConfig,
)
from app.modules.governor.decision.models import DecisionContext
from app.modules.governor.decision.evaluator import DecisionEvaluator


class ShadowingEngine:
    """
    Evaluates shadow manifests to assess activation safety.

    Workflow:
    1. For each decision request, evaluate both active and shadow manifests
    2. Compare decisions (mode, budget, recovery strategy)
    3. Track divergence metrics
    4. Generate shadow report
    5. Assess activation gate (safe to activate?)
    """

    def __init__(
        self,
        active_manifest: GovernorManifest,
        shadow_manifest: GovernorManifest,
        gate_config: Optional[ActivationGateConfig] = None
    ):
        """
        Initialize shadowing engine.

        Args:
            active_manifest: Currently active manifest
            shadow_manifest: Shadow manifest to evaluate
            gate_config: Activation gate configuration
        """
        self.active_manifest = active_manifest
        self.shadow_manifest = shadow_manifest
        self.gate_config = gate_config or ActivationGateConfig()

        self.active_evaluator = DecisionEvaluator(active_manifest)
        self.shadow_evaluator = DecisionEvaluator(shadow_manifest)

        # Tracking
        self.comparisons: List[ShadowDecisionComparison] = []
        self.evaluation_count = 0
        self.mode_divergence_count = 0
        self.budget_divergence_count = 0
        self.would_have_blocked = 0
        self.rule_trigger_counts: Dict[str, int] = {}

        self.shadow_start = datetime.utcnow()

    # ========================================================================
    # Shadow Evaluation
    # ========================================================================

    def evaluate_shadow(
        self,
        context: DecisionContext
    ) -> ShadowDecisionComparison:
        """
        Evaluate context against both active and shadow manifests.

        Args:
            context: Job context

        Returns:
            Comparison of decisions
        """
        # Evaluate active
        active_decision = self.active_evaluator.evaluate(
            context, shadow_mode=False
        )

        # Evaluate shadow
        shadow_decision = self.shadow_evaluator.evaluate(
            context, shadow_mode=True
        )

        # Compare decisions
        mode_delta = active_decision.mode != shadow_decision.mode
        budget_delta = self._budgets_differ(
            active_decision.budget_resolution.budget,
            shadow_decision.budget_resolution.budget
        )

        # Assess impact
        impact = self._assess_impact(
            active_decision.mode,
            shadow_decision.mode,
            mode_delta,
            budget_delta
        )

        # Track "would have blocked"
        if shadow_decision.mode == "RAIL" and active_decision.mode == "DIRECT":
            self.would_have_blocked += 1

        # Track rule triggers
        for rule_id in shadow_decision.triggered_rules:
            self.rule_trigger_counts[rule_id] = (
                self.rule_trigger_counts.get(rule_id, 0) + 1
            )

        # Create comparison
        comparison = ShadowDecisionComparison(
            mission_id=context.mission_id,
            job_id=context.job_id,
            job_type=context.job_type,
            active_mode=active_decision.mode,
            shadow_mode=shadow_decision.mode,
            active_budget=active_decision.budget_resolution.budget,
            shadow_budget=shadow_decision.budget_resolution.budget,
            mode_delta=mode_delta,
            budget_delta=budget_delta,
            impact_assessment=impact,
        )

        # Update tracking
        self.evaluation_count += 1
        if mode_delta:
            self.mode_divergence_count += 1
        if budget_delta:
            self.budget_divergence_count += 1

        # Store comparison (max 100)
        if len(self.comparisons) < 100:
            self.comparisons.append(comparison)

        logger.debug(
            f"Shadow eval: {context.job_type} - "
            f"active={active_decision.mode}, shadow={shadow_decision.mode}, "
            f"delta={mode_delta}"
        )

        return comparison

    # ========================================================================
    # Shadow Report Generation
    # ========================================================================

    def generate_report(self) -> ShadowReport:
        """
        Generate shadow evaluation report.

        Returns:
            Shadow report with activation gate decision
        """
        shadow_end = datetime.utcnow()

        # Calculate rates
        mode_divergence_rate = (
            self.mode_divergence_count / self.evaluation_count
            if self.evaluation_count > 0 else 0.0
        )
        budget_divergence_rate = (
            self.budget_divergence_count / self.evaluation_count
            if self.evaluation_count > 0 else 0.0
        )
        explosion_rate = (
            self.would_have_blocked / self.evaluation_count
            if self.evaluation_count > 0 else 0.0
        )

        # Assess activation gate
        safe_to_activate, gate_reason = self._assess_activation_gate(
            mode_divergence_rate,
            explosion_rate,
            shadow_end - self.shadow_start
        )

        report = ShadowReport(
            manifest_version=self.shadow_manifest.version,
            shadow_start=self.shadow_start,
            shadow_end=shadow_end,
            evaluation_count=self.evaluation_count,
            mode_divergence_count=self.mode_divergence_count,
            mode_divergence_rate=mode_divergence_rate,
            budget_divergence_count=self.budget_divergence_count,
            budget_divergence_rate=budget_divergence_rate,
            would_have_blocked=self.would_have_blocked,
            explosion_rate=explosion_rate,
            rule_trigger_counts=self.rule_trigger_counts,
            safe_to_activate=safe_to_activate,
            activation_gate_reason=gate_reason,
            sample_comparisons=self.comparisons,
        )

        logger.info(
            f"Shadow report generated: "
            f"version={self.shadow_manifest.version}, "
            f"evals={self.evaluation_count}, "
            f"mode_divergence={mode_divergence_rate:.2%}, "
            f"explosion={explosion_rate:.2%}, "
            f"safe={safe_to_activate}"
        )

        return report

    # ========================================================================
    # Helpers
    # ========================================================================

    def _budgets_differ(self, budget1: Any, budget2: Any) -> bool:
        """Check if budgets differ significantly."""
        # Simple comparison - differ if any field differs
        return budget1.model_dump() != budget2.model_dump()

    def _assess_impact(
        self,
        active_mode: str,
        shadow_mode: str,
        mode_delta: bool,
        budget_delta: bool
    ) -> str:
        """Assess impact of shadow decision."""
        if not mode_delta and not budget_delta:
            return "No difference - shadow matches active"

        if mode_delta:
            if shadow_mode == "RAIL" and active_mode == "DIRECT":
                return "IMPACT: Shadow would enforce governance (currently direct)"
            elif shadow_mode == "DIRECT" and active_mode == "RAIL":
                return "IMPACT: Shadow would skip governance (currently enforced)"

        if budget_delta:
            return "IMPACT: Budget limits would change"

        return "Minor difference"

    def _assess_activation_gate(
        self,
        mode_divergence_rate: float,
        explosion_rate: float,
        shadow_duration: Any
    ) -> tuple[bool, str]:
        """
        Assess if shadow manifest is safe to activate.

        Args:
            mode_divergence_rate: Rate of mode divergence
            explosion_rate: Rate of would-have-blocked
            shadow_duration: Time in shadow mode

        Returns:
            (safe_to_activate, reason)
        """
        # Check minimum evaluation count
        if self.evaluation_count < self.gate_config.min_evaluation_count:
            return False, (
                f"Insufficient evaluations: {self.evaluation_count} < "
                f"{self.gate_config.min_evaluation_count}"
            )

        # Check shadow duration
        min_duration = timedelta(hours=self.gate_config.shadow_duration_hours)
        if shadow_duration < min_duration:
            return False, (
                f"Insufficient shadow duration: {shadow_duration} < {min_duration}"
            )

        # Check mode divergence rate
        if mode_divergence_rate > self.gate_config.max_mode_divergence_rate:
            return False, (
                f"Mode divergence too high: {mode_divergence_rate:.2%} > "
                f"{self.gate_config.max_mode_divergence_rate:.2%}"
            )

        # Check explosion rate
        if explosion_rate > self.gate_config.max_explosion_rate:
            return False, (
                f"Explosion rate too high: {explosion_rate:.2%} > "
                f"{self.gate_config.max_explosion_rate:.2%}"
            )

        # All gates passed
        return True, (
            f"All gates passed: evals={self.evaluation_count}, "
            f"duration={shadow_duration}, "
            f"mode_div={mode_divergence_rate:.2%}, "
            f"explosion={explosion_rate:.2%}"
        )
