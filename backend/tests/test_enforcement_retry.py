"""
Unit tests for Budget Retry Handler (Phase 2 Enforcement).

Tests retry logic, exponential backoff, retriability classification, and immune integration.
"""

import pytest
import asyncio
from backend.app.modules.neurorail.enforcement.retry import RetryHandler
from backend.app.modules.governor.manifest.schemas import Budget
from backend.app.modules.neurorail.errors import BudgetRetryExhaustedError


# ============================================================================
# Tests: Basic Retry Logic
# ============================================================================

@pytest.mark.asyncio
async def test_retry_handler_success_first_attempt():
    """Test task that succeeds on first attempt (no retries)."""
    handler = RetryHandler(base_delay_ms=100, jitter=False)

    async def successful_task():
        return "success"

    budget = Budget(max_retries=3)

    result = await handler.execute_with_retry(successful_task, budget)

    assert result == "success"
    assert handler.retry_count == 0
    assert handler.success_after_retry_count == 0


@pytest.mark.asyncio
async def test_retry_handler_success_after_retry():
    """Test task that succeeds after 2 retries."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    attempt_counter = 0

    async def flaky_task():
        nonlocal attempt_counter
        attempt_counter += 1
        if attempt_counter < 3:
            raise ConnectionError("Temporary failure")
        return "success"

    budget = Budget(max_retries=5)

    result = await handler.execute_with_retry(flaky_task, budget)

    assert result == "success"
    assert attempt_counter == 3  # 1 initial + 2 retries
    assert handler.retry_count == 2
    assert handler.success_after_retry_count == 1


@pytest.mark.asyncio
async def test_retry_handler_exhausted():
    """Test task that exhausts all retries."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def always_fails():
        raise ConnectionError("Permanent failure")

    budget = Budget(max_retries=3)

    with pytest.raises(BudgetRetryExhaustedError) as exc_info:
        await handler.execute_with_retry(always_fails, budget)

    assert "Retry budget exhausted" in str(exc_info.value)
    assert handler.retry_count == 3
    assert handler.exhausted_count == 1


# ============================================================================
# Tests: Exponential Backoff
# ============================================================================

@pytest.mark.asyncio
async def test_retry_handler_exponential_backoff():
    """Test exponential backoff delay calculation."""
    handler = RetryHandler(base_delay_ms=100, exponential_base=2.0, jitter=False)

    # Attempt 0: 100 * (2^0) = 100ms
    assert handler._compute_delay(0) == pytest.approx(0.1, abs=0.01)

    # Attempt 1: 100 * (2^1) = 200ms
    assert handler._compute_delay(1) == pytest.approx(0.2, abs=0.01)

    # Attempt 2: 100 * (2^2) = 400ms
    assert handler._compute_delay(2) == pytest.approx(0.4, abs=0.01)

    # Attempt 3: 100 * (2^3) = 800ms
    assert handler._compute_delay(3) == pytest.approx(0.8, abs=0.01)


@pytest.mark.asyncio
async def test_retry_handler_max_delay_cap():
    """Test that delay is capped at max_delay_ms."""
    handler = RetryHandler(base_delay_ms=1000, max_delay_ms=5000, exponential_base=2.0, jitter=False)

    # Attempt 10: 1000 * (2^10) = 1024000ms → capped at 5000ms
    delay = handler._compute_delay(10)

    assert delay == pytest.approx(5.0, abs=0.01)  # 5 seconds


@pytest.mark.asyncio
async def test_retry_handler_jitter():
    """Test that jitter adds randomness to delay."""
    handler = RetryHandler(base_delay_ms=1000, jitter=True)

    # Run delay calculation 10 times
    delays = [handler._compute_delay(1) for _ in range(10)]

    # All delays should be different (with very high probability)
    assert len(set(delays)) > 5  # At least 5 different values

    # All delays should be within jitter range (0.5x to 1.5x)
    base_delay = 2.0  # 1000ms * 2^1 = 2000ms = 2.0s
    for delay in delays:
        assert 0.5 * base_delay <= delay <= 1.5 * base_delay


# ============================================================================
# Tests: Retriability Classification
# ============================================================================

@pytest.mark.asyncio
async def test_retry_handler_non_retriable_error_raises_immediately():
    """Test that non-retriable errors are raised immediately without retry."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def non_retriable_task():
        raise ValueError("Non-retriable error")

    budget = Budget(max_retries=3)

    # ValueError is not in retriable_exceptions, so should raise immediately
    with pytest.raises(ValueError) as exc_info:
        await handler.execute_with_retry(non_retriable_task, budget)

    assert "Non-retriable error" in str(exc_info.value)
    assert handler.retry_count == 0  # No retries


@pytest.mark.asyncio
async def test_retry_handler_retriable_exception_retries():
    """Test that retriable exceptions trigger retries."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def retriable_task():
        raise ConnectionError("Retriable error")

    budget = Budget(max_retries=2)

    # ConnectionError is retriable, so should retry
    with pytest.raises(BudgetRetryExhaustedError):
        await handler.execute_with_retry(retriable_task, budget)

    assert handler.retry_count == 2


