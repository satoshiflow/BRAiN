"""
NeuroRail Lifecycle Schemas.

Defines state machines and transition events for:
- Mission lifecycle
- Job lifecycle
- Attempt lifecycle

All state transitions are explicit and validated to prevent illegal states.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


# ============================================================================
# State Enumerations
# ============================================================================

class MissionState(str, Enum):
    """
    Mission state machine states.

    State flow:
    PENDING → PLANNING → PLANNED → EXECUTING → COMPLETED
                                            ↓
                                     FAILED / CANCELLED / TIMEOUT
    """
    PENDING = "pending"           # Created but not started
    PLANNING = "planning"         # Generating execution plan
    PLANNED = "planned"           # Plan ready, waiting to execute
    EXECUTING = "executing"       # Jobs running
    COMPLETED = "completed"       # All jobs succeeded
    FAILED = "failed"             # Unrecoverable failure
    CANCELLED = "cancelled"       # User cancelled
    TIMEOUT = "timeout"           # Budget exceeded


class JobState(str, Enum):
    """
    Job state machine states.

    State flow:
    PENDING → READY → RUNNING → SUCCEEDED
                             ↓
                      FAILED_MECHANICAL (retriable) → RUNNING (retry)
                      FAILED_ETHICAL (non-retriable)
                      TIMEOUT
                      CANCELLED
    """
    PENDING = "pending"                     # Created, dependencies not satisfied
    READY = "ready"                         # Dependencies satisfied, ready to run
    RUNNING = "running"                     # Currently executing
    SUCCEEDED = "succeeded"                 # Completed successfully
    FAILED_MECHANICAL = "failed_mechanical" # Retriable failure (timeout, network, etc.)
    FAILED_ETHICAL = "failed_ethical"       # Non-retriable failure (policy violation, etc.)
    TIMEOUT = "timeout"                     # Budget timeout
    CANCELLED = "cancelled"                 # Cancelled by user or system


class AttemptState(str, Enum):
    """
    Attempt state machine states.

    State flow:
    CREATED → RUNNING → SUCCEEDED
                     ↓
                  FAILED_TIMEOUT
                  FAILED_RESOURCE
                  FAILED_ERROR
    """
    CREATED = "created"                     # Attempt created
    RUNNING = "running"                     # Attempt executing
    SUCCEEDED = "succeeded"                 # Attempt succeeded
    FAILED_TIMEOUT = "failed_timeout"       # Timeout exceeded
    FAILED_RESOURCE = "failed_resource"     # Resource exhaustion
    FAILED_ERROR = "failed_error"           # Other error


# ============================================================================
# Transition Events
# ============================================================================

class StateTransitionEvent(BaseModel):
    """
    State transition event.

    Records a single state transition with full context.
    """
    event_id: str = Field(
        default_factory=lambda: f"evt_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:14]}",
        description="Unique event identifier"
    )
    entity_type: str = Field(
        ...,
        description="Entity type: mission, plan, job, attempt"
    )
    entity_id: str = Field(..., description="Entity identifier")

    # State transition
    from_state: Optional[str] = Field(
        None,
        description="Previous state (None for creation)"
    )
    to_state: str = Field(..., description="New state")
    transition: str = Field(
        ...,
        description="Transition action: create, start, complete, fail, timeout, cancel, retry"
    )

    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Context
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Transition metadata (reason, error_code, etc.)"
    )
    caused_by: Optional[str] = Field(
        None,
        description="Event ID that triggered this transition"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_20251230140000",
                "entity_type": "job",
                "entity_id": "j_123456789abc",
                "from_state": "ready",
                "to_state": "running",
                "transition": "start",
                "timestamp": "2025-12-30T14:00:00Z",
                "metadata": {"executor": "worker_1"},
                "caused_by": None
            }
        }


# ============================================================================
# State Transition Requests
# ============================================================================

class TransitionRequest(BaseModel):
    """Request to transition an entity to a new state."""
    entity_id: str = Field(..., description="Entity identifier")
    transition: str = Field(
        ...,
        description="Transition action: start, complete, fail, timeout, cancel, retry"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Transition metadata"
    )
    caused_by: Optional[str] = Field(
        None,
        description="Event ID that triggered this transition"
    )


# ============================================================================
# Current State Response
# ============================================================================

class EntityStateResponse(BaseModel):
    """Response for current state query."""
    entity_type: str
    entity_id: str
    current_state: str
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# State History Response
# ============================================================================

class StateHistoryResponse(BaseModel):
    """Response for state history query."""
    entity_type: str
    entity_id: str
    transitions: List[StateTransitionEvent]
    total_transitions: int


# ============================================================================
# Allowed Transitions (State Machine Definitions)
# ============================================================================

# Mission allowed transitions
MISSION_TRANSITIONS: Dict[Optional[MissionState], List[MissionState]] = {
    None: [MissionState.PENDING],  # Creation
    MissionState.PENDING: [MissionState.PLANNING, MissionState.CANCELLED],
    MissionState.PLANNING: [MissionState.PLANNED, MissionState.FAILED, MissionState.CANCELLED],
    MissionState.PLANNED: [MissionState.EXECUTING, MissionState.CANCELLED],
    MissionState.EXECUTING: [
        MissionState.COMPLETED,
        MissionState.FAILED,
        MissionState.TIMEOUT,
        MissionState.CANCELLED
    ],
    # Terminal states (no further transitions)
    MissionState.COMPLETED: [],
    MissionState.FAILED: [],
    MissionState.TIMEOUT: [],
    MissionState.CANCELLED: [],
}

# Job allowed transitions
JOB_TRANSITIONS: Dict[Optional[JobState], List[JobState]] = {
    None: [JobState.PENDING],  # Creation
    JobState.PENDING: [JobState.READY, JobState.CANCELLED],
    JobState.READY: [JobState.RUNNING, JobState.CANCELLED],
    JobState.RUNNING: [
        JobState.SUCCEEDED,
        JobState.FAILED_MECHANICAL,
        JobState.FAILED_ETHICAL,
        JobState.TIMEOUT,
        JobState.CANCELLED
    ],
    # Mechanical failures can be retried
    JobState.FAILED_MECHANICAL: [JobState.RUNNING, JobState.CANCELLED],
    # Terminal states (no further transitions)
    JobState.SUCCEEDED: [],
    JobState.FAILED_ETHICAL: [],
    JobState.TIMEOUT: [],
    JobState.CANCELLED: [],
}

# Attempt allowed transitions
ATTEMPT_TRANSITIONS: Dict[Optional[AttemptState], List[AttemptState]] = {
    None: [AttemptState.CREATED],  # Creation
    AttemptState.CREATED: [AttemptState.RUNNING],
    AttemptState.RUNNING: [
        AttemptState.SUCCEEDED,
        AttemptState.FAILED_TIMEOUT,
        AttemptState.FAILED_RESOURCE,
        AttemptState.FAILED_ERROR
    ],
    # Terminal states (no further transitions)
    AttemptState.SUCCEEDED: [],
    AttemptState.FAILED_TIMEOUT: [],
    AttemptState.FAILED_RESOURCE: [],
    AttemptState.FAILED_ERROR: [],
}


def is_valid_transition(
    entity_type: str,
    from_state: Optional[str],
    to_state: str
) -> bool:
    """
    Check if a state transition is valid.

    Args:
        entity_type: Entity type (mission, job, attempt)
        from_state: Current state (None for creation)
        to_state: Target state

    Returns:
        True if transition is allowed, False otherwise
    """
    if entity_type == "mission":
        transitions = MISSION_TRANSITIONS
        from_enum = MissionState(from_state) if from_state else None
        to_enum = MissionState(to_state)
    elif entity_type == "job":
        transitions = JOB_TRANSITIONS
        from_enum = JobState(from_state) if from_state else None
        to_enum = JobState(to_state)
    elif entity_type == "attempt":
        transitions = ATTEMPT_TRANSITIONS
        from_enum = AttemptState(from_state) if from_state else None
        to_enum = AttemptState(to_state)
    else:
        return False

    allowed_states = transitions.get(from_enum, [])
    return to_enum in allowed_states


def get_allowed_transitions(
    entity_type: str,
    current_state: Optional[str]
) -> List[str]:
    """
    Get list of allowed next states.

    Args:
        entity_type: Entity type (mission, job, attempt)
        current_state: Current state (None for creation)

    Returns:
        List of allowed next states
    """
    if entity_type == "mission":
        transitions = MISSION_TRANSITIONS
        state_enum = MissionState(current_state) if current_state else None
    elif entity_type == "job":
        transitions = JOB_TRANSITIONS
        state_enum = JobState(current_state) if current_state else None
    elif entity_type == "attempt":
        transitions = ATTEMPT_TRANSITIONS
        state_enum = AttemptState(current_state) if current_state else None
    else:
        return []

    allowed = transitions.get(state_enum, [])
    return [state.value for state in allowed]
