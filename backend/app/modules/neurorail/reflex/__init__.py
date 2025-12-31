"""
NeuroRail Reflex System Module (Phase 2).

Automatic failure response and recovery system:
- Circuit breaker pattern
- Lifecycle state machines
- Reflex triggers
- Reflex actions
"""

from backend.app.modules.neurorail.reflex.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    get_circuit_breaker,
)
from backend.app.modules.neurorail.reflex.lifecycle import (
    JobLifecycle,
    JobLifecycleState,
    ALLOWED_TRANSITIONS,
    get_job_lifecycle,
)
from backend.app.modules.neurorail.reflex.triggers import (
    ReflexTrigger,
    TriggerConfig,
    get_reflex_trigger,
)
from backend.app.modules.neurorail.reflex.actions import (
    ReflexAction,
    ReflexActionType,
    ReflexActionResult,
    get_reflex_action,
)

__all__ = [
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerConfig",
    "get_circuit_breaker",
    "JobLifecycle",
    "JobLifecycleState",
    "ALLOWED_TRANSITIONS",
    "get_job_lifecycle",
    "ReflexTrigger",
    "TriggerConfig",
    "get_reflex_trigger",
    "ReflexAction",
    "ReflexActionType",
    "ReflexActionResult",
    "get_reflex_action",
]
