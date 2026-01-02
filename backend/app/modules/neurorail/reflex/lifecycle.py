"""
Lifecycle FSM (Phase 2 Reflex).

Job lifecycle state machine with reflex-triggered transitions.
Enforces valid state transitions and cooldown periods.
"""

import time
from typing import Optional, Dict, List, Any
from enum import Enum
from dataclasses import dataclass
from loguru import logger

from backend.app.modules.neurorail.errors import ReflexLifecycleInvalidError


class JobLifecycleState(str, Enum):
    """Job lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    SUSPENDED = "suspended"      # Reflex-triggered pause
    THROTTLED = "throttled"       # Reflex-triggered rate limiting
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Allowed state transitions
ALLOWED_TRANSITIONS: Dict[JobLifecycleState, List[JobLifecycleState]] = {
    JobLifecycleState.PENDING: [
        JobLifecycleState.RUNNING,
        JobLifecycleState.CANCELLED,
    ],
    JobLifecycleState.RUNNING: [
        JobLifecycleState.SUSPENDED,
        JobLifecycleState.THROTTLED,
        JobLifecycleState.COMPLETED,
        JobLifecycleState.FAILED,
        JobLifecycleState.CANCELLED,
    ],
    JobLifecycleState.SUSPENDED: [
        JobLifecycleState.RUNNING,  # Resume
        JobLifecycleState.CANCELLED,
    ],
    JobLifecycleState.THROTTLED: [
        JobLifecycleState.RUNNING,  # Resume normal speed
        JobLifecycleState.SUSPENDED,
        JobLifecycleState.CANCELLED,
    ],
    # Terminal states have no transitions
    JobLifecycleState.COMPLETED: [],
    JobLifecycleState.FAILED: [],
    JobLifecycleState.CANCELLED: [],
}


@dataclass
class LifecycleTransition:
    """Record of a lifecycle state transition."""
    from_state: JobLifecycleState
    to_state: JobLifecycleState
    timestamp: float
    reason: str
    triggered_by: Optional[str] = None  # "reflex", "manual", "system"


class JobLifecycle:
    """
    Job lifecycle state machine with reflex support.

    Features:
    - Enforces valid state transitions
    - Tracks transition history
    - Cooldown periods for reflex actions
    - Immune system integration

    Usage:
        lifecycle = JobLifecycle(job_id="j_123")

        # Normal transition
        lifecycle.transition(JobLifecycleState.RUNNING, reason="Job started")

        # Reflex-triggered transition
        lifecycle.suspend(reason="Error rate threshold exceeded", triggered_by="reflex")

        # Resume
        lifecycle.resume()
    """

    def __init__(self, job_id: str, initial_state: JobLifecycleState = JobLifecycleState.PENDING):
        """
        Initialize job lifecycle.

        Args:
            job_id: Job identifier
            initial_state: Initial lifecycle state
        """
        self.job_id = job_id
        self.current_state = initial_state
        self.history: List[LifecycleTransition] = []
        self.cooldown_until: Optional[float] = None  # Timestamp when cooldown expires
        self.suspend_count = 0
        self.throttle_count = 0

    def transition(
        self,
        to_state: JobLifecycleState,
        reason: str,
        triggered_by: Optional[str] = None,
    ) -> LifecycleTransition:
        """
        Transition to new state.

        Args:
            to_state: Target state
            reason: Reason for transition
            triggered_by: Who triggered the transition ("reflex", "manual", "system")

        Returns:
            LifecycleTransition record

        Raises:
            ReflexLifecycleInvalidError: If transition is invalid
        """
        # Check if transition is allowed
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, [])
        if to_state not in allowed:
            raise ReflexLifecycleInvalidError(
                from_state=self.current_state,
                to_state=to_state,
                details={
                    "job_id": self.job_id,
                    "reason": reason,
                    "allowed_transitions": [s.value for s in allowed],
                },
            )

        # Create transition record
        transition = LifecycleTransition(
            from_state=self.current_state,
            to_state=to_state,
            timestamp=time.time(),
            reason=reason,
            triggered_by=triggered_by,
        )

        logger.info(
            f"Job {self.job_id} lifecycle transition: {self.current_state} → {to_state}",
            extra={
                "job_id": self.job_id,
                "from_state": self.current_state,
                "to_state": to_state,
                "reason": reason,
                "triggered_by": triggered_by,
            }
        )

        # Update state
        self.current_state = to_state
        self.history.append(transition)

        # Track suspend/throttle counts
        if to_state == JobLifecycleState.SUSPENDED:
            self.suspend_count += 1
        elif to_state == JobLifecycleState.THROTTLED:
            self.throttle_count += 1

        return transition

    def suspend(self, reason: str, cooldown_seconds: float = 60.0, triggered_by: str = "reflex"):
        """Suspend job (reflex action)."""
        transition = self.transition(JobLifecycleState.SUSPENDED, reason, triggered_by)
        self.cooldown_until = time.time() + cooldown_seconds

        logger.warning(
            f"Job {self.job_id} suspended for {cooldown_seconds}s: {reason}",
            extra={"job_id": self.job_id, "cooldown_seconds": cooldown_seconds}
        )

        return transition

    def throttle(self, reason: str, cooldown_seconds: float = 30.0, triggered_by: str = "reflex"):
        """Throttle job (reflex action)."""
        transition = self.transition(JobLifecycleState.THROTTLED, reason, triggered_by)
        self.cooldown_until = time.time() + cooldown_seconds

        logger.warning(
            f"Job {self.job_id} throttled for {cooldown_seconds}s: {reason}",
            extra={"job_id": self.job_id, "cooldown_seconds": cooldown_seconds}
        )

        return transition

    def resume(self, reason: str = "Resume after reflex cooldown"):
        """Resume job from SUSPENDED or THROTTLED."""
        if self.current_state not in [JobLifecycleState.SUSPENDED, JobLifecycleState.THROTTLED]:
            raise ReflexLifecycleInvalidError(
                from_state=self.current_state,
                to_state=JobLifecycleState.RUNNING,
                details={"job_id": self.job_id, "reason": "Can only resume from SUSPENDED or THROTTLED"},
            )

        self.cooldown_until = None
        return self.transition(JobLifecycleState.RUNNING, reason, "system")

    def can_resume(self) -> bool:
        """Check if job can resume (cooldown expired)."""
        if self.cooldown_until is None:
            return True
        return time.time() >= self.cooldown_until

    def get_state_duration(self) -> float:
        """Get duration in current state (seconds)."""
        if not self.history:
            return 0.0
        last_transition = self.history[-1]
        return time.time() - last_transition.timestamp

    def get_metrics(self) -> Dict[str, Any]:
        """Get lifecycle metrics."""
        return {
            "job_id": self.job_id,
            "current_state": self.current_state,
            "suspend_count": self.suspend_count,
            "throttle_count": self.throttle_count,
            "transition_count": len(self.history),
            "state_duration_seconds": self.get_state_duration(),
            "cooldown_active": self.cooldown_until is not None and not self.can_resume(),
        }


# Lifecycle registry
_job_lifecycles: Dict[str, JobLifecycle] = {}


def get_job_lifecycle(job_id: str) -> JobLifecycle:
    """Get or create job lifecycle."""
    if job_id not in _job_lifecycles:
        _job_lifecycles[job_id] = JobLifecycle(job_id)
    return _job_lifecycles[job_id]
