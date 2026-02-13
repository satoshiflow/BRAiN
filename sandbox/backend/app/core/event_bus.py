"""
Core Event Bus - Stub Implementation

Temporary stub to satisfy imports until proper event bus is implemented.
"""

from typing import Any, Callable, Coroutine, Optional
from loguru import logger


class EventBus:
    """
    Stub Event Bus for publish/subscribe pattern.

    TODO: Implement proper event bus with:
    - Event persistence
    - Subscriber management
    - Error isolation
    - Async pub/sub
    """

    def __init__(self, redis_client: Optional[Any] = None):
        """Initialize event bus with optional Redis client."""
        self.redis = redis_client
        self.subscribers: dict[str, list[Callable]] = {}
        logger.warning("[EventBus] Using stub implementation - events not persisted")

    async def publish(self, event_type: str, data: dict) -> bool:
        """
        Publish event to subscribers.

        Args:
            event_type: Type of event (e.g., "payment.created")
            data: Event payload

        Returns:
            True if published successfully
        """
        logger.debug(f"[EventBus] Publishing event: {event_type}")

        # Notify subscribers
        if event_type in self.subscribers:
            for handler in self.subscribers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event_type, data)
                    else:
                        handler(event_type, data)
                except Exception as e:
                    logger.error(f"[EventBus] Subscriber error: {e}")

        return True

    def subscribe(
        self,
        event_type: str,
        handler: Callable[[str, dict], Coroutine[Any, Any, None]]
    ) -> None:
        """
        Subscribe to event type.

        Args:
            event_type: Type of event to subscribe to
            handler: Async function to handle event
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(handler)
        logger.debug(f"[EventBus] Subscribed to {event_type}")


# Import asyncio for coroutine check
import asyncio
