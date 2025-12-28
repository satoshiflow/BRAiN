"""
Event Consumer

Consumes events from Redis Streams and dispatches to subscribers.
Includes idempotency, error handling, and consumer group management.
"""

from __future__ import annotations

import asyncio
import json
from typing import Dict, Any, Optional, List
from loguru import logger
import redis.asyncio as redis

from app.core.redis_client import get_redis
from app.core.db import get_async_session
from .registry import get_subscriber_registry
from .idempotency import IdempotencyGuard


class EventConsumer:
    """
    Redis Streams consumer with idempotency and error handling.

    Reads from brain.events.* streams and dispatches to registered subscribers.
    """

    def __init__(
        self,
        stream_pattern: str = "brain.events.*",
        consumer_group: str = "course_subscribers",
        consumer_name: str = "consumer_01",
        poll_interval: float = 1.0,
    ):
        self.stream_pattern = stream_pattern
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.poll_interval = poll_interval
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the event consumer."""
        if self.running:
            logger.warning("[EventConsumer] Already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._consume_loop())
        logger.info(
            f"[EventConsumer] Started",
            consumer_group=self.consumer_group,
            consumer_name=self.consumer_name,
        )

    async def stop(self) -> None:
        """Stop the event consumer gracefully."""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("[EventConsumer] Stopped")

    async def _consume_loop(self) -> None:
        """Main consumer loop."""
        redis_client = await get_redis()
        registry = get_subscriber_registry()

        # Discover streams matching pattern
        streams = await self._discover_streams(redis_client)

        # Create consumer groups (if not exist)
        for stream in streams:
            await self._ensure_consumer_group(redis_client, stream)

        logger.info(f"[EventConsumer] Consuming from {len(streams)} streams: {streams}")

        while self.running:
            try:
                # Read from all streams
                stream_entries = {}
                for stream in streams:
                    stream_entries[stream] = ">"  # Read new messages

                # XREADGROUP (blocking with timeout)
                messages = await redis_client.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams=stream_entries,
                    count=10,  # Batch size
                    block=int(self.poll_interval * 1000),  # ms
                )

                if not messages:
                    continue  # No new messages

                # Process messages
                for stream, entries in messages:
                    for message_id, fields in entries:
                        await self._process_message(
                            redis_client=redis_client,
                            stream=stream,
                            message_id=message_id,
                            fields=fields,
                            registry=registry,
                        )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[EventConsumer] Consumer loop error: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _discover_streams(self, redis_client: redis.Redis) -> List[str]:
        """Discover streams matching pattern."""
        # For MVP: hardcode known streams
        # Future: Use SCAN with pattern matching
        return [
            "brain.events.paycore",
            "brain.events.missions",
            "brain.events.immune",
        ]

    async def _ensure_consumer_group(
        self, redis_client: redis.Redis, stream: str
    ) -> None:
        """Create consumer group if not exists."""
        try:
            await redis_client.xgroup_create(
                name=stream,
                groupname=self.consumer_group,
                id="0",  # Start from beginning
                mkstream=True,
            )
            logger.info(f"[EventConsumer] Created consumer group for {stream}")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                pass
            else:
                logger.error(f"[EventConsumer] Failed to create group for {stream}: {e}")

    async def _process_message(
        self,
        redis_client: redis.Redis,
        stream: str,
        message_id: str,
        fields: Dict[str, Any],
        registry: Any,
    ) -> None:
        """
        Process single message with idempotency and error handling.

        Args:
            redis_client: Redis client
            stream: Stream name
            message_id: Message ID
            fields: Message fields
            registry: Subscriber registry
        """
        try:
            # Parse event
            data_json = fields.get("data")
            if not data_json:
                logger.warning(f"[EventConsumer] Message missing 'data' field: {message_id}")
                await self._ack_message(redis_client, stream, message_id)
                return

            event = json.loads(data_json)
            event_type = event.get("event_type")

            if not event_type:
                logger.warning(f"[EventConsumer] Event missing 'event_type': {message_id}")
                await self._ack_message(redis_client, stream, message_id)
                return

            # Add trace_id if missing (use message_id)
            if "trace_id" not in event:
                event["trace_id"] = f"evt_{message_id}"

            # Get subscribers for this event type
            subscribers = registry.get_subscribers_for_event(event_type)

            if not subscribers:
                logger.debug(f"[EventConsumer] No subscribers for {event_type}")
                await self._ack_message(redis_client, stream, message_id)
                return

            # Process with each subscriber
            async with get_async_session() as db_session:
                guard = IdempotencyGuard(db_session)

                for subscriber in subscribers:
                    # Check idempotency
                    should_process = await guard.should_process(
                        subscriber.subscriber_name, event
                    )

                    if not should_process:
                        logger.info(
                            f"[EventConsumer] Skipping (already processed)",
                            subscriber=subscriber.subscriber_name,
                            trace_id=event.get("trace_id"),
                        )
                        continue

                    # Process event
                    try:
                        await subscriber.handle(event)

                        logger.info(
                            f"[EventConsumer] Event processed successfully",
                            subscriber=subscriber.subscriber_name,
                            event_type=event_type,
                            trace_id=event.get("trace_id"),
                        )

                    except Exception as e:
                        # Error handling
                        is_transient = await subscriber.on_error(event, e)

                        if not is_transient:
                            # Permanent error: rollback idempotency and ACK (skip)
                            await guard.rollback_processing(subscriber.subscriber_name, event)
                            logger.error(
                                f"[EventConsumer] Permanent error, skipping event",
                                subscriber=subscriber.subscriber_name,
                                error=str(e),
                                trace_id=event.get("trace_id"),
                            )
                        else:
                            # Transient error: rollback idempotency, don't ACK (retry)
                            await guard.rollback_processing(subscriber.subscriber_name, event)
                            logger.warning(
                                f"[EventConsumer] Transient error, will retry",
                                subscriber=subscriber.subscriber_name,
                                error=str(e),
                                trace_id=event.get("trace_id"),
                            )
                            raise  # Don't ACK, will retry

            # ACK message (all subscribers processed successfully)
            await self._ack_message(redis_client, stream, message_id)

        except Exception as e:
            logger.error(
                f"[EventConsumer] Failed to process message: {e}",
                stream=stream,
                message_id=message_id,
            )
            # Don't ACK on transient errors (will retry)

    async def _ack_message(
        self, redis_client: redis.Redis, stream: str, message_id: str
    ) -> None:
        """Acknowledge message."""
        try:
            await redis_client.xack(stream, self.consumer_group, message_id)
            logger.debug(f"[EventConsumer] ACKed message: {message_id}")
        except Exception as e:
            logger.error(f"[EventConsumer] Failed to ACK message {message_id}: {e}")


# Global consumer instance
_consumer: Optional[EventConsumer] = None


async def start_event_consumer() -> EventConsumer:
    """Start the global event consumer."""
    global _consumer
    if _consumer is None:
        _consumer = EventConsumer()
        await _consumer.start()
    return _consumer


async def stop_event_consumer() -> None:
    """Stop the global event consumer."""
    global _consumer
    if _consumer:
        await _consumer.stop()
        _consumer = None
