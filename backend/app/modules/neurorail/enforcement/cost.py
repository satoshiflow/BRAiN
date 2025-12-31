"""
Budget Cost Tracker (Phase 2 Enforcement).

Tracks resource consumption (LLM tokens, API calls, cost credits).
Integrates with immune system and Prometheus metrics.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from loguru import logger

from backend.app.modules.governor.manifest.schemas import Budget
from backend.app.modules.neurorail.errors import (
    BudgetCostExceededError,
    NeuroRailErrorCode,
    should_alert_immune,
)


@dataclass
class CostAccumulator:
    """
    Accumulator for tracking resource consumption.

    Tracks:
    - LLM tokens (prompt + completion)
    - API calls
    - Cost credits (arbitrary unit)
    """
    llm_tokens_used: int = 0
    llm_prompt_tokens: int = 0
    llm_completion_tokens: int = 0
    api_calls_made: int = 0
    cost_credits_used: float = 0.0

    def add_llm_tokens(self, prompt_tokens: int, completion_tokens: int):
        """Add LLM token usage."""
        self.llm_prompt_tokens += prompt_tokens
        self.llm_completion_tokens += completion_tokens
        self.llm_tokens_used = self.llm_prompt_tokens + self.llm_completion_tokens

    def add_api_call(self, cost_credits: float = 0.0):
        """Add API call."""
        self.api_calls_made += 1
        self.cost_credits_used += cost_credits

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "llm_tokens_used": self.llm_tokens_used,
            "llm_prompt_tokens": self.llm_prompt_tokens,
            "llm_completion_tokens": self.llm_completion_tokens,
            "api_calls_made": self.api_calls_made,
            "cost_credits_used": self.cost_credits_used,
        }


class CostTracker:
    """
    Tracks and enforces cost budgets.

    Features:
    - LLM token tracking (max_llm_tokens)
    - API call tracking
    - Cost credit tracking (max_cost_credits)
    - Budget violation detection
    - Immune system integration
    - Prometheus metrics tracking

    Usage:
        tracker = CostTracker()

        budget = Budget(max_llm_tokens=10000, max_cost_credits=100.0)
        attempt_id = "a_123"

        # Initialize accumulator for attempt
        tracker.init_accumulator(attempt_id, budget)

        # Track LLM usage
        tracker.track_llm_tokens(
            attempt_id=attempt_id,
            prompt_tokens=500,
            completion_tokens=200
        )

        # Check if over budget
        if tracker.is_over_budget(attempt_id, budget):
            logger.error("Cost budget exceeded!")
    """

    def __init__(self):
        """Initialize cost tracker."""
        # Per-attempt accumulators
        self.accumulators: Dict[str, CostAccumulator] = {}

        # Metrics
        self.total_violations = 0
        self.token_violations = 0
        self.cost_violations = 0

    def init_accumulator(self, attempt_id: str, budget: Budget):
        """
        Initialize accumulator for attempt.

        Args:
            attempt_id: Attempt identifier
            budget: Budget for tracking
        """
        if attempt_id not in self.accumulators:
            self.accumulators[attempt_id] = CostAccumulator()

            logger.debug(
                f"Initialized cost accumulator for {attempt_id}",
                extra={
                    "attempt_id": attempt_id,
                    "max_llm_tokens": budget.max_llm_tokens,
                    "max_cost_credits": budget.max_cost_credits,
                }
            )

    def track_llm_tokens(
        self,
        attempt_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        budget: Budget,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Track LLM token usage and check budget.

        Args:
            attempt_id: Attempt identifier
            prompt_tokens: Prompt tokens used
            completion_tokens: Completion tokens used
            budget: Budget with max_llm_tokens
            context: Optional context

        Raises:
            BudgetCostExceededError: If max_llm_tokens exceeded
        """
        context = context or {}

        # Ensure accumulator exists
        self.init_accumulator(attempt_id, budget)

        accumulator = self.accumulators[attempt_id]

        # Add tokens
        accumulator.add_llm_tokens(prompt_tokens, completion_tokens)

        logger.debug(
            f"Tracked LLM tokens for {attempt_id}: {accumulator.llm_tokens_used} total",
            extra={
                "attempt_id": attempt_id,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": accumulator.llm_tokens_used,
                "context": context,
            }
        )

        # Check budget
        max_llm_tokens = budget.max_llm_tokens
        if max_llm_tokens and accumulator.llm_tokens_used > max_llm_tokens:
            self.total_violations += 1
            self.token_violations += 1

            logger.error(
                f"LLM token budget exceeded for {attempt_id}: {accumulator.llm_tokens_used} > {max_llm_tokens}",
                extra={
                    "attempt_id": attempt_id,
                    "tokens_used": accumulator.llm_tokens_used,
                    "max_tokens": max_llm_tokens,
                    "context": context,
                }
            )

            # Check immune alert
            immune_alert = should_alert_immune(NeuroRailErrorCode.BUDGET_COST_EXCEEDED)

            raise BudgetCostExceededError(
                message=f"LLM token budget exceeded: {accumulator.llm_tokens_used} > {max_llm_tokens}",
                error_code=NeuroRailErrorCode.BUDGET_COST_EXCEEDED,
                context={
                    **context,
                    "attempt_id": attempt_id,
                    "tokens_used": accumulator.llm_tokens_used,
                    "max_llm_tokens": max_llm_tokens,
                    "cost_type": "llm_tokens",
                    "immune_alert": immune_alert,
                },
            )

    def track_api_call(
        self,
        attempt_id: str,
        cost_credits: float,
        budget: Budget,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Track API call and cost credits.

        Args:
            attempt_id: Attempt identifier
            cost_credits: Cost credits consumed by this call
            budget: Budget with max_cost_credits
            context: Optional context

        Raises:
            BudgetCostExceededError: If max_cost_credits exceeded
        """
        context = context or {}

        # Ensure accumulator exists
        self.init_accumulator(attempt_id, budget)

        accumulator = self.accumulators[attempt_id]

        # Add API call
        accumulator.add_api_call(cost_credits)

        logger.debug(
            f"Tracked API call for {attempt_id}: {accumulator.api_calls_made} calls, {accumulator.cost_credits_used:.2f} credits",
            extra={
                "attempt_id": attempt_id,
                "cost_credits": cost_credits,
                "total_credits": accumulator.cost_credits_used,
                "total_calls": accumulator.api_calls_made,
                "context": context,
            }
        )

        # Check budget
        max_cost_credits = budget.max_cost_credits
        if max_cost_credits and accumulator.cost_credits_used > max_cost_credits:
            self.total_violations += 1
            self.cost_violations += 1

            logger.error(
                f"Cost credit budget exceeded for {attempt_id}: {accumulator.cost_credits_used:.2f} > {max_cost_credits:.2f}",
                extra={
                    "attempt_id": attempt_id,
                    "credits_used": accumulator.cost_credits_used,
                    "max_credits": max_cost_credits,
                    "context": context,
                }
            )

            # Check immune alert
            immune_alert = should_alert_immune(NeuroRailErrorCode.BUDGET_COST_EXCEEDED)

            raise BudgetCostExceededError(
                message=f"Cost credit budget exceeded: {accumulator.cost_credits_used:.2f} > {max_cost_credits:.2f}",
                error_code=NeuroRailErrorCode.BUDGET_COST_EXCEEDED,
                context={
                    **context,
                    "attempt_id": attempt_id,
                    "credits_used": accumulator.cost_credits_used,
                    "max_cost_credits": max_cost_credits,
                    "cost_type": "cost_credits",
                    "immune_alert": immune_alert,
                },
            )

    def is_over_budget(self, attempt_id: str, budget: Budget) -> bool:
        """
        Check if attempt is over budget (non-blocking check).

        Args:
            attempt_id: Attempt identifier
            budget: Budget to check against

        Returns:
            True if over budget, False otherwise
        """
        if attempt_id not in self.accumulators:
            return False

        accumulator = self.accumulators[attempt_id]

        # Check LLM tokens
        max_llm_tokens = budget.max_llm_tokens
        if max_llm_tokens and accumulator.llm_tokens_used > max_llm_tokens:
            return True

        # Check cost credits
        max_cost_credits = budget.max_cost_credits
        if max_cost_credits and accumulator.cost_credits_used > max_cost_credits:
            return True

        return False

    def get_accumulator(self, attempt_id: str) -> Optional[CostAccumulator]:
        """
        Get accumulator for attempt.

        Args:
            attempt_id: Attempt identifier

        Returns:
            CostAccumulator or None if not initialized
        """
        return self.accumulators.get(attempt_id)

    def finalize_accumulator(self, attempt_id: str) -> Optional[Dict[str, Any]]:
        """
        Finalize and remove accumulator, returning final costs.

        Args:
            attempt_id: Attempt identifier

        Returns:
            Final costs as dictionary, or None if not found
        """
        accumulator = self.accumulators.pop(attempt_id, None)
        if accumulator:
            logger.debug(
                f"Finalized cost accumulator for {attempt_id}",
                extra={"attempt_id": attempt_id, "costs": accumulator.to_dict()}
            )
            return accumulator.to_dict()
        return None

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get cost tracker metrics.

        Returns:
            Dictionary with violation counts
        """
        return {
            "total_violations": self.total_violations,
            "token_violations": self.token_violations,
            "cost_violations": self.cost_violations,
            "active_accumulators": len(self.accumulators),
        }

    def reset_metrics(self):
        """Reset metrics counters."""
        self.total_violations = 0
        self.token_violations = 0
        self.cost_violations = 0
        # Note: active accumulators are not reset


# Singleton instance
_cost_tracker: Optional[CostTracker] = None


def get_cost_tracker() -> CostTracker:
    """Get singleton CostTracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
