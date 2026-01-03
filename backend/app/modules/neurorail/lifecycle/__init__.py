"""
NeuroRail Lifecycle Module.

Manages entity state machines and transitions:
- Mission lifecycle (PENDING → PLANNING → EXECUTING → COMPLETED)
- Job lifecycle (PENDING → READY → RUNNING → SUCCEEDED/FAILED)
- Attempt lifecycle (CREATED → RUNNING → SUCCEEDED/FAILED)
"""

from app.modules.neurorail.lifecycle.schemas import (
    MissionState,
    JobState,
    AttemptState,
    StateTransitionEvent,
    TransitionRequest,
    EntityStateResponse,
    StateHistoryResponse,
    is_valid_transition,
    get_allowed_transitions,
)
from app.modules.neurorail.lifecycle.service import (
    LifecycleService,
    get_lifecycle_service,
)
from app.modules.neurorail.lifecycle.router import router

__all__ = [
    # State enums
    "MissionState",
    "JobState",
    "AttemptState",
    # Schemas
    "StateTransitionEvent",
    "TransitionRequest",
    "EntityStateResponse",
    "StateHistoryResponse",
    # State machine utilities
    "is_valid_transition",
    "get_allowed_transitions",
    # Service
    "LifecycleService",
    "get_lifecycle_service",
    # Router
    "router",
]
