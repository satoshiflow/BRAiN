"""
Reflex Actions (Phase 2 Reflex).

Automated actions triggered by reflex system.
"""

from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass
from loguru import logger

from app.modules.neurorail.reflex.lifecycle import JobLifecycle, get_job_lifecycle
from app.modules.neurorail.errors import ReflexActionFailedError


class ReflexActionType(str, Enum):
    """Types of reflex actions."""
    SUSPEND = "suspend"      # Pause job execution
    THROTTLE = "throttle"    # Reduce execution rate
    ALERT = "alert"          # Notify immune system
    CANCEL = "cancel"        # Terminate job


@dataclass
class ReflexActionResult:
    """Result of reflex action execution."""
    action_type: ReflexActionType
    success: bool
    job_id: Optional[str] = None
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ReflexAction:
    """
    Executes automated actions in response to triggers.

    Features:
    - SUSPEND: Pause job with cooldown
    - THROTTLE: Reduce execution rate
    - ALERT: Notify immune system
    - CANCEL: Terminate job

    Usage:
        action = ReflexAction(job_id="j_123")

        # Suspend job
        result = action.suspend(reason="Error rate too high", cooldown_seconds=60.0)

        # Throttle job
        result = action.throttle(reason="Budget violations", cooldown_seconds=30.0)

        # Alert immune system
        result = action.alert(reason="Critical failure detected")

        # Cancel job
        result = action.cancel(reason="Unrecoverable error")
    """

    def __init__(
        self,
        job_id: str,
        immune_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        """
        Initialize reflex action executor.

        Args:
            job_id: Job identifier
            immune_callback: Optional callback for immune system alerts
        """
        self.job_id = job_id
        self.immune_callback = immune_callback
        self.action_count = 0

    def suspend(self, reason: str, cooldown_seconds: float = 60.0) -> ReflexActionResult:
        """
        Suspend job execution.

        Args:
            reason: Reason for suspension
            cooldown_seconds: Cooldown period in seconds

        Returns:
            ReflexActionResult
        """
        try:
            lifecycle = get_job_lifecycle(self.job_id)
            lifecycle.suspend(reason, cooldown_seconds, triggered_by="reflex")

            self.action_count += 1

            logger.warning(
                f"Reflex action SUSPEND executed for job {self.job_id}",
                extra={
                    "job_id": self.job_id,
                    "reason": reason,
                    "cooldown_seconds": cooldown_seconds,
                }
            )

            return ReflexActionResult(
                action_type=ReflexActionType.SUSPEND,
                success=True,
                job_id=self.job_id,
                reason=reason,
                details={"cooldown_seconds": cooldown_seconds},
            )

        except Exception as e:
            logger.error(
                f"Reflex action SUSPEND failed for job {self.job_id}: {e}",
                extra={"job_id": self.job_id, "reason": reason}
            )

            raise ReflexActionFailedError(
                action_type="SUSPEND",
                reason=str(e),
                details={"job_id": self.job_id},
            )

    def throttle(self, reason: str, cooldown_seconds: float = 30.0) -> ReflexActionResult:
        """
        Throttle job execution rate.

        Args:
            reason: Reason for throttling
            cooldown_seconds: Throttle duration in seconds

        Returns:
            ReflexActionResult
        """
        try:
            lifecycle = get_job_lifecycle(self.job_id)
            lifecycle.throttle(reason, cooldown_seconds, triggered_by="reflex")

            self.action_count += 1

            logger.warning(
                f"Reflex action THROTTLE executed for job {self.job_id}",
                extra={
                    "job_id": self.job_id,
                    "reason": reason,
                    "cooldown_seconds": cooldown_seconds,
                }
            )

            return ReflexActionResult(
                action_type=ReflexActionType.THROTTLE,
                success=True,
                job_id=self.job_id,
                reason=reason,
                details={"cooldown_seconds": cooldown_seconds},
            )

        except Exception as e:
            logger.error(
                f"Reflex action THROTTLE failed for job {self.job_id}: {e}",
                extra={"job_id": self.job_id, "reason": reason}
            )

            raise ReflexActionFailedError(
                action_type="THROTTLE",
                reason=str(e),
                details={"job_id": self.job_id},
            )

    def alert(self, reason: str, severity: str = "warning") -> ReflexActionResult:
        """
        Alert immune system.

        Args:
            reason: Reason for alert
            severity: Alert severity (info/warning/error/critical)

        Returns:
            ReflexActionResult
        """
        try:
            alert_data = {
                "job_id": self.job_id,
                "reason": reason,
                "severity": severity,
                "source": "reflex_system",
            }

            # Call immune system callback if provided
            if self.immune_callback:
                self.immune_callback(reason, alert_data)

            self.action_count += 1

            logger.warning(
                f"Reflex action ALERT executed for job {self.job_id}",
                extra={
                    "job_id": self.job_id,
                    "reason": reason,
                    "severity": severity,
                }
            )

            return ReflexActionResult(
                action_type=ReflexActionType.ALERT,
                success=True,
                job_id=self.job_id,
                reason=reason,
                details={"severity": severity},
            )

        except Exception as e:
            logger.error(
                f"Reflex action ALERT failed for job {self.job_id}: {e}",
                extra={"job_id": self.job_id, "reason": reason}
            )

            raise ReflexActionFailedError(
                action_type="ALERT",
                reason=str(e),
                details={"job_id": self.job_id},
            )

    def cancel(self, reason: str) -> ReflexActionResult:
        """
        Cancel job execution.

        Args:
            reason: Reason for cancellation

        Returns:
            ReflexActionResult
        """
        try:
            lifecycle = get_job_lifecycle(self.job_id)
            from app.modules.neurorail.reflex.lifecycle import JobLifecycleState
            lifecycle.transition(JobLifecycleState.CANCELLED, reason, triggered_by="reflex")

            self.action_count += 1

            logger.error(
                f"Reflex action CANCEL executed for job {self.job_id}",
                extra={
                    "job_id": self.job_id,
                    "reason": reason,
                }
            )

            return ReflexActionResult(
                action_type=ReflexActionType.CANCEL,
                success=True,
                job_id=self.job_id,
                reason=reason,
            )

        except Exception as e:
            logger.error(
                f"Reflex action CANCEL failed for job {self.job_id}: {e}",
                extra={"job_id": self.job_id, "reason": reason}
            )

            raise ReflexActionFailedError(
                action_type="CANCEL",
                reason=str(e),
                details={"job_id": self.job_id},
            )

    def get_metrics(self) -> Dict[str, Any]:
        """Get action execution metrics."""
        return {
            "job_id": self.job_id,
            "action_count": self.action_count,
        }


# Action registry
_reflex_actions: Dict[str, ReflexAction] = {}


def get_reflex_action(job_id: str, immune_callback: Optional[Callable] = None) -> ReflexAction:
    """Get or create reflex action executor for job."""
    if job_id not in _reflex_actions:
        _reflex_actions[job_id] = ReflexAction(job_id, immune_callback)
    return _reflex_actions[job_id]
