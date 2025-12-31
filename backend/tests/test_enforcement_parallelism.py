"""
Unit tests for Budget Parallelism Limiter (Phase 2 Enforcement).

Tests parallelism limits, semaphore management, and immune integration.
"""

import pytest
import asyncio
from backend.app.modules.neurorail.enforcement.parallelism import ParallelismLimiter
from backend.app.modules.governor.manifest.schemas import Budget
from backend.app.modules.neurorail.errors import BudgetParallelismExceededError


# ============================================================================
# Tests: Basic Parallelism Limiting
# ============================================================================

@pytest.mark.asyncio
async def test_parallelism_limiter_allows_execution_within_limit():
    """Test that execution is allowed within parallelism limit."""
    limiter = ParallelismLimiter(max_global_parallel=10)

    async def simple_task():
        await asyncio.sleep(0.1)
        return "success"

    budget = Budget(max_parallel_attempts=3)

    result = await limiter.execute_with_limit(
        task=simple_task,
        budget=budget,
        job_id="j_123"
    )

    assert result == "success"
    assert limiter.global_rejected_count == 0


@pytest.mark.asyncio
async def test_parallelism_limiter_concurrent_executions():
    """Test multiple concurrent executions within limit."""
    limiter = ParallelismLimiter(max_global_parallel=10)

    async def concurrent_task():
        await asyncio.sleep(0.2)
        return "done"

    budget = Budget(max_parallel_attempts=5)

    # Execute 3 tasks concurrently (within limit of 5)
    tasks = [
        limiter.execute_with_limit(concurrent_task, budget, job_id="j_123")
        for _ in range(3)
    ]

    results = await asyncio.gather(*tasks)

    assert len(results) == 3
    assert all(r == "done" for r in results)


@pytest.mark.asyncio
async def test_parallelism_limiter_job_limit_blocks():
    """Test that job-specific limit blocks when exceeded."""
    limiter = ParallelismLimiter(max_global_parallel=100)

    async def blocking_task():
        await asyncio.sleep(1.0)  # Long task to hold semaphore
        return "done"

    budget = Budget(max_parallel_attempts=2)  # Max 2 parallel for this job

    # Start 2 tasks (fills the limit)
    task1 = asyncio.create_task(
        limiter.execute_with_limit(blocking_task, budget, job_id="j_123")
    )
    task2 = asyncio.create_task(
        limiter.execute_with_limit(blocking_task, budget, job_id="j_123")
    )

    # Wait a bit for tasks to acquire semaphores
    await asyncio.sleep(0.1)

    # Third task should be rejected (limit reached)
    with pytest.raises(BudgetParallelismExceededError) as exc_info:
        await limiter.execute_with_limit(blocking_task, budget, job_id="j_123")

    assert "Job parallelism limit exceeded" in str(exc_info.value)
    assert limiter.job_rejected_counts.get("j_123", 0) == 1

    # Cleanup: cancel running tasks
    task1.cancel()
    task2.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass
    try:
        await task2
    except asyncio.CancelledError:
        pass


# ============================================================================
# Tests: Global Parallelism Limiting
# ============================================================================

@pytest.mark.asyncio
async def test_parallelism_limiter_global_limit_blocks():
    """Test that global limit blocks when exceeded."""
    limiter = ParallelismLimiter(max_global_parallel=2)  # Very low global limit

    async def blocking_task():
        await asyncio.sleep(1.0)
        return "done"

    budget = Budget(max_parallel_attempts=10)  # High job limit

    # Start 2 tasks (fills global limit)
    task1 = asyncio.create_task(
        limiter.execute_with_limit(blocking_task, budget, job_id="j_1")
    )
    task2 = asyncio.create_task(
        limiter.execute_with_limit(blocking_task, budget, job_id="j_2")
    )

    # Wait for tasks to acquire semaphores
    await asyncio.sleep(0.1)

    # Third task should be rejected (global limit reached)
    with pytest.raises(BudgetParallelismExceededError) as exc_info:
        await limiter.execute_with_limit(blocking_task, budget, job_id="j_3")

    assert "Global parallelism limit exceeded" in str(exc_info.value)
    assert limiter.global_rejected_count == 1

    # Cleanup
    task1.cancel()
    task2.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass
    try:
        await task2
    except asyncio.CancelledError:
        pass


# ============================================================================
# Tests: Metrics
# ============================================================================

