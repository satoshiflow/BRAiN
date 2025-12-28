"""
PayCore Event Simulator

Utility for testing payment events during development.
Publishes events to Redis Streams for consumption by subscribers.
"""

from __future__ import annotations

import time
import json
import uuid
from typing import Dict, Any, Optional
from loguru import logger

from app.core.redis_client import get_redis


class PayCoreSimulator:
    """
    Simulates PayCore payment events for testing.

    Usage:
        simulator = PayCoreSimulator()
        await simulator.publish_payment_succeeded(
            tenant_id="tenant_123",
            user_id="user_456",
            course_id="course_789",
        )
    """

    def __init__(self, stream: str = "brain.events.paycore"):
        self.stream = stream

    async def publish_payment_succeeded(
        self,
        tenant_id: str,
        user_id: str,
        course_id: str,
        language: str = "de",
        intent_id: Optional[str] = None,
        tx_id: Optional[str] = None,
    ) -> str:
        """
        Publish payment succeeded event.

        Args:
            tenant_id: Tenant ID
            user_id: User ID
            course_id: Course ID
            language: Course language
            intent_id: Payment intent ID (optional)
            tx_id: Transaction ID (optional)

        Returns:
            str: Event trace_id
        """
        trace_id = f"evt_{uuid.uuid4().hex[:16]}"
        intent_id = intent_id or f"intent_{uuid.uuid4().hex[:12]}"
        tx_id = tx_id or f"tx_{uuid.uuid4().hex[:12]}"

        event = {
            "event_type": "paycore.payment_succeeded",
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "intent_id": intent_id,
            "tx_id": tx_id,
            "user_id": user_id,
            "metadata": {
                "course_id": course_id,
                "language": language,
            },
            "timestamp": time.time(),
        }

        message_id = await self._publish(event)

        logger.info(
            f"[PayCoreSimulator] Published payment_succeeded",
            trace_id=trace_id,
            tenant_id=tenant_id,
            course_id=course_id,
            message_id=message_id,
        )

        return trace_id

    async def publish_payment_failed(
        self,
        tenant_id: str,
        user_id: str,
        course_id: str,
        reason: str = "card_declined",
        intent_id: Optional[str] = None,
    ) -> str:
        """Publish payment failed event."""
        trace_id = f"evt_{uuid.uuid4().hex[:16]}"
        intent_id = intent_id or f"intent_{uuid.uuid4().hex[:12]}"

        event = {
            "event_type": "paycore.payment_failed",
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "intent_id": intent_id,
            "user_id": user_id,
            "metadata": {
                "course_id": course_id,
                "failure_reason": reason,
            },
            "timestamp": time.time(),
        }

        message_id = await self._publish(event)

        logger.info(
            f"[PayCoreSimulator] Published payment_failed",
            trace_id=trace_id,
            tenant_id=tenant_id,
            reason=reason,
            message_id=message_id,
        )

        return trace_id

    async def publish_refund_succeeded(
        self,
        tenant_id: str,
        user_id: str,
        course_id: str,
        intent_id: str,
        enrollment_id: Optional[str] = None,
        refund_id: Optional[str] = None,
    ) -> str:
        """Publish refund succeeded event."""
        trace_id = f"evt_{uuid.uuid4().hex[:16]}"
        refund_id = refund_id or f"ref_{uuid.uuid4().hex[:12]}"

        event = {
            "event_type": "paycore.refund_succeeded",
            "trace_id": trace_id,
            "tenant_id": tenant_id,
            "intent_id": intent_id,
            "refund_id": refund_id,
            "user_id": user_id,
            "metadata": {
                "course_id": course_id,
                "enrollment_id": enrollment_id,
            },
            "timestamp": time.time(),
        }

        message_id = await self._publish(event)

        logger.info(
            f"[PayCoreSimulator] Published refund_succeeded",
            trace_id=trace_id,
            tenant_id=tenant_id,
            course_id=course_id,
            message_id=message_id,
        )

        return trace_id

    async def _publish(self, event: Dict[str, Any]) -> str:
        """Publish event to Redis Stream."""
        redis_client = await get_redis()

        data = json.dumps(event)
        message_id = await redis_client.xadd(self.stream, {"data": data})

        return message_id


# Singleton
_simulator: Optional[PayCoreSimulator] = None


def get_paycore_simulator() -> PayCoreSimulator:
    """Get PayCore simulator singleton."""
    global _simulator
    if _simulator is None:
        _simulator = PayCoreSimulator()
    return _simulator