@pytest.mark.asyncio
async def test_retry_handler_custom_retriable_exceptions():
    """Test custom retriable exceptions parameter."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def custom_error_task():
        raise ValueError("Custom retriable")

    budget = Budget(max_retries=2)

    # Explicitly mark ValueError as retriable
    with pytest.raises(BudgetRetryExhaustedError):
        await handler.execute_with_retry(
            custom_error_task,
            budget,
            retriable_exceptions=(ValueError,)
        )

    assert handler.retry_count == 2


# ============================================================================
# Tests: Metrics
# ============================================================================

def test_retry_handler_get_metrics():
    """Test metrics retrieval."""
    handler = RetryHandler()
    handler.retry_count = 10
    handler.success_after_retry_count = 3
    handler.exhausted_count = 2

    metrics = handler.get_metrics()

    assert metrics["retry_count"] == 10
    assert metrics["success_after_retry_count"] == 3
    assert metrics["exhausted_count"] == 2


def test_retry_handler_reset_metrics():
    """Test metrics reset."""
    handler = RetryHandler()
    handler.retry_count = 10
    handler.success_after_retry_count = 3
    handler.exhausted_count = 2

    handler.reset_metrics()

    metrics = handler.get_metrics()
    assert metrics["retry_count"] == 0
    assert metrics["success_after_retry_count"] == 0
    assert metrics["exhausted_count"] == 0


# ============================================================================
# Tests: Retry History
# ============================================================================

@pytest.mark.asyncio
async def test_retry_handler_retry_history_in_error():
    """Test that retry history is included in error context."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def always_fails():
        raise ConnectionError("Failure")

    budget = Budget(max_retries=2)

    with pytest.raises(BudgetRetryExhaustedError) as exc_info:
        await handler.execute_with_retry(always_fails, budget)

    error = exc_info.value
    assert "retry_history" in error.context
    assert len(error.context["retry_history"]) == 3  # 1 initial + 2 retries


# ============================================================================
# Tests: Context Tracking
# ============================================================================

@pytest.mark.asyncio
async def test_retry_handler_context_in_error():
    """Test that context is included in error details."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def always_fails():
        raise ConnectionError("Failure")

    budget = Budget(max_retries=2)
    context = {"job_id": "j_123", "attempt_id": "a_456"}

    with pytest.raises(BudgetRetryExhaustedError) as exc_info:
        await handler.execute_with_retry(always_fails, budget, context=context)

    error = exc_info.value
    assert error.context["job_id"] == "j_123"
    assert error.context["attempt_id"] == "a_456"
    assert "max_retries" in error.context
    assert "attempts" in error.context


# ============================================================================
# Tests: Immune System Integration
# ============================================================================

@pytest.mark.asyncio
async def test_retry_handler_immune_alert_flag():
    """Test that immune_alert flag is set in error context."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def always_fails():
        raise ConnectionError("Failure")

    budget = Budget(max_retries=2)

    with pytest.raises(BudgetRetryExhaustedError) as exc_info:
        await handler.execute_with_retry(always_fails, budget)

    error = exc_info.value
    assert "immune_alert" in error.context
    # BudgetRetryExhaustedError has immune_alert=True in errors.py
    assert error.context["immune_alert"] is True


# ============================================================================
# Tests: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_retry_handler_zero_retries():
    """Test that zero retries means no retry attempts."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def always_fails():
        raise ConnectionError("Failure")

    budget = Budget(max_retries=0)  # No retries

    # Should raise BudgetRetryExhaustedError immediately after first failure
    with pytest.raises(BudgetRetryExhaustedError):
        await handler.execute_with_retry(always_fails, budget)

    assert handler.retry_count == 0  # No retries (only initial attempt)


@pytest.mark.asyncio
async def test_retry_handler_uses_default_max_retries():
    """Test that default max_retries is used when not specified."""
    handler = RetryHandler(base_delay_ms=10, jitter=False)

    async def always_fails():
        raise ConnectionError("Failure")

    budget = Budget()  # No max_retries specified

    with pytest.raises(BudgetRetryExhaustedError):
        await handler.execute_with_retry(always_fails, budget)

    # Default is 3 retries
    assert handler.retry_count == 3