def test_parallelism_limiter_get_metrics():
    """Test metrics retrieval."""
    limiter = ParallelismLimiter(max_global_parallel=10)
    limiter.global_rejected_count = 5
    limiter.global_peak_count = 8
    limiter.job_rejected_counts = {"j_123": 2, "j_456": 3}

    metrics = limiter.get_metrics()

    assert metrics["global_rejected_count"] == 5
    assert metrics["global_peak_count"] == 8
    assert metrics["max_global_parallel"] == 10
    assert metrics["job_rejected_counts"]["j_123"] == 2
    assert metrics["job_rejected_counts"]["j_456"] == 3


def test_parallelism_limiter_reset_metrics():
    """Test metrics reset."""
    limiter = ParallelismLimiter(max_global_parallel=10)
    limiter.global_rejected_count = 5
    limiter.job_rejected_counts = {"j_123": 2}

    limiter.reset_metrics()

    metrics = limiter.get_metrics()
    assert metrics["global_rejected_count"] == 0
    assert len(metrics["job_rejected_counts"]) == 0


# ============================================================================
# Tests: Context Tracking
# ============================================================================

@pytest.mark.asyncio
async def test_parallelism_limiter_context_in_error():
    """Test that context is included in error details."""
    limiter = ParallelismLimiter(max_global_parallel=1)

    async def blocking_task():
        await asyncio.sleep(1.0)
        return "done"

    budget = Budget(max_parallel_attempts=1)
    context = {"attempt_id": "a_456"}

    # Start 1 task (fills limit)
    task1 = asyncio.create_task(
        limiter.execute_with_limit(blocking_task, budget, job_id="j_123")
    )

    await asyncio.sleep(0.1)

    # Second task should be rejected
    with pytest.raises(BudgetParallelismExceededError) as exc_info:
        await limiter.execute_with_limit(
            blocking_task, budget, job_id="j_123", context=context
        )

    error = exc_info.value
    assert error.context["attempt_id"] == "a_456"
    assert error.context["job_id"] == "j_123"
    assert "limit_type" in error.context

    # Cleanup
    task1.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass


# ============================================================================
# Tests: Immune System Integration
# ============================================================================

@pytest.mark.asyncio
async def test_parallelism_limiter_immune_alert_flag():
    """Test that immune_alert flag is set in error context."""
    limiter = ParallelismLimiter(max_global_parallel=1)

    async def blocking_task():
        await asyncio.sleep(1.0)
        return "done"

    budget = Budget(max_parallel_attempts=1)

    # Start 1 task
    task1 = asyncio.create_task(
        limiter.execute_with_limit(blocking_task, budget, job_id="j_123")
    )

    await asyncio.sleep(0.1)

    # Second task rejected
    with pytest.raises(BudgetParallelismExceededError) as exc_info:
        await limiter.execute_with_limit(blocking_task, budget, job_id="j_123")

    error = exc_info.value
    assert "immune_alert" in error.context
    # BudgetParallelismExceededError has immune_alert=True
    assert error.context["immune_alert"] is True

    # Cleanup
    task1.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass


# ============================================================================
# Tests: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_parallelism_limiter_uses_default_max_parallel():
    """Test that default max_parallel_attempts is used when not specified."""
    limiter = ParallelismLimiter(max_global_parallel=10)

    async def simple_task():
        await asyncio.sleep(0.1)
        return "success"

    budget = Budget()  # No max_parallel_attempts specified

    result = await limiter.execute_with_limit(simple_task, budget, job_id="j_123")

    assert result == "success"


@pytest.mark.asyncio
async def test_parallelism_limiter_different_jobs_independent():
    """Test that different jobs have independent semaphores."""
    limiter = ParallelismLimiter(max_global_parallel=10)

    async def blocking_task():
        await asyncio.sleep(1.0)
        return "done"

    budget = Budget(max_parallel_attempts=1)

    # Start task for job_1 (fills job_1 limit)
    task1 = asyncio.create_task(
        limiter.execute_with_limit(blocking_task, budget, job_id="j_1")
    )

    await asyncio.sleep(0.1)

    # Task for job_2 should still be allowed (independent semaphore)
    result = await limiter.execute_with_limit(
        lambda: asyncio.sleep(0.1) or "success",
        budget,
        job_id="j_2"
    )

    assert result == "success"

    # Cleanup
    task1.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass
