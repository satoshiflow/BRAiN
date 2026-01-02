"""
Unit tests for SSE Subscriber (Phase 3 Backend).

Tests event subscription and filtering.
"""

import pytest
import asyncio
import time
from backend.app.modules.neurorail.streams.subscriber import SSESubscriber
from backend.app.modules.neurorail.streams.publisher import get_sse_publisher
from backend.app.modules.neurorail.streams.schemas import (
    StreamEvent,
    EventChannel,
    SubscriptionFilter,
)


# ============================================================================
# Tests: Basic Subscription
# ============================================================================

@pytest.mark.asyncio
async def test_subscriber_receive_events():
    """Test subscriber receives events."""
    publisher = get_sse_publisher()

    # Create subscriber
    subscriber = SSESubscriber(
        filter=SubscriptionFilter(channels=[EventChannel.AUDIT])
    )

    # Start streaming in background
    events_received = []

    async def collect_events():
        count = 0
        async for event in subscriber.stream():
            events_received.append(event)
            count += 1
            if count >= 2:
                break

    stream_task = asyncio.create_task(collect_events())

    # Publish events
    await asyncio.sleep(0.1)  # Let subscriber set up
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event1", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event2", {}, time.time()))

    # Wait for collection
    await asyncio.wait_for(stream_task, timeout=2.0)

    assert len(events_received) == 2
    assert events_received[0].event_type == "event1"
    assert events_received[1].event_type == "event2"


# ============================================================================
# Tests: Filtering
# ============================================================================

@pytest.mark.asyncio
async def test_subscriber_filter_by_channel():
    """Test filtering events by channel."""
    publisher = get_sse_publisher()

    # Subscribe to AUDIT only
    subscriber = SSESubscriber(
        filter=SubscriptionFilter(channels=[EventChannel.AUDIT])
    )

    events_received = []

    async def collect_events():
        count = 0
        async for event in subscriber.stream():
            events_received.append(event)
            count += 1
            if count >= 1:
                break

    stream_task = asyncio.create_task(collect_events())

    await asyncio.sleep(0.1)

    # Publish to different channels
    await publisher.publish(StreamEvent(EventChannel.METRICS, "metrics_event", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "audit_event", {}, time.time()))

    await asyncio.wait_for(stream_task, timeout=2.0)

    # Should only receive AUDIT event
    assert len(events_received) == 1
    assert events_received[0].event_type == "audit_event"


@pytest.mark.asyncio
async def test_subscriber_filter_by_event_type():
    """Test filtering events by event type."""
    publisher = get_sse_publisher()

    # Subscribe with event type filter
    subscriber = SSESubscriber(
        filter=SubscriptionFilter(
            channels=[EventChannel.AUDIT],
            event_types=["execution_start", "execution_success"]
        )
    )

    events_received = []

    async def collect_events():
        count = 0
        async for event in subscriber.stream():
            events_received.append(event)
            count += 1
            if count >= 2:
                break

    stream_task = asyncio.create_task(collect_events())

    await asyncio.sleep(0.1)

    # Publish different event types
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "execution_start", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "other_event", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "execution_success", {}, time.time()))

    await asyncio.wait_for(stream_task, timeout=2.0)

    # Should only receive filtered event types
    assert len(events_received) == 2
    assert events_received[0].event_type == "execution_start"
    assert events_received[1].event_type == "execution_success"


@pytest.mark.asyncio
async def test_subscriber_filter_by_entity_id():
    """Test filtering events by entity ID."""
    publisher = get_sse_publisher()

    # Subscribe with entity ID filter
    subscriber = SSESubscriber(
        filter=SubscriptionFilter(
            channels=[EventChannel.AUDIT],
            entity_ids=["m_123", "j_456"]
        )
    )

    events_received = []

    async def collect_events():
        count = 0
        async for event in subscriber.stream():
            events_received.append(event)
            count += 1
            if count >= 2:
                break

    stream_task = asyncio.create_task(collect_events())

    await asyncio.sleep(0.1)

    # Publish with different entity IDs
    await publisher.publish(StreamEvent(
        EventChannel.AUDIT,
        "event1",
        {"mission_id": "m_123"},
        time.time()
    ))
    await publisher.publish(StreamEvent(
        EventChannel.AUDIT,
        "event2",
        {"mission_id": "m_999"},  # Not in filter
        time.time()
    ))
    await publisher.publish(StreamEvent(
        EventChannel.AUDIT,
        "event3",
        {"job_id": "j_456"},
        time.time()
    ))

    await asyncio.wait_for(stream_task, timeout=2.0)

    # Should only receive filtered entity IDs
    assert len(events_received) == 2
    assert events_received[0].data["mission_id"] == "m_123"
    assert events_received[1].data["job_id"] == "j_456"


# ============================================================================
# Tests: Close/Cleanup
# ============================================================================

@pytest.mark.asyncio
async def test_subscriber_close():
    """Test subscriber cleanup."""
    publisher = get_sse_publisher()

    subscriber = SSESubscriber(
        filter=SubscriptionFilter(channels=[EventChannel.AUDIT])
    )

    # Start streaming
    stream_gen = subscriber.stream()
    await stream_gen.__anext__()  # Get iterator started

    # Close subscriber
    await subscriber.close()

    # Queue should be cleaned up
    assert subscriber._queue is None


# ============================================================================
# Tests: Buffer Replay
# ============================================================================

@pytest.mark.asyncio
async def test_subscriber_replay_buffer():
    """Test subscriber receives buffered events."""
    publisher = get_sse_publisher()

    # Publish events BEFORE subscribing
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "old_event1", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "old_event2", {}, time.time()))

    # Subscribe with replay
    subscriber = SSESubscriber(
        filter=SubscriptionFilter(channels=[EventChannel.AUDIT]),
        replay_buffer=True
    )

    events_received = []

    async def collect_events():
        count = 0
        async for event in subscriber.stream():
            events_received.append(event)
            count += 1
            if count >= 2:
                break

    await asyncio.wait_for(collect_events(), timeout=2.0)

    # Should receive buffered events
    assert len(events_received) == 2
    assert events_received[0].event_type == "old_event1"
    assert events_received[1].event_type == "old_event2"


@pytest.mark.asyncio
async def test_subscriber_no_replay_buffer():
    """Test subscriber does not receive buffered events when replay=False."""
    publisher = get_sse_publisher()

    # Clear buffers
    await publisher.clear_buffers()

    # Publish event before subscribing
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "old_event", {}, time.time()))

    # Subscribe without replay
    subscriber = SSESubscriber(
        filter=SubscriptionFilter(channels=[EventChannel.AUDIT]),
        replay_buffer=False
    )

    events_received = []

    async def collect_events():
        count = 0
        async for event in subscriber.stream():
            events_received.append(event)
            count += 1
            if count >= 1:
                break

    stream_task = asyncio.create_task(collect_events())

    await asyncio.sleep(0.1)

    # Publish new event
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "new_event", {}, time.time()))

    await asyncio.wait_for(stream_task, timeout=2.0)

    # Should only receive new event (not old buffered event)
    assert len(events_received) == 1
    assert events_received[0].event_type == "new_event"
