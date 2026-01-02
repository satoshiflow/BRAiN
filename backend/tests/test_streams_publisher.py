"""
Unit tests for SSE Publisher (Phase 3 Backend).

Tests event publishing, subscriber management, and buffering.
"""

import pytest
import asyncio
import time
from backend.app.modules.neurorail.streams.publisher import SSEPublisher
from backend.app.modules.neurorail.streams.schemas import StreamEvent, EventChannel


# ============================================================================
# Tests: Basic Publishing
# ============================================================================

@pytest.mark.asyncio
async def test_publisher_publish_event():
    """Test publishing event to subscribers."""
    publisher = SSEPublisher()

    # Create subscriber
    queue = await publisher.subscribe(channels=[EventChannel.AUDIT])

    # Publish event
    event = StreamEvent(
        channel=EventChannel.AUDIT,
        event_type="test_event",
        data={"key": "value"},
        timestamp=time.time()
    )
    await publisher.publish(event)

    # Subscriber should receive event
    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.channel == EventChannel.AUDIT
    assert received.event_type == "test_event"
    assert received.data["key"] == "value"


@pytest.mark.asyncio
async def test_publisher_multiple_subscribers():
    """Test event delivered to all subscribers."""
    publisher = SSEPublisher()

    # Create 3 subscribers
    queue1 = await publisher.subscribe(channels=[EventChannel.AUDIT])
    queue2 = await publisher.subscribe(channels=[EventChannel.AUDIT])
    queue3 = await publisher.subscribe(channels=[EventChannel.AUDIT])

    # Publish event
    event = StreamEvent(
        channel=EventChannel.AUDIT,
        event_type="test",
        data={},
        timestamp=time.time()
    )
    await publisher.publish(event)

    # All subscribers should receive
    received1 = await asyncio.wait_for(queue1.get(), timeout=1.0)
    received2 = await asyncio.wait_for(queue2.get(), timeout=1.0)
    received3 = await asyncio.wait_for(queue3.get(), timeout=1.0)

    assert received1.event_type == "test"
    assert received2.event_type == "test"
    assert received3.event_type == "test"


# ============================================================================
# Tests: Channel Routing
# ============================================================================

@pytest.mark.asyncio
async def test_publisher_channel_isolation():
    """Test events only delivered to subscribed channels."""
    publisher = SSEPublisher()

    # Subscribe to different channels
    audit_queue = await publisher.subscribe(channels=[EventChannel.AUDIT])
    metrics_queue = await publisher.subscribe(channels=[EventChannel.METRICS])

    # Publish to AUDIT
    event = StreamEvent(
        channel=EventChannel.AUDIT,
        event_type="audit_event",
        data={},
        timestamp=time.time()
    )
    await publisher.publish(event)

    # AUDIT subscriber should receive
    received = await asyncio.wait_for(audit_queue.get(), timeout=1.0)
    assert received.event_type == "audit_event"

    # METRICS subscriber should NOT receive (queue empty)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(metrics_queue.get(), timeout=0.1)


@pytest.mark.asyncio
async def test_publisher_all_channel_receives_all_events():
    """Test ALL channel receives events from all channels."""
    publisher = SSEPublisher()

    # Subscribe to ALL
    all_queue = await publisher.subscribe(channels=[EventChannel.ALL])

    # Publish to different channels
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "audit", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.METRICS, "metrics", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.REFLEX, "reflex", {}, time.time()))

    # ALL subscriber should receive all 3
    event1 = await asyncio.wait_for(all_queue.get(), timeout=1.0)
    event2 = await asyncio.wait_for(all_queue.get(), timeout=1.0)
    event3 = await asyncio.wait_for(all_queue.get(), timeout=1.0)

    event_types = {event1.event_type, event2.event_type, event3.event_type}
    assert event_types == {"audit", "metrics", "reflex"}


# ============================================================================
# Tests: Event Buffering
# ============================================================================

