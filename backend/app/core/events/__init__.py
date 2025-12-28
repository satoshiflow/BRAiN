"""
Event Infrastructure

Provides base subscriber pattern and idempotency guards for event-driven architecture.
"""

from .base_subscriber import EventSubscriber
from .idempotency import IdempotencyGuard, ProcessedEvent
from .registry import SubscriberRegistry, get_subscriber_registry

__all__ = [
    "EventSubscriber",
    "IdempotencyGuard",
    "ProcessedEvent",
    "SubscriberRegistry",
    "get_subscriber_registry",
]
