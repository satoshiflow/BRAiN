"""
Unit tests for Lifecycle FSM (Phase 2 Reflex).

Tests state transitions, cooldown periods, and reflex actions.
"""

import pytest
import time
from backend.app.modules.neurorail.reflex.lifecycle import (
    JobLifecycle,
    JobLifecycleState,
    ALLOWED_TRANSITIONS,
    get_job_lifecycle,
)
from backend.app.modules.neurorail.errors import ReflexLifecycleInvalidError


# ============================================================================
# Tests: Basic State Transitions
# ============================================================================

def test_lifecycle_starts_pending():
    """Test lifecycle starts in PENDING state."""
    lifecycle = JobLifecycle("j_123")
    assert lifecycle.current_state == JobLifecycleState.PENDING


def test_lifecycle_valid_transition():
    """Test valid state transition."""
    lifecycle = JobLifecycle("j_123")

    transition = lifecycle.transition(
        JobLifecycleState.RUNNING,
        reason="Job started",
        triggered_by="system"
    )

    assert lifecycle.current_state == JobLifecycleState.RUNNING
    assert transition.from_state == JobLifecycleState.PENDING
    assert transition.to_state == JobLifecycleState.RUNNING
    assert transition.reason == "Job started"
    assert len(lifecycle.history) == 1


def test_lifecycle_invalid_transition():
    """Test invalid state transition raises error."""
    lifecycle = JobLifecycle("j_123")

    with pytest.raises(ReflexLifecycleInvalidError) as exc_info:
        lifecycle.transition(JobLifecycleState.COMPLETED, reason="Invalid")

    assert "PENDING" in str(exc_info.value)
    assert "COMPLETED" in str(exc_info.value)


def test_lifecycle_terminal_states_no_transitions():
    """Test terminal states cannot transition."""
    lifecycle = JobLifecycle("j_123", initial_state=JobLifecycleState.COMPLETED)

    with pytest.raises(ReflexLifecycleInvalidError):
        lifecycle.transition(JobLifecycleState.RUNNING, reason="Invalid")


def test_lifecycle_transition_history():
    """Test transition history is tracked."""
    lifecycle = JobLifecycle("j_123")

    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")
    lifecycle.transition(JobLifecycleState.SUSPENDED, reason="Suspend")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Resume")

    assert len(lifecycle.history) == 3
    assert lifecycle.history[0].to_state == JobLifecycleState.RUNNING
    assert lifecycle.history[1].to_state == JobLifecycleState.SUSPENDED
    assert lifecycle.history[2].to_state == JobLifecycleState.RUNNING


# ============================================================================
# Tests: Suspend/Resume
# ============================================================================

def test_lifecycle_suspend():
    """Test suspend action."""
    lifecycle = JobLifecycle("j_123", initial_state=JobLifecycleState.RUNNING)

    transition = lifecycle.suspend(
        reason="Error rate too high",
        cooldown_seconds=60.0,
        triggered_by="reflex"
    )

    assert lifecycle.current_state == JobLifecycleState.SUSPENDED
    assert transition.triggered_by == "reflex"
    assert lifecycle.cooldown_until is not None
    assert lifecycle.suspend_count == 1


def test_lifecycle_throttle():
    """Test throttle action."""
    lifecycle = JobLifecycle("j_123", initial_state=JobLifecycleState.RUNNING)

    transition = lifecycle.throttle(
        reason="Budget violations",
        cooldown_seconds=30.0,
        triggered_by="reflex"
    )

    assert lifecycle.current_state == JobLifecycleState.THROTTLED
    assert transition.triggered_by == "reflex"
    assert lifecycle.cooldown_until is not None
    assert lifecycle.throttle_count == 1


def test_lifecycle_resume_from_suspended():
    """Test resume from SUSPENDED state."""
    lifecycle = JobLifecycle("j_123", initial_state=JobLifecycleState.RUNNING)
    lifecycle.suspend(reason="Test suspend", cooldown_seconds=0.0)

    transition = lifecycle.resume(reason="Resume normal operation")

    assert lifecycle.current_state == JobLifecycleState.RUNNING
    assert lifecycle.cooldown_until is None
    assert transition.triggered_by == "system"


def test_lifecycle_resume_from_throttled():
    """Test resume from THROTTLED state."""
    lifecycle = JobLifecycle("j_123", initial_state=JobLifecycleState.RUNNING)
    lifecycle.throttle(reason="Test throttle", cooldown_seconds=0.0)

    transition = lifecycle.resume(reason="Resume normal speed")

    assert lifecycle.current_state == JobLifecycleState.RUNNING
    assert lifecycle.cooldown_until is None


def test_lifecycle_resume_invalid_state():
    """Test resume from invalid state raises error."""
    lifecycle = JobLifecycle("j_123", initial_state=JobLifecycleState.RUNNING)

    with pytest.raises(ReflexLifecycleInvalidError) as exc_info:
        lifecycle.resume()

    assert "Can only resume from SUSPENDED or THROTTLED" in str(exc_info.value)


