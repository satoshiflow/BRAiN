"""
Unit tests for Reflex Actions (Phase 2 Reflex).

Tests automated reflex actions: SUSPEND, THROTTLE, ALERT, CANCEL.
"""

import pytest
from backend.app.modules.neurorail.reflex.actions import (
    ReflexAction,
    ReflexActionType,
    ReflexActionResult,
    get_reflex_action,
)
from backend.app.modules.neurorail.reflex.lifecycle import (
    JobLifecycle,
    JobLifecycleState,
    get_job_lifecycle,
)
from backend.app.modules.neurorail.errors import ReflexActionFailedError


# ============================================================================
# Tests: Suspend Action
# ============================================================================

def test_action_suspend_success():
    """Test SUSPEND action executes successfully."""
    # Setup job lifecycle
    lifecycle = get_job_lifecycle("j_123")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    # Execute suspend action
    action = ReflexAction(job_id="j_123")
    result = action.suspend(reason="Error rate too high", cooldown_seconds=60.0)

    assert result.success is True
    assert result.action_type == ReflexActionType.SUSPEND
    assert result.job_id == "j_123"
    assert result.reason == "Error rate too high"
    assert result.details["cooldown_seconds"] == 60.0

    # Verify lifecycle state changed
    assert lifecycle.current_state == JobLifecycleState.SUSPENDED


def test_action_suspend_increments_count():
    """Test SUSPEND increments action count."""
    lifecycle = get_job_lifecycle("j_suspend_count")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_suspend_count")

    action.suspend(reason="Test1", cooldown_seconds=0.0)
    lifecycle.resume()
    action.suspend(reason="Test2", cooldown_seconds=0.0)

    assert action.action_count == 2


# ============================================================================
# Tests: Throttle Action
# ============================================================================

def test_action_throttle_success():
    """Test THROTTLE action executes successfully."""
    lifecycle = get_job_lifecycle("j_456")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_456")
    result = action.throttle(reason="Budget violations", cooldown_seconds=30.0)

    assert result.success is True
    assert result.action_type == ReflexActionType.THROTTLE
    assert result.job_id == "j_456"
    assert result.reason == "Budget violations"
    assert result.details["cooldown_seconds"] == 30.0

    assert lifecycle.current_state == JobLifecycleState.THROTTLED


def test_action_throttle_increments_count():
    """Test THROTTLE increments action count."""
    lifecycle = get_job_lifecycle("j_throttle_count")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_throttle_count")

    action.throttle(reason="Test1", cooldown_seconds=0.0)
    lifecycle.resume()
    action.throttle(reason="Test2", cooldown_seconds=0.0)

    assert action.action_count == 2


# ============================================================================
# Tests: Alert Action
# ============================================================================

def test_action_alert_success():
    """Test ALERT action executes successfully."""
    action = ReflexAction(job_id="j_789")
    result = action.alert(reason="Critical failure detected", severity="critical")

    assert result.success is True
    assert result.action_type == ReflexActionType.ALERT
    assert result.job_id == "j_789"
    assert result.reason == "Critical failure detected"
    assert result.details["severity"] == "critical"


def test_action_alert_with_callback():
    """Test ALERT calls immune system callback."""
    callback_invoked = False
    callback_data = {}

    def immune_callback(reason: str, data: dict):
        nonlocal callback_invoked, callback_data
        callback_invoked = True
        callback_data = data

    action = ReflexAction(job_id="j_alert_callback", immune_callback=immune_callback)
    result = action.alert(reason="Test alert", severity="warning")

    assert callback_invoked is True
    assert callback_data["job_id"] == "j_alert_callback"
    assert callback_data["reason"] == "Test alert"
    assert callback_data["severity"] == "warning"
    assert callback_data["source"] == "reflex_system"


def test_action_alert_default_severity():
    """Test ALERT uses default severity."""
    action = ReflexAction(job_id="j_alert_default")
    result = action.alert(reason="Test")

    assert result.details["severity"] == "warning"


def test_action_alert_increments_count():
    """Test ALERT increments action count."""
    action = ReflexAction(job_id="j_alert_count")

    action.alert(reason="Test1")
    action.alert(reason="Test2")
    action.alert(reason="Test3")

    assert action.action_count == 3


# ============================================================================
# Tests: Cancel Action
# ============================================================================

def test_action_cancel_success():
    """Test CANCEL action executes successfully."""
    lifecycle = get_job_lifecycle("j_cancel_1")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_cancel_1")
    result = action.cancel(reason="Unrecoverable error")

    assert result.success is True
    assert result.action_type == ReflexActionType.CANCEL
    assert result.job_id == "j_cancel_1"
    assert result.reason == "Unrecoverable error"

    assert lifecycle.current_state == JobLifecycleState.CANCELLED


def test_action_cancel_increments_count():
    """Test CANCEL increments action count."""
    lifecycle = get_job_lifecycle("j_cancel_count")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_cancel_count")
    action.cancel(reason="Test")

    assert action.action_count == 1


