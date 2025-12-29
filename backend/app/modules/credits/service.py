from datetime import datetime, timezone
from typing import Optional
import time
import logging

from .schemas import CreditsHealth, CreditsInfo

logger = logging.getLogger(__name__)

MODULE_NAME = "brain.credits"
MODULE_VERSION = "1.0.0"

# Optional EventStream import (Sprint 5: EventStream Integration)
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level EventStream (Sprint 5: EventStream Integration)
_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for Credits module (Sprint 5)."""
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit Credits event with error handling (non-blocking).

    Args:
        event_type: Event type (e.g., "credits.health_checked")
        payload: Event payload dictionary

    Note:
        - Never raises exceptions
        - Logs failures at ERROR level
        - Gracefully handles missing EventStream
    """
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[CreditsService] EventStream not available, skipping event")
        return

    try:
        event = Event(
            type=event_type,
            source="credits_service",
            target=None,
            payload=payload
        )
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"[CreditsService] Event publishing failed: {e}", exc_info=True)


async def get_health() -> CreditsHealth:
    """Get Credits module health status.

    Returns:
        CreditsHealth: Health status object

    Events:
        - credits.health_checked (optional): Health check performed
    """
    result = CreditsHealth(status="ok", timestamp=datetime.now(timezone.utc))

    # EVENT: credits.health_checked (optional - Sprint 5)
    await _emit_event_safe("credits.health_checked", {
        "status": result.status,
        "checked_at": result.timestamp.timestamp(),
    })

    return result


async def get_info() -> CreditsInfo:
    """Get Credits module information.

    Returns:
        CreditsInfo: Module information object
    """
    return CreditsInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config={},
    )
