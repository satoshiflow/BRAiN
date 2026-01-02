"""
Constraint Reduction Engine (Phase 2b)

Applies manifest-defined reductions to base constraints with MONOTONICITY guarantee.

Key Principles:
- Reductions can only REDUCE constraints, never expand
- Pure functions (deterministic, no side effects)
- Validation before application
- Clear error messages on monotonicity violations

Author: Governor v1 System (Phase 2b)
Version: 2b.1
Created: 2026-01-02
"""

from __future__ import annotations

import logging
from typing import Optional

from backend.brain.governor.constraints.schema import (
    BudgetConstraints,
    CapabilityConstraints,
    EffectiveConstraints,
    LifecycleConstraints,
    RuntimeConstraints,
)
from backend.brain.governor.manifests.schema import ReductionSpec


logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class MonotonicityViolationError(Exception):
    """Raised when a reduction would expand constraints (violates monotonicity)."""
    pass


class InvalidReductionError(Exception):
    """Raised when a reduction specification is invalid."""
    pass


# ============================================================================
# Constraint Reducer
# ============================================================================

class ConstraintReducer:
    """
    Applies manifest-defined reductions to base constraints.

    Responsibilities:
    - Parse reduction specifications (percentages, absolutes, keywords)
    - Apply reductions to each constraint category
    - Validate monotonicity (reductions only reduce, never expand)
    - Provide clear error messages

    Example:
        >>> reducer = ConstraintReducer()
        >>> base = get_default_constraints(AgentType.WORKER)
        >>> spec = ReductionSpec(max_llm_calls_per_day="-30%")
        >>> reduced = reducer.reduce(base, spec)
        >>> assert reduced.budget.max_llm_calls_per_day < base.budget.max_llm_calls_per_day
    """

    def reduce(
        self,
        base: EffectiveConstraints,
        spec: ReductionSpec
    ) -> EffectiveConstraints:
        """
        Apply reduction specification to base constraints.

        Args:
            base: Base EffectiveConstraints (from defaults or previous reduction)
            spec: ReductionSpec from manifest

        Returns:
            Reduced EffectiveConstraints

        Raises:
            MonotonicityViolationError: If reduction would expand constraints
            InvalidReductionError: If reduction spec is invalid

        Example:
            >>> spec = ReductionSpec(max_llm_calls_per_day="-50%", parallelism="-75%")
            >>> reduced = reducer.reduce(base, spec)
        """
        # Start with base constraints (immutable)
        reduced_budget = self._reduce_budget(base.budget, spec)
        reduced_capabilities = self._reduce_capabilities(base.capabilities, spec)
        reduced_runtime = self._reduce_runtime(base.runtime, spec)
        reduced_lifecycle = self._reduce_lifecycle(base.lifecycle, spec)

        # Locks are NOT reduced (they are absolute)
        reduced_locks = base.locks.model_copy()

        # Construct reduced constraints
        reduced = EffectiveConstraints(
            budget=reduced_budget,
            capabilities=reduced_capabilities,
            runtime=reduced_runtime,
            lifecycle=reduced_lifecycle,
            locks=reduced_locks
        )

        # Validate monotonicity
        self._validate_monotonicity(base, reduced)

        return reduced

    # ------------------------------------------------------------------------
    # Budget Reductions
    # ------------------------------------------------------------------------

    def _reduce_budget(
        self,
        base: BudgetConstraints,
        spec: ReductionSpec
    ) -> BudgetConstraints:
        """
        Reduce budget constraints.

        Fields:
        - max_credits_per_mission
        - max_llm_calls_per_day
        - max_llm_tokens_per_call
        """
        budget_dict = base.model_dump()

        # max_credits_per_mission
        if spec.max_credits_per_mission is not None:
            budget_dict["max_credits_per_mission"] = self._apply_reduction(
                base.max_credits_per_mission,
                spec.max_credits_per_mission,
                field_name="max_credits_per_mission"
            )

        # max_llm_calls_per_day
        if spec.max_llm_calls_per_day is not None:
            budget_dict["max_llm_calls_per_day"] = self._apply_reduction(
                base.max_llm_calls_per_day,
                spec.max_llm_calls_per_day,
                field_name="max_llm_calls_per_day"
            )

        # max_llm_tokens_per_call
        if spec.max_llm_tokens_per_call is not None:
            budget_dict["max_llm_tokens_per_call"] = self._apply_reduction(
                base.max_llm_tokens_per_call,
                spec.max_llm_tokens_per_call,
                field_name="max_llm_tokens_per_call"
            )

        return BudgetConstraints(**budget_dict)

    # ------------------------------------------------------------------------
    # Capability Reductions
    # ------------------------------------------------------------------------

    def _reduce_capabilities(
        self,
        base: CapabilityConstraints,
        spec: ReductionSpec
    ) -> CapabilityConstraints:
        """
        Reduce capability constraints.

        Fields:
        - network_access (enum: full → restricted → none)
        """
        cap_dict = base.model_dump()

        # network_access (special enum reduction)
        if spec.network_access is not None:
            cap_dict["network_access"] = self._reduce_network_access(
                base.network_access,
                spec.network_access
            )

        return CapabilityConstraints(**cap_dict)

    def _reduce_network_access(
        self,
        base: str,
        reduction: str
    ) -> str:
        """
        Reduce network access (enum hierarchy).

        Hierarchy: full > restricted > none

        Args:
            base: Current network access level
            reduction: Target level or keyword

        Returns:
            Reduced network access level

        Example:
            >>> _reduce_network_access("full", "restricted")  # → "restricted"
            >>> _reduce_network_access("restricted", "disable")  # → "none"
        """
        hierarchy = {"none": 0, "restricted": 1, "full": 2}

        # Handle keywords
        if reduction == "disable":
            reduction = "none"

        # Validate reduction is in hierarchy
        if reduction not in hierarchy:
            raise InvalidReductionError(
                f"Invalid network_access reduction: {reduction}. "
                f"Must be one of: {list(hierarchy.keys())} or 'disable'"
            )

        base_level = hierarchy[base]
        reduction_level = hierarchy[reduction]

        # Monotonicity check
        if reduction_level > base_level:
            raise MonotonicityViolationError(
                f"Cannot expand network_access from '{base}' to '{reduction}' "
                f"(monotonicity violation)"
            )

        return reduction

    # ------------------------------------------------------------------------
    # Runtime Reductions
    # ------------------------------------------------------------------------

    def _reduce_runtime(
        self,
        base: RuntimeConstraints,
        spec: ReductionSpec
    ) -> RuntimeConstraints:
        """
        Reduce runtime constraints.

        Fields:
        - parallelism (int or "single")
        - max_lifetime_seconds
        """
        runtime_dict = base.model_dump()

        # parallelism
        if spec.parallelism is not None:
            runtime_dict["parallelism"] = self._reduce_parallelism(
                base.parallelism,
                spec.parallelism
            )

        # max_lifetime_seconds
        if spec.max_lifetime_seconds is not None:
            runtime_dict["max_lifetime_seconds"] = self._apply_reduction(
                base.max_lifetime_seconds,
                spec.max_lifetime_seconds,
                field_name="max_lifetime_seconds"
            )

        return RuntimeConstraints(**runtime_dict)

    def _reduce_parallelism(
        self,
        base: int,
        reduction: str
    ) -> int:
        """
        Reduce parallelism.

        Args:
            base: Current parallelism (int)
            reduction: Reduction spec (percentage, absolute, or "single")

        Returns:
            Reduced parallelism (int)

        Example:
            >>> _reduce_parallelism(10, "-50%")  # → 5
            >>> _reduce_parallelism(10, "single")  # → 1
        """
        # Handle keyword "single"
        if reduction == "single":
            return 1

        # Apply standard reduction
        return self._apply_reduction(
            base,
            reduction,
            field_name="parallelism"
        )

    # ------------------------------------------------------------------------
    # Lifecycle Reductions
    # ------------------------------------------------------------------------

    def _reduce_lifecycle(
        self,
        base: LifecycleConstraints,
        spec: ReductionSpec
    ) -> LifecycleConstraints:
        """
        Reduce lifecycle constraints.

        Currently no lifecycle fields are reducible in Phase 2b.
        Future: initial_status, auto_suspend, etc.
        """
        # No lifecycle reductions in Phase 2b
        return base.model_copy()

    # ------------------------------------------------------------------------
    # Generic Reduction Application
    # ------------------------------------------------------------------------

    def _apply_reduction(
        self,
        base_value: int,
        reduction: str,
        field_name: str
    ) -> int:
        """
        Apply reduction to a numeric value.

        Handles:
        - Percentages: "-30%" → reduce by 30%
        - Absolutes: "100" → set to 100 (if less than base)

        Args:
            base_value: Current value
            reduction: Reduction spec (percentage or absolute)
            field_name: Field name (for error messages)

        Returns:
            Reduced value

        Raises:
            MonotonicityViolationError: If reduction would increase value
            InvalidReductionError: If reduction spec is invalid

        Example:
            >>> _apply_reduction(1000, "-30%", "max_credits")  # → 700
            >>> _apply_reduction(1000, "500", "max_credits")  # → 500
            >>> _apply_reduction(1000, "1500", "max_credits")  # → MonotonicityViolationError
        """
        # Percentage reduction
        if reduction.endswith("%"):
            try:
                percentage = float(reduction.rstrip("%"))
            except ValueError:
                raise InvalidReductionError(
                    f"Invalid percentage reduction for {field_name}: {reduction}"
                )

            # Must be negative (reduction)
            if percentage >= 0:
                raise InvalidReductionError(
                    f"Percentage reduction must be negative (e.g., '-30%'), got: {reduction}"
                )

            # Calculate reduced value
            multiplier = 1 + (percentage / 100)
            reduced_value = int(base_value * multiplier)

            return reduced_value

        # Absolute reduction
        else:
            try:
                absolute_value = int(reduction)
            except ValueError:
                raise InvalidReductionError(
                    f"Invalid absolute reduction for {field_name}: {reduction}. "
                    f"Must be integer or percentage (e.g., '-30%')"
                )

            # Monotonicity check
            if absolute_value > base_value:
                raise MonotonicityViolationError(
                    f"Cannot expand {field_name} from {base_value} to {absolute_value} "
                    f"(monotonicity violation)"
                )

            return absolute_value

    # ------------------------------------------------------------------------
    # Monotonicity Validation
    # ------------------------------------------------------------------------

    def _validate_monotonicity(
        self,
        base: EffectiveConstraints,
        reduced: EffectiveConstraints
    ) -> None:
        """
        Validate that all reductions are monotonic (only reduce, never expand).

        Args:
            base: Base constraints
            reduced: Reduced constraints

        Raises:
            MonotonicityViolationError: If any constraint was expanded

        Example:
            >>> _validate_monotonicity(base, reduced)  # No error if valid
        """
        violations = []

        # Check budget constraints
        if reduced.budget.max_credits_per_mission > base.budget.max_credits_per_mission:
            violations.append(
                f"max_credits_per_mission expanded: {base.budget.max_credits_per_mission} → {reduced.budget.max_credits_per_mission}"
            )

        if reduced.budget.max_llm_calls_per_day > base.budget.max_llm_calls_per_day:
            violations.append(
                f"max_llm_calls_per_day expanded: {base.budget.max_llm_calls_per_day} → {reduced.budget.max_llm_calls_per_day}"
            )

        if reduced.budget.max_llm_tokens_per_call > base.budget.max_llm_tokens_per_call:
            violations.append(
                f"max_llm_tokens_per_call expanded: {base.budget.max_llm_tokens_per_call} → {reduced.budget.max_llm_tokens_per_call}"
            )

        # Check capability constraints (network_access hierarchy)
        network_hierarchy = {"none": 0, "restricted": 1, "full": 2}
        base_network_level = network_hierarchy[base.capabilities.network_access]
        reduced_network_level = network_hierarchy[reduced.capabilities.network_access]

        if reduced_network_level > base_network_level:
            violations.append(
                f"network_access expanded: {base.capabilities.network_access} → {reduced.capabilities.network_access}"
            )

        # Check runtime constraints
        if reduced.runtime.parallelism > base.runtime.parallelism:
            violations.append(
                f"parallelism expanded: {base.runtime.parallelism} → {reduced.runtime.parallelism}"
            )

        if reduced.runtime.max_lifetime_seconds > base.runtime.max_lifetime_seconds:
            violations.append(
                f"max_lifetime_seconds expanded: {base.runtime.max_lifetime_seconds} → {reduced.runtime.max_lifetime_seconds}"
            )

        # Raise if violations found
        if violations:
            raise MonotonicityViolationError(
                f"Monotonicity violations detected:\n" + "\n".join(f"  - {v}" for v in violations)
            )


# ============================================================================
# Convenience Function
# ============================================================================

def apply_reduction(
    base: EffectiveConstraints,
    spec: ReductionSpec
) -> EffectiveConstraints:
    """
    Convenience function to apply reduction without creating ConstraintReducer instance.

    Args:
        base: Base EffectiveConstraints
        spec: ReductionSpec from manifest

    Returns:
        Reduced EffectiveConstraints

    Example:
        >>> reduced = apply_reduction(base, spec)
    """
    reducer = ConstraintReducer()
    return reducer.reduce(base, spec)