# ============================================================================
# Tests: Metrics
# ============================================================================

def test_action_get_metrics():
    """Test get_metrics returns action count."""
    lifecycle = get_job_lifecycle("j_metrics")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_metrics")

    action.suspend(reason="Test1", cooldown_seconds=0.0)
    lifecycle.resume()
    action.alert(reason="Test2")
    action.throttle(reason="Test3", cooldown_seconds=0.0)

    metrics = action.get_metrics()

    assert metrics["job_id"] == "j_metrics"
    assert metrics["action_count"] == 3


# ============================================================================
# Tests: Action Registry
# ============================================================================

def test_get_reflex_action_creates_new():
    """Test get_reflex_action creates new action executor."""
    action = get_reflex_action("j_new_action")

    assert action.job_id == "j_new_action"


def test_get_reflex_action_returns_existing():
    """Test get_reflex_action returns existing action executor."""
    action1 = get_reflex_action("j_existing_action")
    action1.alert(reason="Test")

    action2 = get_reflex_action("j_existing_action")

    assert action1 is action2
    assert action2.action_count == 1


def test_get_reflex_action_with_callback():
    """Test get_reflex_action with immune callback."""
    def test_callback(reason: str, data: dict):
        pass

    action = get_reflex_action("j_callback_action", immune_callback=test_callback)

    assert action.immune_callback is test_callback


# ============================================================================
# Tests: Action Combinations
# ============================================================================

def test_action_suspend_then_alert():
    """Test SUSPEND followed by ALERT."""
    lifecycle = get_job_lifecycle("j_combo_1")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_combo_1")

    suspend_result = action.suspend(reason="Error rate high", cooldown_seconds=0.0)
    alert_result = action.alert(reason="Job suspended due to errors", severity="warning")

    assert suspend_result.success is True
    assert alert_result.success is True
    assert action.action_count == 2
    assert lifecycle.current_state == JobLifecycleState.SUSPENDED


def test_action_throttle_then_cancel():
    """Test THROTTLE followed by CANCEL."""
    lifecycle = get_job_lifecycle("j_combo_2")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_combo_2")

    throttle_result = action.throttle(reason="Budget violations", cooldown_seconds=0.0)
    cancel_result = action.cancel(reason="Violations continue, cancelling")

    assert throttle_result.success is True
    assert cancel_result.success is True
    assert action.action_count == 2
    assert lifecycle.current_state == JobLifecycleState.CANCELLED


# ============================================================================
# Tests: Error Handling
# ============================================================================

def test_action_suspend_invalid_state_raises_error():
    """Test SUSPEND from invalid state raises error."""
    # Job in COMPLETED state cannot be suspended
    lifecycle = get_job_lifecycle("j_invalid_suspend")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")
    lifecycle.transition(JobLifecycleState.COMPLETED, reason="Done")

    action = ReflexAction(job_id="j_invalid_suspend")

    with pytest.raises(ReflexActionFailedError) as exc_info:
        action.suspend(reason="Test", cooldown_seconds=0.0)

    assert exc_info.value.action_type == "SUSPEND"


def test_action_throttle_invalid_state_raises_error():
    """Test THROTTLE from invalid state raises error."""
    lifecycle = get_job_lifecycle("j_invalid_throttle")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")
    lifecycle.transition(JobLifecycleState.FAILED, reason="Error")

    action = ReflexAction(job_id="j_invalid_throttle")

    with pytest.raises(ReflexActionFailedError) as exc_info:
        action.throttle(reason="Test", cooldown_seconds=0.0)

    assert exc_info.value.action_type == "THROTTLE"


def test_action_cancel_invalid_state_raises_error():
    """Test CANCEL from invalid state raises error."""
    # Already cancelled
    lifecycle = get_job_lifecycle("j_invalid_cancel")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")
    lifecycle.transition(JobLifecycleState.CANCELLED, reason="Cancelled")

    action = ReflexAction(job_id="j_invalid_cancel")

    with pytest.raises(ReflexActionFailedError) as exc_info:
        action.cancel(reason="Test")

    assert exc_info.value.action_type == "CANCEL"


# ============================================================================
# Tests: Edge Cases
# ============================================================================

def test_action_multiple_alerts_allowed():
    """Test multiple ALERT actions are allowed."""
    action = ReflexAction(job_id="j_multi_alert")

    action.alert(reason="Alert 1")
    action.alert(reason="Alert 2")
    action.alert(reason="Alert 3")

    assert action.action_count == 3


def test_action_result_structure():
    """Test ReflexActionResult has correct structure."""
    lifecycle = get_job_lifecycle("j_result_test")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    action = ReflexAction(job_id="j_result_test")
    result = action.suspend(reason="Test", cooldown_seconds=10.0)

    assert isinstance(result, ReflexActionResult)
    assert hasattr(result, "action_type")
    assert hasattr(result, "success")
    assert hasattr(result, "job_id")
    assert hasattr(result, "reason")
    assert hasattr(result, "details")
