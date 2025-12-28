"""
Course Payment Subscriber

Subscribes to PayCore payment events and dispatches to handlers.
"""

from __future__ import annotations

from typing import List, Dict, Any
from loguru import logger

from app.core.events.base_subscriber import EventSubscriber
from .handlers import (
    handle_payment_succeeded,
    handle_payment_failed,
    handle_refund_succeeded,
)


class CoursePaymentSubscriber(EventSubscriber):
    """
    Subscriber for PayCore payment events.

    Handles:
    - paycore.payment_succeeded: Grant course access
    - paycore.payment_failed: Log failure (audit)
    - paycore.refund_succeeded: Mark enrollment as refunded
    """

    @property
    def subscriber_name(self) -> str:
        return "course_payment_subscriber"

    @property
    def event_types(self) -> List[str]:
        return [
            "paycore.payment_succeeded",
            "paycore.payment_failed",
            "paycore.refund_succeeded",
        ]

    async def handle(self, event: Dict[str, Any]) -> None:
        """
        Dispatch event to appropriate handler.

        Args:
            event: Event payload

        Raises:
            ValueError: For validation errors (permanent)
            Exception: For service errors (transient)
        """
        event_type = event.get("event_type")

        # Defensive validation
        if not event_type:
            raise ValueError("Event missing 'event_type' field")

        if event_type not in self.event_types:
            logger.warning(
                f"[{self.subscriber_name}] Unexpected event type: {event_type}",
                trace_id=event.get("trace_id"),
            )
            return  # Skip silently (shouldn't happen if registry works)

        # Dispatch to handler
        handlers = {
            "paycore.payment_succeeded": handle_payment_succeeded,
            "paycore.payment_failed": handle_payment_failed,
            "paycore.refund_succeeded": handle_refund_succeeded,
        }

        handler = handlers[event_type]

        logger.debug(
            f"[{self.subscriber_name}] Processing event",
            event_type=event_type,
            trace_id=event.get("trace_id"),
            tenant_id=event.get("tenant_id"),
        )

        await handler(event)
