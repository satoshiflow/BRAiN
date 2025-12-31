"""
Unit tests for Budget Cost Tracker (Phase 2 Enforcement).

Tests cost tracking, budget violations, and immune integration.
"""

import pytest
from backend.app.modules.neurorail.enforcement.cost import CostTracker, CostAccumulator
from backend.app.modules.governor.manifest.schemas import Budget
from backend.app.modules.neurorail.errors import BudgetCostExceededError


# ============================================================================
# Tests: Basic Cost Tracking
# ============================================================================

def test_cost_tracker_init_accumulator():
    """Test accumulator initialization."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=10000)

    tracker.init_accumulator("a_123", budget)

    assert "a_123" in tracker.accumulators
    accumulator = tracker.accumulators["a_123"]
    assert accumulator.llm_tokens_used == 0


def test_cost_tracker_track_llm_tokens_within_budget():
    """Test tracking LLM tokens within budget."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=10000)
    attempt_id = "a_123"

    tracker.track_llm_tokens(
        attempt_id=attempt_id,
        prompt_tokens=500,
        completion_tokens=200,
        budget=budget
    )

    accumulator = tracker.get_accumulator(attempt_id)
    assert accumulator.llm_prompt_tokens == 500
    assert accumulator.llm_completion_tokens == 200
    assert accumulator.llm_tokens_used == 700


def test_cost_tracker_track_llm_tokens_exceeds_budget():
    """Test tracking LLM tokens that exceed budget."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=1000)
    attempt_id = "a_123"

    # First tracking within budget
    tracker.track_llm_tokens(
        attempt_id=attempt_id,
        prompt_tokens=500,
        completion_tokens=200,
        budget=budget
    )

    # Second tracking exceeds budget
    with pytest.raises(BudgetCostExceededError) as exc_info:
        tracker.track_llm_tokens(
            attempt_id=attempt_id,
            prompt_tokens=300,
            completion_tokens=200,
            budget=budget
        )

    assert "LLM token budget exceeded" in str(exc_info.value)
    assert tracker.token_violations == 1


def test_cost_tracker_track_api_call_within_budget():
    """Test tracking API calls within budget."""
    tracker = CostTracker()
    budget = Budget(max_cost_credits=100.0)
    attempt_id = "a_123"

    tracker.track_api_call(
        attempt_id=attempt_id,
        cost_credits=25.0,
        budget=budget
    )

    accumulator = tracker.get_accumulator(attempt_id)
    assert accumulator.api_calls_made == 1
    assert accumulator.cost_credits_used == 25.0


def test_cost_tracker_track_api_call_exceeds_budget():
    """Test tracking API calls that exceed budget."""
    tracker = CostTracker()
    budget = Budget(max_cost_credits=50.0)
    attempt_id = "a_123"

    # First call within budget
    tracker.track_api_call(
        attempt_id=attempt_id,
        cost_credits=30.0,
        budget=budget
    )

    # Second call exceeds budget
    with pytest.raises(BudgetCostExceededError) as exc_info:
        tracker.track_api_call(
            attempt_id=attempt_id,
            cost_credits=25.0,
            budget=budget
        )

    assert "Cost credit budget exceeded" in str(exc_info.value)
    assert tracker.cost_violations == 1


# ============================================================================
# Tests: Cost Accumulator
# ============================================================================

def test_cost_accumulator_add_llm_tokens():
    """Test adding LLM tokens to accumulator."""
    accumulator = CostAccumulator()

    accumulator.add_llm_tokens(500, 200)

    assert accumulator.llm_prompt_tokens == 500
    assert accumulator.llm_completion_tokens == 200
    assert accumulator.llm_tokens_used == 700


def test_cost_accumulator_add_llm_tokens_multiple_times():
    """Test adding LLM tokens multiple times."""
    accumulator = CostAccumulator()

    accumulator.add_llm_tokens(500, 200)
    accumulator.add_llm_tokens(300, 100)

    assert accumulator.llm_prompt_tokens == 800
    assert accumulator.llm_completion_tokens == 300
    assert accumulator.llm_tokens_used == 1100


def test_cost_accumulator_add_api_call():
    """Test adding API call to accumulator."""
    accumulator = CostAccumulator()

    accumulator.add_api_call(cost_credits=10.0)

    assert accumulator.api_calls_made == 1
    assert accumulator.cost_credits_used == 10.0


def test_cost_accumulator_add_api_call_multiple_times():
    """Test adding multiple API calls."""
    accumulator = CostAccumulator()

    accumulator.add_api_call(cost_credits=10.0)
    accumulator.add_api_call(cost_credits=15.0)
    accumulator.add_api_call(cost_credits=5.0)

    assert accumulator.api_calls_made == 3
    assert accumulator.cost_credits_used == 30.0


def test_cost_accumulator_to_dict():
    """Test converting accumulator to dictionary."""
    accumulator = CostAccumulator()
    accumulator.add_llm_tokens(500, 200)
    accumulator.add_api_call(cost_credits=10.0)

    data = accumulator.to_dict()

    assert data["llm_tokens_used"] == 700
    assert data["llm_prompt_tokens"] == 500
    assert data["llm_completion_tokens"] == 200
    assert data["api_calls_made"] == 1
    assert data["cost_credits_used"] == 10.0


# ============================================================================
# Tests: Budget Checks
# ============================================================================

def test_cost_tracker_is_over_budget_tokens():
    """Test checking if over budget (tokens)."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=1000)
    attempt_id = "a_123"

    tracker.init_accumulator(attempt_id, budget)

    # Within budget
    tracker.accumulators[attempt_id].add_llm_tokens(400, 300)
    assert tracker.is_over_budget(attempt_id, budget) is False

    # Over budget
    tracker.accumulators[attempt_id].add_llm_tokens(200, 200)
    assert tracker.is_over_budget(attempt_id, budget) is True


