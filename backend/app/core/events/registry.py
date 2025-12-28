"""
Subscriber Registry

Central registry for all event subscribers.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from loguru import logger

from .base_subscriber import EventSubscriber


class SubscriberRegistry:
    """
    Registry for event subscribers.

    Maps event types to subscribers for efficient dispatch.
    """

    def __init__(self):
        self._subscribers: List[EventSubscriber] = []
        self._by_event_type: Dict[str, List[EventSubscriber]] = {}

    def register(self, subscriber: EventSubscriber) -> None:
        """
        Register a subscriber.

        Args:
            subscriber: EventSubscriber instance
        """
        self._subscribers.append(subscriber)

        for event_type in subscriber.event_types:
            if event_type not in self._by_event_type:
                self._by_event_type[event_type] = []
            self._by_event_type[event_type].append(subscriber)

        logger.info(
            f"[SubscriberRegistry] Registered subscriber: {subscriber.subscriber_name}",
            event_types=subscriber.event_types,
        )

    def get_subscribers_for_event(self, event_type: str) -> List[EventSubscriber]:
        """Get all subscribers for a given event type."""
        return self._by_event_type.get(event_type, [])

    def get_all_subscribers(self) -> List[EventSubscriber]:
        """Get all registered subscribers."""
        return self._subscribers.copy()

    def get_subscriber_by_name(self, name: str) -> Optional[EventSubscriber]:
        """Get subscriber by name."""
        for sub in self._subscribers:
            if sub.subscriber_name == name:
                return sub
        return None


# Global registry singleton
_registry: Optional[SubscriberRegistry] = None


def get_subscriber_registry() -> SubscriberRegistry:
    """Get global subscriber registry."""
    global _registry
    if _registry is None:
        _registry = SubscriberRegistry()
    return _registry
