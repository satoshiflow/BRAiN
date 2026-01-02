"""
SSE Publisher (Phase 3 Backend).

Publishes events to SSE streams for realtime updates.
"""

import asyncio
from typing import Dict, List, Optional
from loguru import logger

from backend.app.modules.neurorail.streams.schemas import StreamEvent, EventChannel


class SSEPublisher:
    """
    SSE event publisher.

    Publishes events to subscribers via asyncio queues.
    Thread-safe for concurrent publishing.

    Features:
    - Channel-based event routing
    - Multiple subscriber support
    - Automatic subscriber cleanup
    - Event buffering (last N events)

    Usage:
        publisher = SSEPublisher()

        # Publish event
        event = StreamEvent(
            channel=EventChannel.AUDIT,
            event_type="execution_start",
            data={"attempt_id": "a_123"},
            timestamp=time.time()
        )
        await publisher.publish(event)

        # Subscribe
        queue = await publisher.subscribe(channels=[EventChannel.AUDIT])
        event = await queue.get()
    """

    def __init__(self, buffer_size: int = 100):
        """
        Initialize SSE publisher.

        Args:
            buffer_size: Max events to buffer per channel (for late subscribers)
        """
        self.buffer_size = buffer_size

        # Subscribers: Dict[channel, List[asyncio.Queue]]
        self._subscribers: Dict[EventChannel, List[asyncio.Queue]] = {
            channel: [] for channel in EventChannel
        }

        # Event buffers: Dict[channel, List[StreamEvent]]
        self._buffers: Dict[EventChannel, List[StreamEvent]] = {
            channel: [] for channel in EventChannel
        }

        # Stats
        self.total_events_published = 0
        self.total_subscribers = 0

        self._lock = asyncio.Lock()

    async def publish(self, event: StreamEvent):
        """
        Publish event to subscribers.

        Args:
            event: Event to publish
        """
        async with self._lock:
            # Add to buffer
            channel_buffer = self._buffers[event.channel]
            channel_buffer.append(event)
            if len(channel_buffer) > self.buffer_size:
                channel_buffer.pop(0)  # Remove oldest

            # Publish to channel subscribers
            await self._publish_to_subscribers(event.channel, event)

            # Publish to ALL subscribers
            if event.channel != EventChannel.ALL:
                await self._publish_to_subscribers(EventChannel.ALL, event)

            self.total_events_published += 1

        logger.debug(
            f"Published SSE event: {event.channel}/{event.event_type}",
            extra={
                "channel": event.channel,
                "event_type": event.event_type,
                "subscribers": len(self._subscribers[event.channel]),
            }
        )

    async def _publish_to_subscribers(self, channel: EventChannel, event: StreamEvent):
        """Publish event to all subscribers of a channel."""
        subscribers = self._subscribers[channel]

        # Remove dead subscribers (queue full or closed)
        dead_subscribers = []

        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"Subscriber queue full for channel {channel}, dropping event")
            except Exception as e:
                logger.error(f"Error publishing to subscriber: {e}")
                dead_subscribers.append(queue)

        # Cleanup dead subscribers
        for queue in dead_subscribers:
            subscribers.remove(queue)

    async def subscribe(
        self,
        channels: Optional[List[EventChannel]] = None,
        queue_size: int = 100,
        replay_buffer: bool = True
    ) -> asyncio.Queue:
        """
        Subscribe to event channels.

        Args:
            channels: List of channels to subscribe to (default: [EventChannel.ALL])
            queue_size: Max queue size for subscriber
            replay_buffer: If True, replay buffered events on subscribe

        Returns:
            asyncio.Queue for receiving events
        """
        if channels is None:
            channels = [EventChannel.ALL]

        queue = asyncio.Queue(maxsize=queue_size)

        async with self._lock:
            # Add to subscribers
            for channel in channels:
                self._subscribers[channel].append(queue)

            # Replay buffered events (optional)
            if replay_buffer:
                for channel in channels:
                    for event in self._buffers[channel]:
                        try:
                            queue.put_nowait(event)
                        except asyncio.QueueFull:
                            logger.warning(f"Queue full during buffer replay for channel {channel}")
                            break

            self.total_subscribers += 1

        logger.info(
            f"New SSE subscriber: channels={[c.value for c in channels]}",
            extra={"channels": channels, "total_subscribers": self.total_subscribers}
        )

        return queue

    async def unsubscribe(self, queue: asyncio.Queue, channels: Optional[List[EventChannel]] = None):
        """
        Unsubscribe from channels.

        Args:
            queue: Queue to remove
            channels: Channels to unsubscribe from (default: all)
        """
        if channels is None:
            channels = list(EventChannel)

        async with self._lock:
            for channel in channels:
                if queue in self._subscribers[channel]:
                    self._subscribers[channel].remove(queue)

        logger.info(f"SSE subscriber unsubscribed from channels: {channels}")

    def get_stats(self) -> Dict[str, any]:
        """Get publisher statistics."""
        return {
            "total_events_published": self.total_events_published,
            "total_subscribers": self.total_subscribers,
            "subscribers_by_channel": {
                channel.value: len(subs) for channel, subs in self._subscribers.items()
            },
            "buffer_sizes": {
                channel.value: len(buf) for channel, buf in self._buffers.items()
            },
        }

    async def clear_buffers(self):
        """Clear all event buffers."""
        async with self._lock:
            for channel in EventChannel:
                self._buffers[channel].clear()

        logger.info("SSE event buffers cleared")


# Singleton publisher
_sse_publisher: Optional[SSEPublisher] = None


def get_sse_publisher() -> SSEPublisher:
    """Get or create singleton SSE publisher."""
    global _sse_publisher
    if _sse_publisher is None:
        _sse_publisher = SSEPublisher()
    return _sse_publisher
