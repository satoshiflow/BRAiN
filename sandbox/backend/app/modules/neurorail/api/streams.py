"""
SSE Streams API (Phase 3 Backend).

FastAPI endpoints for Server-Sent Events streaming.
"""

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
import asyncio
import time

from app.modules.neurorail.streams import (
    get_sse_publisher,
    SSESubscriber,
    EventChannel,
    SubscriptionFilter,
    StreamEvent,
)
from app.modules.neurorail.rbac import require_permission, Permission

router = APIRouter(prefix="/api/neurorail/v1/stream", tags=["neurorail-streams"])


@router.get("/events")
@require_permission(Permission.READ_AUDIT)  # Minimum permission: read audit
async def stream_events(
    channels: Optional[List[str]] = Query(default=None, description="Event channels to subscribe to"),
    event_types: Optional[List[str]] = Query(default=None, description="Event types to filter"),
    entity_ids: Optional[List[str]] = Query(default=None, description="Entity IDs to filter"),
):
    """
    SSE endpoint for realtime event streaming.

    Subscribe to NeuroRail events in realtime using Server-Sent Events.

    **Channels:**
    - `audit`: Audit events (execution_start, execution_success, etc.)
    - `lifecycle`: Lifecycle state transitions
    - `metrics`: Telemetry metrics snapshots
    - `reflex`: Reflex system events (triggers, actions, circuit breaker)
    - `governor`: Governor mode decisions
    - `enforcement`: Budget enforcement events
    - `all`: All channels (default)

    **Example:**
    ```javascript
    const eventSource = new EventSource('/api/neurorail/v1/stream/events?channels=audit&channels=reflex');

    eventSource.addEventListener('execution_start', (event) => {
        const data = JSON.parse(event.data);
        console.log('Execution started:', data);
    });
    ```

    Returns:
        StreamingResponse with SSE events
    """

    # Parse channels
    parsed_channels = []
    if channels:
        for channel_str in channels:
            try:
                parsed_channels.append(EventChannel(channel_str))
            except ValueError:
                # Invalid channel, skip
                pass

    if not parsed_channels:
        parsed_channels = [EventChannel.ALL]

    # Create subscription filter
    filter = SubscriptionFilter(
        channels=parsed_channels,
        event_types=event_types,
        entity_ids=entity_ids,
    )

    # Create subscriber
    subscriber = SSESubscriber(filter=filter, replay_buffer=True)

    async def event_generator():
        """Generate SSE events."""
        try:
            async for event in subscriber.stream():
                # Format as SSE
                yield event.to_sse_format()

                # Yield empty comment to keep connection alive
                await asyncio.sleep(0.01)

        except asyncio.CancelledError:
            # Client disconnected
            await subscriber.close()
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/stats")
@require_permission(Permission.READ_METRICS)
async def get_stream_stats():
    """
    Get SSE stream statistics.

    Returns publisher metrics including subscriber counts and buffer sizes.

    Returns:
        Stream statistics
    """
    publisher = get_sse_publisher()
    return publisher.get_stats()


@router.post("/publish")
@require_permission(Permission.MANAGE_SYSTEM)
async def publish_event(
    channel: str,
    event_type: str,
    data: dict,
):
    """
    Manually publish an event to SSE streams.

    **Admin only.** For testing and manual event injection.

    Args:
        channel: Event channel (audit, lifecycle, metrics, etc.)
        event_type: Event type identifier
        data: Event payload

    Returns:
        Success confirmation
    """
    try:
        channel_enum = EventChannel(channel)
    except ValueError:
        return {"error": f"Invalid channel: {channel}"}

    # Create event
    event = StreamEvent(
        channel=channel_enum,
        event_type=event_type,
        data=data,
        timestamp=time.time(),
    )

    # Publish
    publisher = get_sse_publisher()
    await publisher.publish(event)

    return {
        "success": True,
        "channel": channel,
        "event_type": event_type,
    }


@router.delete("/buffers")
@require_permission(Permission.MANAGE_SYSTEM)
async def clear_buffers():
    """
    Clear all SSE event buffers.

    **Admin only.** Removes all buffered events.

    Returns:
        Success confirmation
    """
    publisher = get_sse_publisher()
    await publisher.clear_buffers()

    return {"success": True, "message": "Event buffers cleared"}
