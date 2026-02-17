"""Unit tests for Circuit Breaker (Phase 2 Reflex)."""

import pytest
import asyncio
from app.modules.neurorail.reflex.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
)
from app.modules.neurorail.errors import ReflexCircuitOpenError


@pytest.mark.asyncio
async def test_circuit_breaker_starts_closed():
    """Test circuit starts in CLOSED state."""
    breaker = CircuitBreaker("test_circuit")
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """Test circuit opens after failure threshold."""
    config = CircuitBreakerConfig(failure_threshold=3, recovery_timeout=60.0)
    breaker = CircuitBreaker("test_circuit", config)

    # Simulate 3 failures
    for _ in range(3):
        try:
            await breaker.call(lambda: asyncio.coroutine(lambda: (_ for _ in ()).throw(Exception("fail")))())
        except Exception:
            pass

    # Circuit should be OPEN
    assert breaker.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open():
    """Test circuit rejects requests when OPEN."""
    config = CircuitBreakerConfig(failure_threshold=1)
    breaker = CircuitBreaker("test_circuit", config)

    # Trigger opening
    try:
        await breaker.call(lambda: asyncio.coroutine(lambda: (_ for _ in ()).throw(Exception("fail")))())
    except Exception:
        pass

    # Should reject next request
    with pytest.raises(ReflexCircuitOpenError) as exc_info:
        await breaker.call(lambda: asyncio.sleep(0))

    assert "OPEN" in str(exc_info.value)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Test circuit transitions to HALF_OPEN after recovery timeout."""
    config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1)  # 100ms
    breaker = CircuitBreaker("test_circuit", config)

    # Trigger opening
    try:
        await breaker.call(lambda: asyncio.coroutine(lambda: (_ for _ in ()).throw(Exception("fail")))())
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN

    # Wait for recovery timeout
    await asyncio.sleep(0.2)

    # Next call should transition to HALF_OPEN
    async def success_task():
        return "success"

    result = await breaker.call(success_task)
    assert result == "success"
    assert breaker.state == CircuitState.HALF_OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_closes_after_successes():
    """Test circuit closes after success threshold in HALF_OPEN."""
    config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, success_threshold=2)
    breaker = CircuitBreaker("test_circuit", config)

    # Open circuit
    try:
        await breaker.call(lambda: asyncio.coroutine(lambda: (_ for _ in ()).throw(Exception("fail")))())
    except Exception:
        pass

    await asyncio.sleep(0.2)  # Wait for recovery

    # Transition to HALF_OPEN with first success
    async def success_task():
        return "ok"

    await breaker.call(success_task)
    assert breaker.state == CircuitState.HALF_OPEN

    # Second success should close circuit
    await breaker.call(success_task)
    assert breaker.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_manual_reset():
    """Test manual circuit reset."""
    breaker = CircuitBreaker("test_circuit")

    # Open circuit
    for _ in range(5):
        try:
            await breaker.call(lambda: asyncio.coroutine(lambda: (_ for _ in ()).throw(Exception("fail")))())
        except Exception:
            pass

    assert breaker.state == CircuitState.OPEN

    # Manual reset
    breaker.reset()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.metrics.failure_count == 0


def test_circuit_breaker_metrics():
    """Test metrics collection."""
    breaker = CircuitBreaker("test_circuit")

    metrics = breaker.get_metrics()

    assert metrics["circuit_id"] == "test_circuit"
    assert metrics["state"] == CircuitState.CLOSED
    assert metrics["total_calls"] == 0
