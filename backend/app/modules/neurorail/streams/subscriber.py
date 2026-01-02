"""
SSE Subscriber (Phase 3 Backend).

Client-side subscriber for consuming SSE events.
"""

import asyncio
from typing import Optional, AsyncGenerator
from loguru import logger

from backend.app.modules.neurorail.streams.schemas import StreamEvent, SubscriptionFilter
from backend.app.modules.neurorail.streams.publisher import get_sse_publisher


class SSESubscriber:
    """
    SSE event subscriber.

    Subscribes to SSE events from publisher and yields filtered events.

    Usage:
        subscriber = SSESubscriber(filter=SubscriptionFilter(
            channels=[EventChannel.AUDIT],
            event_types=["execution_start", "execution_success"]
        ))

        async for event in subscriber.stream():
            print(event.data)
    """

    def __init__(
        self,
        filter: Optional[SubscriptionFilter] = None,
        queue_size: int = 100,
        replay_buffer: bool = True
    ):
        """
        Initialize SSE subscriber.

        Args:
            filter: Event filter (default: subscribe to all)
            queue_size: Max queue size
            replay_buffer: Replay buffered events on subscribe
        """
        self.filter = filter or SubscriptionFilter()
        self.queue_size = queue_size
        self.replay_buffer = replay_buffer

        self._queue: Optional[asyncio.Queue] = None
        self._publisher = get_sse_publisher()

    async def stream(self) -> AsyncGenerator[StreamEvent, None]:
        """
        Stream events from publisher.

        Yields:
            StreamEvent objects matching filter
        """
        # Subscribe to channels
        self._queue = await self._publisher.subscribe(
            channels=self.filter.channels,
            queue_size=self.queue_size,
            replay_buffer=self.replay_buffer
        )

        try:
            while True:
                # Wait for next event
                event = await self._queue.get()

                # Apply filter
                if self.filter.matches(event):
                    yield event

        except asyncio.CancelledError:
            logger.info("SSE subscriber stream cancelled")
            raise

        finally:
            # Cleanup
            if self._queue:
                await self._publisher.unsubscribe(self._queue, self.filter.channels)

    async def close(self):
        """Close subscriber and cleanup."""
        if self._queue:
            await self._publisher.unsubscribe(self._queue, self.filter.channels)
            self._queue = None
