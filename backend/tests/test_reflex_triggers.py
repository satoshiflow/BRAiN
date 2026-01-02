"""
Unit tests for Reflex Triggers (Phase 2 Reflex).

Tests error rate monitoring, budget violation tracking, and trigger activation.
"""

import pytest
import time
from backend.app.modules.neurorail.reflex.triggers import (
    ReflexTrigger,
    TriggerConfig,
    get_reflex_trigger,
)
from backend.app.modules.neurorail.errors import ReflexTriggerActivatedError


# ============================================================================
# Tests: Event Recording
# ============================================================================

def test_trigger_record_success():
    """Test recording successful operations."""
    trigger = ReflexTrigger("test_trigger")

    trigger.record_success()
    trigger.record_success()

    assert len(trigger.events) == 2
    assert all(e["type"] == "success" for e in trigger.events)


def test_trigger_record_failure():
    """Test recording failed operations."""
    trigger = ReflexTrigger("test_trigger")

    trigger.record_failure(error_type="timeout")
    trigger.record_failure(error_type="overbudget")

    assert len(trigger.events) == 2
    assert all(e["type"] == "failure" for e in trigger.events)
    assert trigger.events[0]["error_type"] == "timeout"


def test_trigger_record_budget_violation():
    """Test recording budget violations."""
    trigger = ReflexTrigger("test_trigger")

    trigger.record_budget_violation("token_limit")
    trigger.record_budget_violation("cost_limit")

    assert trigger.budget_violations == 2
    assert len(trigger.events) == 2


# ============================================================================
# Tests: Error Rate Calculation
# ============================================================================

def test_trigger_compute_error_rate_insufficient_samples():
    """Test error rate returns None when insufficient samples."""
    config = TriggerConfig(name="test", min_samples=5)
    trigger = ReflexTrigger("test_trigger", config)

    trigger.record_success()
    trigger.record_failure()

    error_rate = trigger.compute_error_rate()
    assert error_rate is None  # Only 2 samples, need 5


def test_trigger_compute_error_rate_zero():
    """Test error rate is 0% when all successes."""
    config = TriggerConfig(name="test", min_samples=5)
    trigger = ReflexTrigger("test_trigger", config)

    for _ in range(5):
        trigger.record_success()

    error_rate = trigger.compute_error_rate()
    assert error_rate == 0.0


def test_trigger_compute_error_rate_fifty_percent():
    """Test error rate is 50% when half fail."""
    config = TriggerConfig(name="test", min_samples=5)
    trigger = ReflexTrigger("test_trigger", config)

    trigger.record_success()
    trigger.record_failure()
    trigger.record_success()
    trigger.record_failure()
    trigger.record_success()

    error_rate = trigger.compute_error_rate()
    assert error_rate == 0.4  # 2 failures / 5 total


def test_trigger_compute_error_rate_hundred_percent():
    """Test error rate is 100% when all fail."""
    config = TriggerConfig(name="test", min_samples=5)
    trigger = ReflexTrigger("test_trigger", config)

    for _ in range(5):
        trigger.record_failure()

    error_rate = trigger.compute_error_rate()
    assert error_rate == 1.0


# ============================================================================
# Tests: Sliding Window
# ============================================================================

def test_trigger_sliding_window_excludes_old_events():
    """Test sliding window excludes events outside time window."""
    config = TriggerConfig(name="test", window_seconds=0.1, min_samples=2)
    trigger = ReflexTrigger("test_trigger", config)

    # Record old events
    trigger.record_failure()
    trigger.record_failure()

    # Wait for window to expire
    time.sleep(0.15)

    # Record new events
    trigger.record_success()
    trigger.record_success()

    # Error rate should only consider recent successes
    error_rate = trigger.compute_error_rate()
    assert error_rate == 0.0  # Old failures excluded


def test_trigger_sliding_window_includes_recent_events():
    """Test sliding window includes recent events."""
    config = TriggerConfig(name="test", window_seconds=1.0, min_samples=3)
    trigger = ReflexTrigger("test_trigger", config)

    trigger.record_success()
    time.sleep(0.05)
    trigger.record_failure()
    time.sleep(0.05)
    trigger.record_success()

    error_rate = trigger.compute_error_rate()
    assert error_rate == pytest.approx(0.333, abs=0.01)  # 1 failure / 3 total


# ============================================================================
# Tests: Trigger Activation Logic
# ============================================================================

def test_trigger_should_activate_error_rate_threshold():
    """Test trigger activates when error rate exceeds threshold."""
    config = TriggerConfig(name="test", error_rate_threshold=0.5, min_samples=5)
    trigger = ReflexTrigger("test_trigger", config)

    # 60% error rate (3/5)
    trigger.record_failure()
    trigger.record_failure()
    trigger.record_failure()
    trigger.record_success()
    trigger.record_success()

    assert trigger.should_activate() is True


def test_trigger_should_activate_budget_violations():
    """Test trigger activates when budget violations exceed threshold."""
    config = TriggerConfig(name="test", budget_violation_threshold=3)
    trigger = ReflexTrigger("test_trigger", config)

    trigger.record_budget_violation("token_limit")
    trigger.record_budget_violation("token_limit")
    trigger.record_budget_violation("cost_limit")

    assert trigger.should_activate() is True


