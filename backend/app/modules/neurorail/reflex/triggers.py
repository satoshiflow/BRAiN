"""
Reflex Triggers (Phase 2 Reflex).

Automatically detects conditions that require reflex actions.
"""

import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from loguru import logger

from app.modules.neurorail.errors import ReflexTriggerActivatedError


@dataclass
class TriggerConfig:
    """Configuration for reflex trigger."""
    name: str
    error_rate_threshold: float = 0.5  # 50% error rate
    window_seconds: float = 60.0       # 1 minute window
    min_samples: int = 5               # Minimum samples to evaluate
    budget_violation_threshold: int = 3  # Max budget violations before trigger


class ReflexTrigger:
    """
    Monitors metrics and activates when thresholds are exceeded.

    Features:
    - Error rate monitoring
    - Budget violation tracking
    - Sliding window evaluation
    - Manual trigger support

    Usage:
        trigger = ReflexTrigger(
            trigger_id="error_rate_monitor",
            config=TriggerConfig(error_rate_threshold=0.5)
        )

        # Track events
        trigger.record_success()
        trigger.record_failure()

        # Check if trigger should activate
        if trigger.should_activate():
            trigger.activate(reason="Error rate threshold exceeded")
    """

    def __init__(self, trigger_id: str, config: Optional[TriggerConfig] = None):
        self.trigger_id = trigger_id
        self.config = config or TriggerConfig(name=trigger_id)

        # Metrics
        self.events: List[Dict[str, Any]] = []  # Event history with timestamps
        self.budget_violations = 0
        self.activation_count = 0
        self.last_activation_time: Optional[float] = None

    def record_success(self):
        """Record successful operation."""
        self.events.append({
            "type": "success",
            "timestamp": time.time(),
        })

    def record_failure(self, error_type: Optional[str] = None):
        """Record failed operation."""
        self.events.append({
            "type": "failure",
            "timestamp": time.time(),
            "error_type": error_type,
        })

    def record_budget_violation(self, violation_type: str):
        """Record budget violation."""
        self.budget_violations += 1
        self.events.append({
            "type": "budget_violation",
            "timestamp": time.time(),
            "violation_type": violation_type,
        })

    def _get_recent_events(self) -> List[Dict[str, Any]]:
        """Get events within sliding window."""
        cutoff = time.time() - self.config.window_seconds
        return [e for e in self.events if e["timestamp"] >= cutoff]

    def compute_error_rate(self) -> Optional[float]:
        """Compute error rate in sliding window."""
        recent = self._get_recent_events()

        if len(recent) < self.config.min_samples:
            return None  # Not enough data

        failures = sum(1 for e in recent if e["type"] == "failure")
        total = len(recent)

        return failures / total if total > 0 else 0.0

    def should_activate(self) -> bool:
        """Check if trigger should activate."""
        # Check error rate
        error_rate = self.compute_error_rate()
        if error_rate is not None and error_rate >= self.config.error_rate_threshold:
            return True

        # Check budget violations
        if self.budget_violations >= self.config.budget_violation_threshold:
            return True

        return False

    def activate(self, reason: str, context: Optional[Dict[str, Any]] = None):
        """
        Activate trigger.

        Args:
            reason: Reason for activation
            context: Optional context for error enrichment

        Raises:
            ReflexTriggerActivatedError
        """
        self.activation_count += 1
        self.last_activation_time = time.time()

        logger.warning(
            f"Reflex trigger {self.trigger_id} activated: {reason}",
            extra={
                "trigger_id": self.trigger_id,
                "reason": reason,
                "error_rate": self.compute_error_rate(),
                "budget_violations": self.budget_violations,
                "context": context,
            }
        )

        raise ReflexTriggerActivatedError(
            trigger_type=self.trigger_id,
            reason=reason,
            details={
                **context or {},
                "trigger_id": self.trigger_id,
                "error_rate": self.compute_error_rate(),
                "budget_violations": self.budget_violations,
                "activation_count": self.activation_count,
            },
        )

    def reset(self):
        """Reset trigger metrics."""
        self.events.clear()
        self.budget_violations = 0

    def get_metrics(self) -> Dict[str, Any]:
        """Get trigger metrics."""
        return {
            "trigger_id": self.trigger_id,
            "error_rate": self.compute_error_rate(),
            "budget_violations": self.budget_violations,
            "activation_count": self.activation_count,
            "last_activation_time": self.last_activation_time,
            "recent_event_count": len(self._get_recent_events()),
        }


# Trigger registry
_triggers: Dict[str, ReflexTrigger] = {}


def get_reflex_trigger(trigger_id: str, config: Optional[TriggerConfig] = None) -> ReflexTrigger:
    """Get or create reflex trigger."""
    if trigger_id not in _triggers:
        _triggers[trigger_id] = ReflexTrigger(trigger_id, config)
    return _triggers[trigger_id]
