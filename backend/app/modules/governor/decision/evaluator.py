"""
Governor Decision Evaluator (Phase 2).

Deterministic rule evaluation engine for governance decisions.

Key Principles:
- Deterministic: Same inputs → same outputs
- Priority-based: Lower priority number = higher precedence
- OR/AND logic: Supports when.any[] and when.all[]
- Fallback: If no rule matches, use defaults
- Traceable: All matched rules logged in decision
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Tuple
from loguru import logger

from backend.app.modules.governor.manifest.schemas import (
    GovernorManifest,
    ManifestRule,
    RuleCondition,
    Budget,
    RiskClass,
)
from backend.app.modules.governor.decision.models import (
    DecisionContext,
    BudgetResolution,
    RecoveryStrategy,
    GovernorDecision,
)
from backend.app.modules.neurorail.errors import (
    NeuroRailError,
    NeuroRailErrorCode,
    DecisionBudgetResolutionError,
)


class DecisionEvaluator:
    """
    Evaluates manifest rules to produce governance decisions.

    Evaluation Process:
    1. Sort rules by priority (ascending - lower = higher priority)
    2. Evaluate each rule condition against job context
    3. First matching rule wins
    4. If no rule matches, use manifest defaults
    5. Resolve budget (rule override, job override, risk class multiplier)
    6. Determine recovery strategy
    7. Create immutable decision record
    """

    def __init__(self, manifest: GovernorManifest):
        """
        Initialize evaluator with manifest.

        Args:
            manifest: Active manifest to evaluate against
        """
        self.manifest = manifest
        # Sort rules by priority (ascending)
        self.sorted_rules = sorted(manifest.rules, key=lambda r: r.priority)

    # ========================================================================
    # Main Evaluation
    # ========================================================================

    def evaluate(
        self,
        context: DecisionContext,
        shadow_mode: bool = False
    ) -> GovernorDecision:
        """
        Evaluate decision for job context.

        Args:
            context: Job context for decision
            shadow_mode: Whether decision is in shadow mode

        Returns:
            Immutable governance decision

        Raises:
            DecisionBudgetResolutionError: If budget resolution fails
        """
        logger.debug(
            f"Evaluating decision for {context.job_type} "
            f"(manifest: {self.manifest.version})"
        )

        # 1. Find matching rule (first match wins)
        matched_rule, matched_rule_ids = self._find_matching_rule(context)

        # 2. Determine mode and recovery strategy
        if matched_rule:
            mode = matched_rule.mode
            recovery_strategy = (
                matched_rule.recovery_strategy
                or self._get_risk_class_recovery(context.risk_class)
                or RecoveryStrategy.RETRY
            )
            reason = matched_rule.reason
        else:
            # Fallback to defaults
            mode = "DIRECT"  # Default: no governance overhead
            recovery_strategy = RecoveryStrategy.RETRY
            reason = "No matching rule - using manifest defaults"
            logger.debug(f"No rule matched for {context.job_type}, using defaults")

        # 3. Resolve budget
        budget_resolution = self._resolve_budget(context, matched_rule)

        # 4. Determine immune alert requirement
        immune_alert_required = self._should_alert_immune(
            mode, recovery_strategy, context
        )

        # 5. Create decision
        decision = GovernorDecision(
            mission_id=context.mission_id,
            job_id=context.job_id,
            job_type=context.job_type,
            mode=mode,
            budget_resolution=budget_resolution,
            recovery_strategy=recovery_strategy,
            manifest_id=self.manifest.manifest_id,
            manifest_version=self.manifest.version,
            triggered_rules=matched_rule_ids,
            reason=reason,
            shadow_mode=shadow_mode,
            evidence={
                "environment": context.environment,
                "risk_class": context.risk_class,
                "idempotent": context.idempotent,
                "external_dependency": context.external_dependency,
                "uses_personal_data": context.uses_personal_data,
            },
            immune_alert_required=immune_alert_required,
            health_impact=self._assess_health_impact(mode, recovery_strategy),
        )

        logger.info(
            f"Decision: mode={mode}, recovery={recovery_strategy}, "
            f"budget_source={budget_resolution.source}, "
            f"rules={matched_rule_ids}, shadow={shadow_mode}"
        )

        return decision

    # ========================================================================
    # Rule Matching
    # ========================================================================

    def _find_matching_rule(
        self,
        context: DecisionContext
    ) -> Tuple[Optional[ManifestRule], List[str]]:
        """
        Find first matching rule by priority.

        Args:
            context: Job context

        Returns:
            (matched_rule, matched_rule_ids)
        """
        matched_rule_ids = []

        for rule in self.sorted_rules:
            if not rule.enabled:
                continue

            if self._evaluate_condition(rule.when, context):
                matched_rule_ids.append(rule.rule_id)
                logger.debug(
                    f"Rule matched: {rule.rule_id} (priority={rule.priority})"
                )
                return rule, matched_rule_ids

        return None, matched_rule_ids

    def _evaluate_condition(
        self,
        condition: RuleCondition,
        context: DecisionContext
    ) -> bool:
        """
        Evaluate rule condition against context.

        Supports:
        - Direct field matches
        - OR-logic (when.any[])
        - AND-logic (when.all[])

        Args:
            condition: Rule condition
            context: Job context

        Returns:
            True if condition matches
        """
        # Handle OR-logic
        if condition.any:
            for sub_condition in condition.any:
                if self._matches_simple_condition(sub_condition, context):
                    return True
            return False

        # Handle AND-logic
        if condition.all:
            for sub_condition in condition.all:
                if not self._matches_simple_condition(sub_condition, context):
                    return False
            return True

        # Handle simple condition
        return self._matches_simple_condition(
            condition.model_dump(exclude_none=True), context
        )

    def _matches_simple_condition(
        self,
        condition_dict: Dict[str, Any],
        context: DecisionContext
    ) -> bool:
        """
        Check if simple condition matches context.

        Args:
            condition_dict: Condition fields
            context: Job context

        Returns:
            True if all fields match
        """
        context_dict = context.model_dump(exclude_none=True)

        for field, expected_value in condition_dict.items():
            # Skip meta fields
            if field in ["any", "all", "extra_fields"]:
                continue

            # Get actual value from context
            actual_value = context_dict.get(field)

            # Check match
            if actual_value != expected_value:
                return False

        return True

    # ========================================================================
    # Budget Resolution
    # ========================================================================

    def _resolve_budget(
        self,
        context: DecisionContext,
        matched_rule: Optional[ManifestRule]
    ) -> BudgetResolution:
        """
        Resolve budget from manifest rules.

        Resolution order (first match wins):
        1. Job-specific override (manifest.job_overrides[job_type])
        2. Matched rule budget override
        3. Manifest defaults

        Then apply risk class multiplier if applicable.

        Args:
            context: Job context
            matched_rule: Matched rule (if any)

        Returns:
            Budget resolution with source tracking

        Raises:
            DecisionBudgetResolutionError: If resolution fails
        """
        try:
            budget: Budget
            source: str
            rule_id: Optional[str] = None
            multiplier: Optional[float] = None

            # 1. Check job-specific override
            if context.job_type in self.manifest.job_overrides:
                budget = self.manifest.job_overrides[context.job_type]
                source = "job_override"
                logger.debug(f"Budget from job override: {context.job_type}")

            # 2. Check matched rule override
            elif matched_rule and matched_rule.budget_override:
                budget = matched_rule.budget_override
                source = "rule_override"
                rule_id = matched_rule.rule_id
                logger.debug(f"Budget from rule override: {rule_id}")

            # 3. Use manifest defaults
            else:
                budget = self.manifest.budget_defaults
                source = "defaults"
                logger.debug("Budget from manifest defaults")

            # Apply risk class multiplier
            if context.risk_class and context.risk_class in self.manifest.risk_classes:
                risk_class = self.manifest.risk_classes[context.risk_class]
                multiplier = risk_class.budget_multiplier

                if multiplier != 1.0:
                    budget = self._apply_budget_multiplier(budget, multiplier)
                    logger.debug(
                        f"Applied risk class multiplier: {multiplier} "
                        f"({context.risk_class})"
                    )

            return BudgetResolution(
                budget=budget,
                source=source,
                rule_id=rule_id,
                multiplier_applied=multiplier,
                details={
                    "job_type": context.job_type,
                    "risk_class": context.risk_class,
                }
            )

        except Exception as e:
            logger.error(f"Budget resolution failed: {e}")
            raise DecisionBudgetResolutionError(
                job_type=context.job_type,
                reason=str(e),
            ) from e

    def _apply_budget_multiplier(
        self,
        budget: Budget,
        multiplier: float
    ) -> Budget:
        """
        Apply multiplier to budget limits.

        Args:
            budget: Original budget
            multiplier: Multiplier factor

        Returns:
            New budget with multiplied limits
        """
        return Budget(
            timeout_ms=int(budget.timeout_ms * multiplier) if budget.timeout_ms else None,
            max_retries=budget.max_retries,  # Retries not multiplied
            max_parallel_attempts=(
                int(budget.max_parallel_attempts * multiplier)
                if budget.max_parallel_attempts else None
            ),
            max_global_parallel=(
                int(budget.max_global_parallel * multiplier)
                if budget.max_global_parallel else None
            ),
            max_llm_tokens=(
                int(budget.max_llm_tokens * multiplier)
                if budget.max_llm_tokens else None
            ),
            max_cost_credits=(
                budget.max_cost_credits * multiplier
                if budget.max_cost_credits else None
            ),
            grace_period_ms=budget.grace_period_ms,  # Grace period not multiplied
        )

    # ========================================================================
    # Recovery Strategy
    # ========================================================================

    def _get_risk_class_recovery(
        self,
        risk_class_name: Optional[str]
    ) -> Optional[RecoveryStrategy]:
        """
        Get default recovery strategy from risk class.

        Args:
            risk_class_name: Risk class name

        Returns:
            Recovery strategy from risk class, or None
        """
        if not risk_class_name:
            return None

        risk_class = self.manifest.risk_classes.get(risk_class_name)
        if not risk_class:
            return None

        return risk_class.recovery_strategy

    # ========================================================================
    # Health & Immune Integration
    # ========================================================================

    def _should_alert_immune(
        self,
        mode: str,
        recovery_strategy: RecoveryStrategy,
        context: DecisionContext
    ) -> bool:
        """
        Determine if immune system should be alerted.

        Criteria:
        - MANUAL_CONFIRM recovery strategy
        - Production environment with RAIL mode
        - Personal data processing

        Args:
            mode: Execution mode
            recovery_strategy: Recovery strategy
            context: Job context

        Returns:
            True if immune alert required
        """
        # Always alert on manual confirm
        if recovery_strategy == RecoveryStrategy.MANUAL_CONFIRM:
            return True

        # Alert on production RAIL mode
        if mode == "RAIL" and context.environment == "production":
            return True

        # Alert on personal data processing
        if context.uses_personal_data:
            return True

        return False

    def _assess_health_impact(
        self,
        mode: str,
        recovery_strategy: RecoveryStrategy
    ) -> str:
        """
        Assess expected health impact for monitoring.

        Args:
            mode: Execution mode
            recovery_strategy: Recovery strategy

        Returns:
            Health impact level
        """
        if recovery_strategy == RecoveryStrategy.MANUAL_CONFIRM:
            return "high"  # Requires human intervention

        if mode == "RAIL":
            return "medium"  # Governance overhead

        return "low"  # Direct execution, minimal overhead
