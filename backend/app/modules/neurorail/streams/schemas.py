"""
SSE Stream Schemas (Phase 3 Backend).

Data structures for SSE event streaming.
"""

from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass
import time


class EventChannel(str, Enum):
    """SSE event channels for different data types."""

    AUDIT = "audit"              # Audit events from audit module
    LIFECYCLE = "lifecycle"      # Lifecycle state transitions
    METRICS = "metrics"          # Telemetry metrics snapshots
    REFLEX = "reflex"            # Reflex system events (triggers, actions)
    GOVERNOR = "governor"        # Governor mode decisions
    ENFORCEMENT = "enforcement"  # Budget enforcement events
    ALL = "all"                  # Subscribe to all channels


@dataclass
class StreamEvent:
    """
    SSE event message structure.

    Attributes:
        channel: Event channel (audit, lifecycle, metrics, etc.)
        event_type: Specific event type (e.g., "execution_start", "state_transition")
        data: Event payload (JSON-serializable dict)
        timestamp: Event timestamp (Unix timestamp)
        event_id: Optional event ID for client tracking
    """

    channel: EventChannel
    event_type: str
    data: Dict[str, Any]
    timestamp: float
    event_id: Optional[str] = None

    def to_sse_format(self) -> str:
        """
        Format event as SSE message.

        SSE format:
            id: <event_id>
            event: <event_type>
            data: <json_payload>

        Returns:
            Formatted SSE message string
        """
        import json

        lines = []

        # Event ID (optional)
        if self.event_id:
            lines.append(f"id: {self.event_id}")

        # Event type
        lines.append(f"event: {self.event_type}")

        # Event data (JSON)
        payload = {
            "channel": self.channel,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "data": self.data,
        }
        data_json = json.dumps(payload)
        lines.append(f"data: {data_json}")

        # Empty line terminates event
        lines.append("")

        return "\n".join(lines) + "\n"


@dataclass
class SubscriptionFilter:
    """
    Filter for SSE subscriptions.

    Attributes:
        channels: List of channels to subscribe to (default: [EventChannel.ALL])
        event_types: Optional list of event types to include
        entity_ids: Optional list of entity IDs to filter (e.g., mission_id, job_id)
    """

    channels: list[EventChannel] = None
    event_types: Optional[list[str]] = None
    entity_ids: Optional[list[str]] = None

    def __post_init__(self):
        if self.channels is None:
            self.channels = [EventChannel.ALL]

    def matches(self, event: StreamEvent) -> bool:
        """
        Check if event matches filter criteria.

        Args:
            event: Event to check

        Returns:
            True if event matches filter
        """
        # Check channel
        if EventChannel.ALL not in self.channels and event.channel not in self.channels:
            return False

        # Check event type
        if self.event_types and event.event_type not in self.event_types:
            return False

        # Check entity IDs (if specified in event data)
        if self.entity_ids:
            event_entity_ids = [
                event.data.get("mission_id"),
                event.data.get("plan_id"),
                event.data.get("job_id"),
                event.data.get("attempt_id"),
            ]
            if not any(eid in self.entity_ids for eid in event_entity_ids if eid):
                return False

        return True
