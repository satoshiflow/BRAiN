from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class AXEEventType(str, Enum):
    RUN_CREATED = "axe.run.created"
    RUN_STATE_CHANGED = "axe.run.state_changed"
    RUN_SUCCEEDED = "axe.run.succeeded"
    RUN_FAILED = "axe.run.failed"
    RUN_CANCELLED = "axe.run.cancelled"
    CAPABILITY_STARTED = "axe.capability.started"
    CAPABILITY_PROGRESS = "axe.capability.progress"
    CAPABILITY_COMPLETED = "axe.capability.completed"
    CAPABILITY_FAILED = "axe.capability.failed"
    TOKEN_STREAM = "axe.token.stream"
    TOKEN_COMPLETE = "axe.token.complete"
    ERROR = "axe.error"


class AXERunState(str, Enum):
    QUEUED = "queued"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AXEEvent(BaseModel):
    event_type: AXEEventType
    run_id: UUID
    sequence: int
    timestamp: str
    data: dict[str, Any]


class AXERunStateChangedEventData(BaseModel):
    previous_state: AXERunState | None
    current_state: AXERunState
    reason: str | None = None


class AXETokenStreamEventData(BaseModel):
    delta: str
    finish_reason: str | None = None


class AXEErrorEventData(BaseModel):
    code: str
    message: str
    recoverable: bool = False
