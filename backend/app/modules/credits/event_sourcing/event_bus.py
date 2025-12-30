"""
Event Bus - Pub/Sub for Event Distribution.

Implements:
- Publish events to EventJournal
- Notify subscribers (projections, handlers)
- Async pub/sub pattern
- Error isolation (failed subscriber doesn't crash system)
- Multiple subscribers per event type

Architecture:
┌─────────────────────────────────────┐
│          EventBus                   │
├─────────────────────────────────────┤
│  publish(event)                     │
│    ├─> 1. Write to EventJournal    │
│    ├─> 2. Notify all subscribers   │
│    └─> 3. Return success           │
│                                     │
│  subscribe(event_type, handler)    │
│    └─> Register handler             │
└─────────────────────────────────────┘

Subscribers:
- Projections: Update in-memory read models
- Handlers: Side effects (notifications, integrations)
- Observers: Metrics, logging, monitoring

Error Handling:
- Failed journal write → raise exception (critical)
- Failed subscriber → log error, continue (non-critical)
- Subscriber errors don't prevent event persistence
"""

from __future__ import annotations

from typing import Callable, Coroutine, Dict, List

from loguru import logger

from backend.app.modules.credits.event_sourcing.events import (
    EventEnvelope,
    EventType,
)
from backend.app.modules.credits.event_sourcing.event_journal import (
    EventJournal,
    get_event_journal,
)


# Type alias for event handler functions
EventHandler = Callable[[EventEnvelope], Coroutine[None, None, None]]


class EventBusError(Exception):
    """Base exception for EventBus errors."""
    pass


class EventBus:
    """
    Event Bus for publishing and subscribing to events.

    Features:
    - Publish events to journal (persistent)
    - Notify subscribers (projections, handlers)
    - Error isolation (failed subscriber doesn't crash)
    - Multiple subscribers per event type

    Thread-Safety:
    - NOT thread-safe (use asyncio locks if needed)
    - Single-writer pattern recommended

    Example:
        >>> bus = EventBus(journal)
        >>>
        >>> # Subscribe to events
        >>> async def update_balance(event: EventEnvelope):
        ...     print(f"Balance updated: {event.payload}")
        >>>
        >>> bus.subscribe(EventType.CREDIT_ALLOCATED, update_balance)
        >>>
        >>> # Publish event
        >>> event = create_credit_allocated_event(...)
        >>> await bus.publish(event)
    """

    def __init__(self, journal: EventJournal):
        """
        Initialize EventBus.

        Args:
            journal: EventJournal for persistent storage
        """
        self.journal = journal

        # Subscribers: event_type → list of handlers
        self._subscribers: Dict[EventType, List[EventHandler]] = {}

        # Metrics
        self._total_published = 0
        self._total_subscriber_errors = 0

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: Type of events to listen for
            handler: Async function to handle events

        Example:
            >>> async def my_handler(event: EventEnvelope):
            ...     print(f"Event: {event.event_type}")
            >>> bus.subscribe(EventType.CREDIT_ALLOCATED, my_handler)
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)

        logger.debug(
            f"Subscribed to {event_type}",
            event_type=event_type,
            handler=handler.__name__,
            total_subscribers=len(self._subscribers[event_type]),
        )

    def unsubscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> bool:
        """
        Unsubscribe from events.

        Args:
            event_type: Type of events
            handler: Handler to remove

        Returns:
            True if handler was removed, False if not found
        """
        if event_type not in self._subscribers:
            return False

        try:
            self._subscribers[event_type].remove(handler)
            logger.debug(
                f"Unsubscribed from {event_type}",
                event_type=event_type,
                handler=handler.__name__,
            )
            return True
        except ValueError:
            return False

    async def publish(self, event: EventEnvelope) -> bool:
        """
        Publish event to journal and notify subscribers.

        Steps:
        1. Write event to journal (persistent, idempotent)
        2. Notify all subscribers for this event type
        3. Return success

        Args:
            event: Event to publish

        Returns:
            True if event was published (not duplicate)
            False if event was duplicate (idempotency)

        Raises:
            EventBusError: If journal write fails (critical)

        Notes:
        - Journal write is atomic (event persisted or exception)
        - Subscriber errors are logged but don't prevent publication
        - If journal write succeeds, event is guaranteed persisted
        """
        # === Step 1: Persist to Journal ===
        try:
            published = await self.journal.append_event(event)
        except Exception as e:
            # Journal write failure is critical (cannot continue)
            logger.error(
                "Failed to publish event to journal (CRITICAL)",
                event_id=event.event_id,
                event_type=event.event_type,
                error=str(e),
            )
            raise EventBusError(f"Cannot publish event: {e}") from e

        # If event was duplicate (idempotency), don't notify subscribers
        if not published:
            logger.debug(
                "Event not published (duplicate)",
                event_id=event.event_id,
                idempotency_key=event.idempotency_key,
            )
            return False

        # === Step 2: Notify Subscribers ===
        await self._notify_subscribers(event)

        # === Step 3: Update Metrics ===
        self._total_published += 1

        logger.debug(
            "Event published successfully",
            event_id=event.event_id,
            event_type=event.event_type,
            total_published=self._total_published,
        )

        return True

    async def _notify_subscribers(self, event: EventEnvelope) -> None:
        """
        Notify all subscribers for this event type.

        Args:
            event: Event to distribute

        Notes:
        - Subscriber errors are logged but don't crash
        - Failed subscribers don't prevent other subscribers
        """
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            logger.debug(
                f"No subscribers for {event.event_type}",
                event_id=event.event_id,
                event_type=event.event_type,
            )
            return

        for handler in handlers:
            try:
                await handler(event)
                logger.debug(
                    f"Subscriber notified: {handler.__name__}",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    handler=handler.__name__,
                )

            except Exception as e:
                # Subscriber error is non-critical (log and continue)
                self._total_subscriber_errors += 1
                logger.error(
                    f"Subscriber error (non-critical): {handler.__name__}",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    handler=handler.__name__,
                    error=str(e),
                    total_subscriber_errors=self._total_subscriber_errors,
                )

    def get_metrics(self) -> dict:
        """
        Get EventBus metrics.

        Returns:
            Dict with metrics:
            - total_published: Events published
            - total_subscriber_errors: Subscriber failures
            - subscribers_by_type: Number of subscribers per event type
        """
        subscribers_by_type = {
            event_type: len(handlers)
            for event_type, handlers in self._subscribers.items()
        }

        return {
            "total_published": self._total_published,
            "total_subscriber_errors": self._total_subscriber_errors,
            "subscribers_by_type": subscribers_by_type,
        }


# === Singleton Pattern ===
# Global event bus instance (initialized on first use)

_event_bus_instance: EventBus | None = None


async def get_event_bus() -> EventBus:
    """
    Get singleton EventBus instance.

    Returns:
        EventBus instance (initialized with journal)
    """
    global _event_bus_instance

    if _event_bus_instance is None:
        journal = await get_event_journal()
        _event_bus_instance = EventBus(journal)

    return _event_bus_instance