@pytest.mark.asyncio
async def test_publisher_buffer_replay_on_subscribe():
    """Test buffered events replayed to new subscribers."""
    publisher = SSEPublisher(buffer_size=10)

    # Publish 3 events BEFORE subscribing
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event1", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event2", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event3", {}, time.time()))

    # Subscribe with replay
    queue = await publisher.subscribe(channels=[EventChannel.AUDIT], replay_buffer=True)

    # Should immediately receive 3 buffered events
    event1 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event2 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event3 = await asyncio.wait_for(queue.get(), timeout=1.0)

    assert event1.event_type == "event1"
    assert event2.event_type == "event2"
    assert event3.event_type == "event3"


@pytest.mark.asyncio
async def test_publisher_buffer_no_replay():
    """Test buffer not replayed when replay_buffer=False."""
    publisher = SSEPublisher()

    # Publish event before subscribing
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "old_event", {}, time.time()))

    # Subscribe without replay
    queue = await publisher.subscribe(channels=[EventChannel.AUDIT], replay_buffer=False)

    # Should NOT receive old event (queue empty)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.1)


@pytest.mark.asyncio
async def test_publisher_buffer_size_limit():
    """Test buffer limited to buffer_size."""
    publisher = SSEPublisher(buffer_size=3)

    # Publish 5 events (exceeds buffer size)
    for i in range(5):
        await publisher.publish(StreamEvent(EventChannel.AUDIT, f"event{i}", {}, time.time()))

    # Subscribe with replay
    queue = await publisher.subscribe(channels=[EventChannel.AUDIT], replay_buffer=True)

    # Should only receive last 3 events (2, 3, 4)
    event1 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event2 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event3 = await asyncio.wait_for(queue.get(), timeout=1.0)

    assert event1.event_type == "event2"  # Oldest 2 were dropped
    assert event2.event_type == "event3"
    assert event3.event_type == "event4"


# ============================================================================
# Tests: Subscriber Management
# ============================================================================

@pytest.mark.asyncio
async def test_publisher_unsubscribe():
    """Test unsubscribing from channels."""
    publisher = SSEPublisher()

    # Subscribe
    queue = await publisher.subscribe(channels=[EventChannel.AUDIT])

    # Publish event - should receive
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event1", {}, time.time()))
    received = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert received.event_type == "event1"

    # Unsubscribe
    await publisher.unsubscribe(queue, channels=[EventChannel.AUDIT])

    # Publish event - should NOT receive
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event2", {}, time.time()))
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.1)


# ============================================================================
# Tests: Statistics
# ============================================================================

def test_publisher_stats():
    """Test publisher statistics."""
    publisher = SSEPublisher()
    stats = publisher.get_stats()

    assert "total_events_published" in stats
    assert "total_subscribers" in stats
    assert "subscribers_by_channel" in stats
    assert "buffer_sizes" in stats


@pytest.mark.asyncio
async def test_publisher_stats_updated():
    """Test stats updated after operations."""
    publisher = SSEPublisher()

    initial_stats = publisher.get_stats()
    assert initial_stats["total_events_published"] == 0

    # Publish event
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "test", {}, time.time()))

    updated_stats = publisher.get_stats()
    assert updated_stats["total_events_published"] == 1


# ============================================================================
# Tests: Clear Buffers
# ============================================================================

@pytest.mark.asyncio
async def test_publisher_clear_buffers():
    """Test clearing event buffers."""
    publisher = SSEPublisher()

    # Publish events
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event1", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event2", {}, time.time()))

    # Clear buffers
    await publisher.clear_buffers()

    # Subscribe with replay - should NOT receive old events
    queue = await publisher.subscribe(channels=[EventChannel.AUDIT], replay_buffer=True)
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(queue.get(), timeout=0.1)


# ============================================================================
# Tests: Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_publisher_queue_full_handling():
    """Test handling of full subscriber queues."""
    publisher = SSEPublisher()

    # Subscribe with very small queue
    queue = await publisher.subscribe(channels=[EventChannel.AUDIT], queue_size=2)

    # Fill queue
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event1", {}, time.time()))
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event2", {}, time.time()))

    # Queue is full - next publish should not block (event dropped)
    await publisher.publish(StreamEvent(EventChannel.AUDIT, "event3", {}, time.time()))

    # Drain queue - should get first 2 events
    event1 = await asyncio.wait_for(queue.get(), timeout=1.0)
    event2 = await asyncio.wait_for(queue.get(), timeout=1.0)

    assert event1.event_type == "event1"
    assert event2.event_type == "event2"