def test_trigger_should_not_activate_below_thresholds():
    """Test trigger does not activate below thresholds."""
    config = TriggerConfig(
        name="test",
        error_rate_threshold=0.5,
        budget_violation_threshold=3,
        min_samples=5
    )
    trigger = ReflexTrigger("test_trigger", config)

    # 40% error rate (below 50% threshold)
    trigger.record_failure()
    trigger.record_failure()
    trigger.record_success()
    trigger.record_success()
    trigger.record_success()

    # 2 budget violations (below 3 threshold)
    trigger.record_budget_violation("token_limit")
    trigger.record_budget_violation("cost_limit")

    assert trigger.should_activate() is False


# ============================================================================
# Tests: Activation
# ============================================================================

def test_trigger_activate_raises_error():
    """Test activate raises ReflexTriggerActivatedError."""
    trigger = ReflexTrigger("test_trigger")

    with pytest.raises(ReflexTriggerActivatedError) as exc_info:
        trigger.activate(reason="Error rate exceeded")

    assert "Error rate exceeded" in str(exc_info.value)
    assert exc_info.value.trigger_type == "test_trigger"


def test_trigger_activate_increments_count():
    """Test activate increments activation count."""
    trigger = ReflexTrigger("test_trigger")

    try:
        trigger.activate(reason="Test1")
    except ReflexTriggerActivatedError:
        pass

    try:
        trigger.activate(reason="Test2")
    except ReflexTriggerActivatedError:
        pass

    assert trigger.activation_count == 2


def test_trigger_activate_sets_timestamp():
    """Test activate sets last activation timestamp."""
    trigger = ReflexTrigger("test_trigger")

    before = time.time()

    try:
        trigger.activate(reason="Test")
    except ReflexTriggerActivatedError:
        pass

    after = time.time()

    assert trigger.last_activation_time is not None
    assert before <= trigger.last_activation_time <= after


def test_trigger_activate_includes_context():
    """Test activate includes context in error."""
    trigger = ReflexTrigger("test_trigger")
    context = {"job_id": "j_123", "attempt_id": "a_456"}

    with pytest.raises(ReflexTriggerActivatedError) as exc_info:
        trigger.activate(reason="Test", context=context)

    error = exc_info.value
    assert error.details["job_id"] == "j_123"
    assert error.details["attempt_id"] == "a_456"


# ============================================================================
# Tests: Reset
# ============================================================================

def test_trigger_reset_clears_events():
    """Test reset clears event history."""
    trigger = ReflexTrigger("test_trigger")

    trigger.record_success()
    trigger.record_failure()
    trigger.record_budget_violation("token_limit")

    trigger.reset()

    assert len(trigger.events) == 0
    assert trigger.budget_violations == 0


# ============================================================================
# Tests: Metrics
# ============================================================================

def test_trigger_get_metrics():
    """Test get_metrics returns comprehensive metrics."""
    config = TriggerConfig(name="test", min_samples=3)
    trigger = ReflexTrigger("test_trigger", config)

    trigger.record_success()
    trigger.record_failure()
    trigger.record_failure()
    trigger.record_budget_violation("token_limit")

    try:
        trigger.activate(reason="Test")
    except ReflexTriggerActivatedError:
        pass

    metrics = trigger.get_metrics()

    assert metrics["trigger_id"] == "test_trigger"
    assert metrics["error_rate"] == pytest.approx(0.666, abs=0.01)  # 2 failures / 3 total
    assert metrics["budget_violations"] == 1
    assert metrics["activation_count"] == 1
    assert metrics["last_activation_time"] is not None
    assert metrics["recent_event_count"] == 4  # 3 events + 1 budget violation


# ============================================================================
# Tests: Trigger Registry
# ============================================================================

def test_get_reflex_trigger_creates_new():
    """Test get_reflex_trigger creates new trigger if not exists."""
    trigger = get_reflex_trigger("new_trigger")

    assert trigger.trigger_id == "new_trigger"


def test_get_reflex_trigger_returns_existing():
    """Test get_reflex_trigger returns existing trigger."""
    trigger1 = get_reflex_trigger("existing_trigger")
    trigger1.record_success()

    trigger2 = get_reflex_trigger("existing_trigger")

    assert trigger1 is trigger2
    assert len(trigger2.events) == 1


def test_get_reflex_trigger_with_config():
    """Test get_reflex_trigger with custom config."""
    config = TriggerConfig(name="custom", error_rate_threshold=0.8)
    trigger = get_reflex_trigger("custom_trigger", config)

    assert trigger.config.error_rate_threshold == 0.8


# ============================================================================
# Tests: Edge Cases
# ============================================================================

def test_trigger_error_rate_empty_events():
    """Test error rate calculation with no events."""
    trigger = ReflexTrigger("test_trigger")

    error_rate = trigger.compute_error_rate()
    assert error_rate is None  # Not enough samples


def test_trigger_activation_with_no_data():
    """Test activation check with no data."""
    trigger = ReflexTrigger("test_trigger")

    assert trigger.should_activate() is False


def test_trigger_mixed_event_types():
    """Test correct error rate with mixed event types."""
    config = TriggerConfig(name="test", min_samples=5)
    trigger = ReflexTrigger("test_trigger", config)

    trigger.record_success()
    trigger.record_failure()
    trigger.record_budget_violation("token_limit")  # Not counted in error rate
    trigger.record_success()
    trigger.record_failure()
    trigger.record_success()

    # Error rate should only consider success/failure (3 success, 2 failure = 5 total)
    error_rate = trigger.compute_error_rate()
    assert error_rate == 0.4  # 2 failures / 5 total
