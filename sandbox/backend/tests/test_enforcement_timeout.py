"""
Unit tests for Budget Timeout Enforcer (Phase 2 Enforcement).

Tests timeout enforcement, grace period handling, and immune integration.
"""

import pytest
import asyncio
from app.modules.neurorail.enforcement.timeout import TimeoutEnforcer
from app.modules.governor.manifest.schemas import Budget
from app.modules.neurorail.errors import BudgetTimeoutExceededError


# ============================================================================
# Tests: Basic Timeout Enforcement
# ============================================================================

@pytest.mark.asyncio
async def test_timeout_enforcer_task_completes_within_budget():
    """Test task that completes within timeout budget."""
    enforcer = TimeoutEnforcer()

    async def fast_task():
        await asyncio.sleep(0.1)  # 100ms
        return "success"

    budget = Budget(timeout_ms=1000)  # 1 second

    result = await enforcer.enforce(fast_task, budget)

    assert result == "success"
    assert enforcer.timeout_count == 0


@pytest.mark.asyncio
async def test_timeout_enforcer_task_exceeds_budget():
    """Test task that exceeds timeout budget."""
    enforcer = TimeoutEnforcer()

    async def slow_task():
        await asyncio.sleep(2.0)  # 2 seconds
        return "never reached"

    budget = Budget(timeout_ms=500)  # 500ms

    with pytest.raises(BudgetTimeoutExceededError) as exc_info:
        await enforcer.enforce(slow_task, budget)

    assert "exceeded timeout budget" in str(exc_info.value).lower()
    assert enforcer.timeout_count == 1


@pytest.mark.asyncio
async def test_timeout_enforcer_exact_timeout():
    """Test task that takes exactly the timeout duration."""
    enforcer = TimeoutEnforcer()

    async def exact_task():
        await asyncio.sleep(1.0)  # Exactly 1 second
        return "success"

    budget = Budget(timeout_ms=1000)  # 1 second

    # Should complete (asyncio.wait_for has some tolerance)
    # But might timeout depending on system load
    # We test that either it completes or raises BudgetTimeoutExceededError
    try:
        result = await enforcer.enforce(exact_task, budget)
        assert result == "success"
    except BudgetTimeoutExceededError:
        # Also acceptable (edge case)
        pass


@pytest.mark.asyncio
async def test_timeout_enforcer_uses_default_timeout():
    """Test that default timeout is used when not specified."""
    enforcer = TimeoutEnforcer()

    async def fast_task():
        await asyncio.sleep(0.1)
        return "success"

    budget = Budget()  # No timeout specified

    result = await enforcer.enforce(fast_task, budget)

    assert result == "success"


# ============================================================================
# Tests: Grace Period Handling
# ============================================================================

@pytest.mark.asyncio
async def test_timeout_enforcer_grace_period_completes():
    """Test grace period cleanup completes successfully."""
    enforcer = TimeoutEnforcer()

    async def slow_task():
        await asyncio.sleep(2.0)  # Exceeds timeout
        return "never"

    cleanup_invoked = False

    async def cleanup_handler():
        nonlocal cleanup_invoked
        cleanup_invoked = True
        await asyncio.sleep(0.1)  # Quick cleanup

    budget = Budget(timeout_ms=500, grace_period_ms=1000)

    with pytest.raises(BudgetTimeoutExceededError):
        await enforcer.enforce_with_grace_period(
            task=slow_task,
            budget=budget,
            cleanup_handler=cleanup_handler
        )

    assert cleanup_invoked is True
    assert enforcer.grace_period_invoked_count == 1
    assert enforcer.timeout_count == 1


@pytest.mark.asyncio
async def test_timeout_enforcer_grace_period_exceeds():
    """Test grace period cleanup also times out."""
    enforcer = TimeoutEnforcer()

    async def slow_task():
        await asyncio.sleep(2.0)
        return "never"

    async def slow_cleanup():
        await asyncio.sleep(3.0)  # Exceeds grace period
        return "never"

    budget = Budget(timeout_ms=500, grace_period_ms=1000)

    with pytest.raises(BudgetTimeoutExceededError) as exc_info:
        await enforcer.enforce_with_grace_period(
            task=slow_task,
            budget=budget,
            cleanup_handler=slow_cleanup
        )

    assert "exceeded timeout budget" in str(exc_info.value).lower()
    assert enforcer.grace_period_invoked_count == 1


