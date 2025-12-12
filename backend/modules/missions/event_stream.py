# backend/modules/missions/event_stream.py
"""
Simple EventStream stub implementation.

This replaces the removed mission_control_core.core module with a minimal
implementation that maintains API compatibility.
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class EventType(str, Enum):
    """Event types for mission/task lifecycle."""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"


class Event(BaseModel):
    """Event model."""
    event_id: str
    event_type: EventType
    timestamp: float
    source: str
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    data: Dict[str, Any] = {}


class EventStream:
    """
    Minimal EventStream implementation.

    Stores events in memory (not persistent).
    For production use, implement Redis-based storage.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self._events: List[Event] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the event stream."""
        self._initialized = True

    async def emit(self, event: Event) -> None:
        """Emit an event to the stream."""
        self._events.append(event)
        # Keep only last 1000 events to prevent memory issues
        if len(self._events) > 1000:
            self._events = self._events[-1000:]

    async def get_event_history(
        self,
        *,
        agent_id: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get event history with optional filters."""
        events = self._events

        if agent_id:
            events = [e for e in events if e.agent_id == agent_id]

        if event_types:
            events = [e for e in events if e.event_type in event_types]

        # Return most recent events first
        return list(reversed(events[-limit:]))

    async def get_stream_stats(self) -> Dict[str, Any]:
        """Get stream statistics."""
        event_counts = {}
        for event in self._events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return {
            "total_events": len(self._events),
            "event_counts": event_counts,
            "oldest_event": self._events[0].timestamp if self._events else None,
            "newest_event": self._events[-1].timestamp if self._events else None,
        }


async def emit_task_event(
    event_stream: EventStream,
    task_id: str,
    event_type: EventType,
    source: str,
    mission_id: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Helper function to emit a task-related event.

    Args:
        event_stream: The EventStream instance
        task_id: ID of the task
        event_type: Type of event
        source: Source/origin of the event
        mission_id: Optional mission ID
        extra_data: Optional additional data
    """
    import uuid

    event = Event(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        timestamp=time.time(),
        source=source,
        task_id=task_id,
        data={
            "mission_id": mission_id,
            **(extra_data or {}),
        },
    )

    await event_stream.emit(event)