def test_cost_tracker_is_over_budget_credits():
    """Test checking if over budget (cost credits)."""
    tracker = CostTracker()
    budget = Budget(max_cost_credits=50.0)
    attempt_id = "a_123"

    tracker.init_accumulator(attempt_id, budget)

    # Within budget
    tracker.accumulators[attempt_id].add_api_call(cost_credits=30.0)
    assert tracker.is_over_budget(attempt_id, budget) is False

    # Over budget
    tracker.accumulators[attempt_id].add_api_call(cost_credits=25.0)
    assert tracker.is_over_budget(attempt_id, budget) is True


def test_cost_tracker_is_over_budget_nonexistent_attempt():
    """Test checking budget for non-existent attempt."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=1000)

    # Should return False for non-existent attempt
    assert tracker.is_over_budget("nonexistent", budget) is False


# ============================================================================
# Tests: Accumulator Finalization
# ============================================================================

def test_cost_tracker_finalize_accumulator():
    """Test finalizing accumulator."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=10000)
    attempt_id = "a_123"

    tracker.track_llm_tokens(attempt_id, 500, 200, budget)
    tracker.track_api_call(attempt_id, 10.0, budget)

    # Finalize
    final_costs = tracker.finalize_accumulator(attempt_id)

    assert final_costs is not None
    assert final_costs["llm_tokens_used"] == 700
    assert final_costs["api_calls_made"] == 1
    assert attempt_id not in tracker.accumulators  # Removed


def test_cost_tracker_finalize_nonexistent_accumulator():
    """Test finalizing non-existent accumulator."""
    tracker = CostTracker()

    final_costs = tracker.finalize_accumulator("nonexistent")

    assert final_costs is None


# ============================================================================
# Tests: Metrics
# ============================================================================

def test_cost_tracker_get_metrics():
    """Test metrics retrieval."""
    tracker = CostTracker()
    tracker.total_violations = 10
    tracker.token_violations = 6
    tracker.cost_violations = 4
    tracker.accumulators["a_1"] = CostAccumulator()
    tracker.accumulators["a_2"] = CostAccumulator()

    metrics = tracker.get_metrics()

    assert metrics["total_violations"] == 10
    assert metrics["token_violations"] == 6
    assert metrics["cost_violations"] == 4
    assert metrics["active_accumulators"] == 2


def test_cost_tracker_reset_metrics():
    """Test metrics reset."""
    tracker = CostTracker()
    tracker.total_violations = 10
    tracker.token_violations = 6
    tracker.cost_violations = 4

    tracker.reset_metrics()

    metrics = tracker.get_metrics()
    assert metrics["total_violations"] == 0
    assert metrics["token_violations"] == 0
    assert metrics["cost_violations"] == 0


# ============================================================================
# Tests: Context Tracking
# ============================================================================

def test_cost_tracker_context_in_error():
    """Test that context is included in error details."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=1000)
    attempt_id = "a_123"
    context = {"job_id": "j_456"}

    with pytest.raises(BudgetCostExceededError) as exc_info:
        tracker.track_llm_tokens(
            attempt_id=attempt_id,
            prompt_tokens=800,
            completion_tokens=300,
            budget=budget,
            context=context
        )

    error = exc_info.value
    assert error.context["job_id"] == "j_456"
    assert error.context["attempt_id"] == "a_123"
    assert "max_llm_tokens" in error.context


# ============================================================================
# Tests: Immune System Integration
# ============================================================================

def test_cost_tracker_immune_alert_flag():
    """Test that immune_alert flag is set in error context."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=1000)

    with pytest.raises(BudgetCostExceededError) as exc_info:
        tracker.track_llm_tokens("a_123", 800, 300, budget)

    error = exc_info.value
    assert "immune_alert" in error.context
    # BudgetCostExceededError has immune_alert=True
    assert error.context["immune_alert"] is True


# ============================================================================
# Tests: Edge Cases
# ============================================================================

def test_cost_tracker_no_budget_limits():
    """Test tracking without budget limits."""
    tracker = CostTracker()
    budget = Budget()  # No limits specified

    # Should not raise any errors
    tracker.track_llm_tokens("a_123", 10000, 10000, budget)
    tracker.track_api_call("a_123", 1000.0, budget)

    accumulator = tracker.get_accumulator("a_123")
    assert accumulator.llm_tokens_used == 20000
    assert accumulator.cost_credits_used == 1000.0


def test_cost_tracker_multiple_attempts():
    """Test tracking multiple attempts independently."""
    tracker = CostTracker()
    budget = Budget(max_llm_tokens=1000)

    tracker.track_llm_tokens("a_1", 400, 200, budget)
    tracker.track_llm_tokens("a_2", 300, 100, budget)

    acc1 = tracker.get_accumulator("a_1")
    acc2 = tracker.get_accumulator("a_2")

    assert acc1.llm_tokens_used == 600
    assert acc2.llm_tokens_used == 400
