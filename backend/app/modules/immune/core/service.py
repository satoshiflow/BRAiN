from datetime import datetime, timedelta
from typing import List, Optional

from loguru import logger

from backend.app.modules.immune.schemas import ImmuneEvent, ImmuneHealthSummary, ImmuneSeverity

# EventStream integration (Sprint 3)
try:
    from backend.mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None
    import warnings
    warnings.warn(
        "[ImmuneService] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )


class ImmuneService:
    """
    In-Memory Immunsystem.
    Hält Events im Speicher und generiert eine Health-Übersicht.

    Sprint 3 EventStream Integration:
    - immune.event_published: Every immune event
    - immune.critical_event: CRITICAL severity events
    """

    def __init__(self, event_stream: Optional["EventStream"] = None) -> None:
        self._events: List[ImmuneEvent] = []
        self._id_counter: int = 1
        self.event_stream = event_stream  # EventStream integration (Sprint 3)

    async def _emit_event_safe(
        self,
        event_type: str,
        immune_event: ImmuneEvent,
    ) -> None:
        """
        Emit immune event with error handling (non-blocking).

        Charter v1.0 Compliance:
        - Event publishing MUST NOT block business logic
        - Failures are logged but NOT raised
        - Graceful degradation when EventStream unavailable
        """
        if self.event_stream is None or Event is None:
            logger.debug("[ImmuneService] EventStream not available, skipping event: %s", event_type)
            return

        try:
            # Build base payload
            payload = {
                "event_id": immune_event.id,
                "severity": immune_event.severity.value,
                "type": immune_event.type.value,
                "message": immune_event.message,
            }

            # Add optional fields
            if immune_event.agent_id:
                payload["agent_id"] = immune_event.agent_id
            if immune_event.module:
                payload["module"] = immune_event.module
            if immune_event.meta:
                payload["meta"] = immune_event.meta

            # Add timestamp
            timestamp_field = "critical_at" if event_type == "immune.critical_event" else "published_at"
            payload[timestamp_field] = immune_event.created_at.timestamp()

            # Create and publish event
            event = Event(
                type=event_type,
                source="immune_service",
                target=None,
                payload=payload,
            )

            await self.event_stream.publish(event)

            logger.debug(
                "[ImmuneService] Event published: %s (event_id=%s)",
                event_type,
                immune_event.id,
            )

        except Exception as e:
            logger.error(
                "[ImmuneService] Event publishing failed: %s (event_type=%s, event_id=%s)",
                e,
                event_type,
                immune_event.id,
                exc_info=True,
            )
            # DO NOT raise - business logic must continue

    async def publish_event(self, event: ImmuneEvent) -> int:
        now = datetime.utcnow()
        stored = ImmuneEvent(
            **event.model_dump(exclude={"id", "created_at"}),
            id=self._id_counter,
            created_at=now,
        )
        self._id_counter += 1
        self._events.append(stored)

        # EVENT: immune.event_published (always emit)
        await self._emit_event_safe(
            event_type="immune.event_published",
            immune_event=stored,
        )

        # EVENT: immune.critical_event (conditional: if severity is CRITICAL)
        if stored.severity == ImmuneSeverity.CRITICAL:
            await self._emit_event_safe(
                event_type="immune.critical_event",
                immune_event=stored,
            )

        return stored.id

    def get_recent_events(self, minutes: int = 60) -> List[ImmuneEvent]:
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=minutes)
        return [e for e in self._events if e.created_at >= cutoff]

    def health_summary(self, minutes: int = 60) -> ImmuneHealthSummary:
        events = self.get_recent_events(minutes=minutes)
        active_issues = len(events)
        critical_issues = sum(1 for e in events if e.severity == ImmuneSeverity.CRITICAL)
        # letzte 10
        last_events = events[-10:]
        return ImmuneHealthSummary(
            active_issues=active_issues,
            critical_issues=critical_issues,
            last_events=last_events,
        )