@pytest.mark.asyncio
async def test_timeout_enforcer_no_cleanup_handler():
    """Test grace period enforcement without cleanup handler."""
    enforcer = TimeoutEnforcer()

    async def slow_task():
        await asyncio.sleep(2.0)
        return "never"

    budget = Budget(timeout_ms=500, grace_period_ms=1000)

    with pytest.raises(BudgetTimeoutExceededError):
        await enforcer.enforce_with_grace_period(
            task=slow_task,
            budget=budget,
            cleanup_handler=None  # No cleanup
        )

    assert enforcer.grace_period_invoked_count == 1


# ============================================================================
# Tests: Metrics
# ============================================================================

def test_timeout_enforcer_get_metrics():
    """Test metrics retrieval."""
    enforcer = TimeoutEnforcer()
    enforcer.timeout_count = 5
    enforcer.grace_period_invoked_count = 2

    metrics = enforcer.get_metrics()

    assert metrics["timeout_count"] == 5
    assert metrics["grace_period_invoked_count"] == 2


def test_timeout_enforcer_reset_metrics():
    """Test metrics reset."""
    enforcer = TimeoutEnforcer()
    enforcer.timeout_count = 5
    enforcer.grace_period_invoked_count = 2

    enforcer.reset_metrics()

    metrics = enforcer.get_metrics()
    assert metrics["timeout_count"] == 0
    assert metrics["grace_period_invoked_count"] == 0


# ============================================================================
# Tests: Context Tracking
# ============================================================================

@pytest.mark.asyncio
async def test_timeout_enforcer_context_in_error():
    """Test that context is included in error details."""
    enforcer = TimeoutEnforcer()

    async def slow_task():
        await asyncio.sleep(2.0)
        return "never"

    budget = Budget(timeout_ms=500)
    context = {"job_id": "j_123", "attempt_id": "a_456"}

    with pytest.raises(BudgetTimeoutExceededError) as exc_info:
        await enforcer.enforce(slow_task, budget, context=context)

    error = exc_info.value
    assert error.context["job_id"] == "j_123"
    assert error.context["attempt_id"] == "a_456"
    assert "timeout_ms" in error.context
    assert "elapsed_ms" in error.context


# ============================================================================
# Tests: Immune System Integration
# ============================================================================

@pytest.mark.asyncio
async def test_timeout_enforcer_immune_alert_flag():
    """Test that immune_alert flag is set in error context."""
    enforcer = TimeoutEnforcer()

    async def slow_task():
        await asyncio.sleep(2.0)
        return "never"

    budget = Budget(timeout_ms=500)

    with pytest.raises(BudgetTimeoutExceededError) as exc_info:
        await enforcer.enforce(slow_task, budget)

    error = exc_info.value
    assert "immune_alert" in error.context
    # BudgetTimeoutExceededError has immune_alert=True in errors.py
    assert error.context["immune_alert"] is True


# ============================================================================
# Tests: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_timeout_enforcer_zero_timeout():
    """Test that zero timeout immediately times out."""
    enforcer = TimeoutEnforcer()

    async def any_task():
        await asyncio.sleep(0.001)
        return "never"

    budget = Budget(timeout_ms=0)  # Zero timeout

    with pytest.raises(BudgetTimeoutExceededError):
        await enforcer.enforce(any_task, budget)


@pytest.mark.asyncio
async def test_timeout_enforcer_very_long_timeout():
    """Test that very long timeout allows task to complete."""
    enforcer = TimeoutEnforcer()

    async def fast_task():
        await asyncio.sleep(0.1)
        return "success"

    budget = Budget(timeout_ms=60000)  # 1 minute

    result = await enforcer.enforce(fast_task, budget)

    assert result == "success"
    assert enforcer.timeout_count == 0