# ============================================================================
# Tests: Cooldown Periods
# ============================================================================

def test_lifecycle_can_resume_no_cooldown():
    """Test can_resume returns True when no cooldown."""
    lifecycle = JobLifecycle("j_123")
    assert lifecycle.can_resume() is True


def test_lifecycle_can_resume_cooldown_active():
    """Test can_resume returns False during cooldown."""
    lifecycle = JobLifecycle("j_123", initial_state=JobLifecycleState.RUNNING)
    lifecycle.suspend(reason="Test", cooldown_seconds=10.0)

    assert lifecycle.can_resume() is False


def test_lifecycle_can_resume_cooldown_expired():
    """Test can_resume returns True after cooldown expires."""
    lifecycle = JobLifecycle("j_123", initial_state=JobLifecycleState.RUNNING)
    lifecycle.suspend(reason="Test", cooldown_seconds=0.01)  # 10ms cooldown

    time.sleep(0.02)  # Wait for cooldown to expire

    assert lifecycle.can_resume() is True


# ============================================================================
# Tests: Metrics
# ============================================================================

def test_lifecycle_get_state_duration():
    """Test get_state_duration returns time in current state."""
    lifecycle = JobLifecycle("j_123")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")

    time.sleep(0.05)  # 50ms

    duration = lifecycle.get_state_duration()
    assert duration >= 0.05  # At least 50ms


def test_lifecycle_get_metrics():
    """Test get_metrics returns comprehensive metrics."""
    lifecycle = JobLifecycle("j_123")
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start")
    lifecycle.suspend(reason="Test1", cooldown_seconds=0.0)
    lifecycle.resume()
    lifecycle.throttle(reason="Test2", cooldown_seconds=0.0)

    metrics = lifecycle.get_metrics()

    assert metrics["job_id"] == "j_123"
    assert metrics["current_state"] == JobLifecycleState.THROTTLED
    assert metrics["suspend_count"] == 1
    assert metrics["throttle_count"] == 1
    assert metrics["transition_count"] == 4  # PENDING→RUNNING→SUSPENDED→RUNNING→THROTTLED


# ============================================================================
# Tests: Lifecycle Registry
# ============================================================================

def test_get_job_lifecycle_creates_new():
    """Test get_job_lifecycle creates new lifecycle if not exists."""
    lifecycle = get_job_lifecycle("j_new_123")

    assert lifecycle.job_id == "j_new_123"
    assert lifecycle.current_state == JobLifecycleState.PENDING


def test_get_job_lifecycle_returns_existing():
    """Test get_job_lifecycle returns existing lifecycle."""
    lifecycle1 = get_job_lifecycle("j_existing_456")
    lifecycle1.transition(JobLifecycleState.RUNNING, reason="Start")

    lifecycle2 = get_job_lifecycle("j_existing_456")

    assert lifecycle1 is lifecycle2
    assert lifecycle2.current_state == JobLifecycleState.RUNNING


# ============================================================================
# Tests: State Transition Chains
# ============================================================================

def test_lifecycle_complete_workflow():
    """Test complete lifecycle workflow."""
    lifecycle = JobLifecycle("j_123")

    # PENDING → RUNNING
    lifecycle.transition(JobLifecycleState.RUNNING, reason="Start job")
    assert lifecycle.current_state == JobLifecycleState.RUNNING

    # RUNNING → SUSPENDED (reflex action)
    lifecycle.suspend(reason="Error rate high", cooldown_seconds=0.0, triggered_by="reflex")
    assert lifecycle.current_state == JobLifecycleState.SUSPENDED

    # SUSPENDED → RUNNING (resume)
    lifecycle.resume(reason="Cooldown expired")
    assert lifecycle.current_state == JobLifecycleState.RUNNING

    # RUNNING → COMPLETED
    lifecycle.transition(JobLifecycleState.COMPLETED, reason="Job finished")
    assert lifecycle.current_state == JobLifecycleState.COMPLETED

    # Verify full history
    assert len(lifecycle.history) == 4


def test_lifecycle_cancel_from_any_state():
    """Test cancellation from various states."""
    # From PENDING
    lifecycle1 = JobLifecycle("j_1")
    lifecycle1.transition(JobLifecycleState.CANCELLED, reason="User cancelled")
    assert lifecycle1.current_state == JobLifecycleState.CANCELLED

    # From RUNNING
    lifecycle2 = JobLifecycle("j_2", initial_state=JobLifecycleState.RUNNING)
    lifecycle2.transition(JobLifecycleState.CANCELLED, reason="User cancelled")
    assert lifecycle2.current_state == JobLifecycleState.CANCELLED

    # From SUSPENDED
    lifecycle3 = JobLifecycle("j_3", initial_state=JobLifecycleState.SUSPENDED)
    lifecycle3.transition(JobLifecycleState.CANCELLED, reason="User cancelled")
    assert lifecycle3.current_state == JobLifecycleState.CANCELLED
