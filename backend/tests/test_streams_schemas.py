"""
Unit tests for SSE Stream Schemas (Phase 3 Backend).

Tests event formatting and filtering.
"""

import pytest
import time
import json
from app.modules.neurorail.streams.schemas import (
    StreamEvent,
    EventChannel,
    SubscriptionFilter,
)


# ============================================================================
# Tests: StreamEvent
# ============================================================================

def test_stream_event_creation():
    """Test creating stream event."""
    event = StreamEvent(
        channel=EventChannel.AUDIT,
        event_type="execution_start",
        data={"attempt_id": "a_123"},
        timestamp=1234567890.0,
        event_id="evt_001"
    )

    assert event.channel == EventChannel.AUDIT
    assert event.event_type == "execution_start"
    assert event.data["attempt_id"] == "a_123"
    assert event.timestamp == 1234567890.0
    assert event.event_id == "evt_001"


def test_stream_event_to_sse_format():
    """Test SSE message formatting."""
    event = StreamEvent(
        channel=EventChannel.AUDIT,
        event_type="test_event",
        data={"key": "value"},
        timestamp=1234567890.0,
        event_id="evt_123"
    )

    sse_message = event.to_sse_format()

    # Check SSE format
    assert "id: evt_123" in sse_message
    assert "event: test_event" in sse_message
    assert "data: " in sse_message

    # Parse JSON data
    lines = sse_message.strip().split("\n")
    data_line = [l for l in lines if l.startswith("data: ")][0]
    data_json = data_line.replace("data: ", "")
    data_parsed = json.loads(data_json)

    assert data_parsed["channel"] == EventChannel.AUDIT
    assert data_parsed["event_type"] == "test_event"
    assert data_parsed["data"]["key"] == "value"
    assert data_parsed["timestamp"] == 1234567890.0


def test_stream_event_to_sse_format_without_id():
    """Test SSE formatting without event ID."""
    event = StreamEvent(
        channel=EventChannel.AUDIT,
        event_type="test_event",
        data={},
        timestamp=time.time(),
        event_id=None  # No ID
    )

    sse_message = event.to_sse_format()

    # Should not contain id line
    assert "id: " not in sse_message
    assert "event: test_event" in sse_message


# ============================================================================
# Tests: SubscriptionFilter
# ============================================================================

def test_subscription_filter_default():
    """Test default subscription filter."""
    filter = SubscriptionFilter()

    assert EventChannel.ALL in filter.channels
    assert filter.event_types is None
    assert filter.entity_ids is None


def test_subscription_filter_custom():
    """Test custom subscription filter."""
    filter = SubscriptionFilter(
        channels=[EventChannel.AUDIT, EventChannel.METRICS],
        event_types=["execution_start", "execution_success"],
        entity_ids=["m_123", "j_456"]
    )

    assert EventChannel.AUDIT in filter.channels
    assert EventChannel.METRICS in filter.channels
    assert "execution_start" in filter.event_types
    assert "m_123" in filter.entity_ids


# ============================================================================
# Tests: Filter Matching
# ============================================================================

def test_filter_matches_channel():
    """Test filter matches event channel."""
    filter = SubscriptionFilter(channels=[EventChannel.AUDIT])

    audit_event = StreamEvent(EventChannel.AUDIT, "test", {}, time.time())
    metrics_event = StreamEvent(EventChannel.METRICS, "test", {}, time.time())

    assert filter.matches(audit_event) is True
    assert filter.matches(metrics_event) is False


def test_filter_matches_all_channel():
    """Test ALL channel matches all events."""
    filter = SubscriptionFilter(channels=[EventChannel.ALL])

    audit_event = StreamEvent(EventChannel.AUDIT, "test", {}, time.time())
    metrics_event = StreamEvent(EventChannel.METRICS, "test", {}, time.time())
    reflex_event = StreamEvent(EventChannel.REFLEX, "test", {}, time.time())

    assert filter.matches(audit_event) is True
    assert filter.matches(metrics_event) is True
    assert filter.matches(reflex_event) is True


def test_filter_matches_event_type():
    """Test filter matches event type."""
    filter = SubscriptionFilter(
        channels=[EventChannel.AUDIT],
        event_types=["execution_start", "execution_success"]
    )

    start_event = StreamEvent(EventChannel.AUDIT, "execution_start", {}, time.time())
    failure_event = StreamEvent(EventChannel.AUDIT, "execution_failure", {}, time.time())

    assert filter.matches(start_event) is True
    assert filter.matches(failure_event) is False


def test_filter_matches_entity_id_mission():
    """Test filter matches mission_id."""
    filter = SubscriptionFilter(
        channels=[EventChannel.AUDIT],
        entity_ids=["m_123"]
    )

    matching_event = StreamEvent(
        EventChannel.AUDIT,
        "test",
        {"mission_id": "m_123"},
        time.time()
    )
    non_matching_event = StreamEvent(
        EventChannel.AUDIT,
        "test",
        {"mission_id": "m_999"},
        time.time()
    )

    assert filter.matches(matching_event) is True
    assert filter.matches(non_matching_event) is False


def test_filter_matches_entity_id_job():
    """Test filter matches job_id."""
    filter = SubscriptionFilter(
        channels=[EventChannel.AUDIT],
        entity_ids=["j_456"]
    )

    matching_event = StreamEvent(
        EventChannel.AUDIT,
        "test",
        {"job_id": "j_456"},
        time.time()
    )

    assert filter.matches(matching_event) is True


def test_filter_matches_multiple_criteria():
    """Test filter matches multiple criteria (AND logic)."""
    filter = SubscriptionFilter(
        channels=[EventChannel.AUDIT],
        event_types=["execution_start"],
        entity_ids=["m_123"]
    )

    # Matches all criteria
    matching_event = StreamEvent(
        EventChannel.AUDIT,
        "execution_start",
        {"mission_id": "m_123"},
        time.time()
    )

    # Wrong event type
    wrong_type_event = StreamEvent(
        EventChannel.AUDIT,
        "execution_failure",
        {"mission_id": "m_123"},
        time.time()
    )

    # Wrong entity ID
    wrong_entity_event = StreamEvent(
        EventChannel.AUDIT,
        "execution_start",
        {"mission_id": "m_999"},
        time.time()
    )

    assert filter.matches(matching_event) is True
    assert filter.matches(wrong_type_event) is False
    assert filter.matches(wrong_entity_event) is False


def test_filter_no_entity_id_in_event():
    """Test filter when event has no entity ID."""
    filter = SubscriptionFilter(
        channels=[EventChannel.AUDIT],
        entity_ids=["m_123"]
    )

    event_no_id = StreamEvent(
        EventChannel.AUDIT,
        "test",
        {},  # No entity IDs
        time.time()
    )

    assert filter.matches(event_no_id) is False


# ============================================================================
# Tests: EventChannel Enum
# ============================================================================

def test_event_channel_values():
    """Test EventChannel enum values."""
    assert EventChannel.AUDIT.value == "audit"
    assert EventChannel.LIFECYCLE.value == "lifecycle"
    assert EventChannel.METRICS.value == "metrics"
    assert EventChannel.REFLEX.value == "reflex"
    assert EventChannel.GOVERNOR.value == "governor"
    assert EventChannel.ENFORCEMENT.value == "enforcement"
    assert EventChannel.ALL.value == "all"


def test_event_channel_from_string():
    """Test creating EventChannel from string."""
    audit_channel = EventChannel("audit")
    assert audit_channel == EventChannel.AUDIT

    with pytest.raises(ValueError):
        EventChannel("invalid_channel")
