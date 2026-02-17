"""
Sprint 5: EventStream Integration Tests for Supervisor Module

Tests verify that Supervisor module correctly publishes events to EventStream
following Charter v1.0 specification.

Test Coverage:
- Supervisor Module: 4 tests
- Total: 4 tests

Run with: pytest backend/tests/test_supervisor_events.py -v
"""

import sys
import os
import uuid
import time
import pytest
from typing import List, Dict, Any
from datetime import datetime, timezone

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# =============================================================================
# Mock Infrastructure
# =============================================================================

class MockEvent:
    """Mock Event class for testing (Charter v1.0 compliant)."""

    def __init__(self, type: str, source: str, target, payload: dict):
        self.id = str(uuid.uuid4())
        self.type = type
        self.source = source
        self.target = target
        self.timestamp = time.time()
        self.payload = payload
        self.meta = {}


class MockEventStream:
    """Mock EventStream for capturing published events."""

    def __init__(self):
        self.events: List[MockEvent] = []

    async def publish(self, event):
        """Capture published event."""
        self.events.append(event)

    def get_events_by_type(self, event_type: str) -> List[MockEvent]:
        """Get all events of specific type."""
        return [e for e in self.events if e.type == event_type]

    def clear(self):
        """Clear all captured events."""
        self.events = []


class MockMissionStats:
    """Mock mission statistics from missions module."""

    def __init__(self):
        self.total = 150
        # Use UPPERCASE string keys to match MissionStatus enum values
        self.by_status = {
            "PENDING": 3,
            "RUNNING": 5,
            "COMPLETED": 130,
            "FAILED": 10,
            "CANCELLED": 2,
        }
        self.last_updated = time.time()


class MockStatsResponse:
    """Mock stats response from missions.service.get_stats."""

    def __init__(self):
        self.stats = MockMissionStats()


async def mock_get_stats():
    """Mock missions.service.get_stats function."""
    return MockStatsResponse()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_event_stream():
    """Provide MockEventStream instance."""
    return MockEventStream()


@pytest.fixture
def setup_supervisor_module(mock_event_stream):
    """Setup Supervisor module with mocked EventStream and missions dependency."""
    import backend.app.modules.supervisor.service as service_module

    # Store original Event class
    original_event = getattr(service_module, 'Event', None)

    # Store original get_stats function
    original_get_stats = service_module.get_stats

    # Mock Event class
    service_module.Event = MockEvent

    # Mock get_stats function
    service_module.get_stats = mock_get_stats

    # Set event stream
    service_module.set_event_stream(mock_event_stream)

    yield service_module, mock_event_stream

    # Cleanup
    if original_event:
        service_module.Event = original_event
    service_module.get_stats = original_get_stats
    service_module.set_event_stream(None)
    mock_event_stream.clear()


# =============================================================================
# Supervisor Module Tests
# =============================================================================

@pytest.mark.asyncio
async def test_supervisor_health_checked(setup_supervisor_module):
    """Test supervisor.health_checked event emission."""
    service_module, event_stream = setup_supervisor_module

    # Call health function
    result = await service_module.get_health()

    # Verify result
    assert result is not None
    assert result.status == "ok"
    assert isinstance(result.timestamp, datetime)

    # Verify event emitted
    health_events = event_stream.get_events_by_type("supervisor.health_checked")
    assert len(health_events) == 1

    event = health_events[0]
    assert event.type == "supervisor.health_checked"
    assert event.source == "supervisor_service"
    assert event.target is None  # Broadcast event

    # Verify payload
    assert "status" in event.payload
    assert event.payload["status"] == "ok"
    assert "checked_at" in event.payload
    assert isinstance(event.payload["checked_at"], float)


@pytest.mark.asyncio
async def test_supervisor_status_queried(setup_supervisor_module):
    """Test supervisor.status_queried event with mission statistics."""
    service_module, event_stream = setup_supervisor_module

    # Call status function (get_stats is already mocked in fixture)
    result = await service_module.get_status()

    # Verify result has correct mission counts
    assert result is not None
    assert result.status == "ok"
    assert result.total_missions == 150
    assert result.running_missions == 5
    assert result.pending_missions == 3
    assert result.completed_missions == 130
    assert result.failed_missions == 10
    assert result.cancelled_missions == 2
    assert isinstance(result.agents, list)
    assert len(result.agents) == 0  # Stub implementation

    # Verify event emitted
    status_events = event_stream.get_events_by_type("supervisor.status_queried")
    assert len(status_events) == 1

    event = status_events[0]
    assert event.type == "supervisor.status_queried"
    assert event.source == "supervisor_service"
    assert event.target is None  # Broadcast event

    # Verify payload contains all mission statistics
    assert "total_missions" in event.payload
    assert event.payload["total_missions"] == 150
    assert "running_missions" in event.payload
    assert event.payload["running_missions"] == 5
    assert "pending_missions" in event.payload
    assert event.payload["pending_missions"] == 3
    assert "completed_missions" in event.payload
    assert event.payload["completed_missions"] == 130
    assert "failed_missions" in event.payload
    assert event.payload["failed_missions"] == 10
    assert "cancelled_missions" in event.payload
    assert event.payload["cancelled_missions"] == 2
    assert "agent_count" in event.payload
    assert event.payload["agent_count"] == 0
    assert "queried_at" in event.payload
    assert isinstance(event.payload["queried_at"], float)


@pytest.mark.asyncio
async def test_supervisor_agents_listed(setup_supervisor_module):
    """Test supervisor.agents_listed event emission."""
    service_module, event_stream = setup_supervisor_module

    # Call list_agents function
    result = await service_module.list_agents()

    # Verify result (empty list stub)
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 0

    # Verify event emitted
    agents_events = event_stream.get_events_by_type("supervisor.agents_listed")
    assert len(agents_events) == 1

    event = agents_events[0]
    assert event.type == "supervisor.agents_listed"
    assert event.source == "supervisor_service"
    assert event.target is None  # Broadcast event

    # Verify payload
    assert "agent_count" in event.payload
    assert event.payload["agent_count"] == 0
    assert "queried_at" in event.payload
    assert isinstance(event.payload["queried_at"], float)


@pytest.mark.asyncio
async def test_supervisor_charter_compliance(setup_supervisor_module):
    """Test Supervisor events comply with Charter v1.0."""
    service_module, event_stream = setup_supervisor_module

    # Generate all events
    await service_module.get_health()
    await service_module.get_status()
    await service_module.list_agents()

    # Verify we have all 3 events
    assert len(event_stream.events) == 3, "Expected 3 events"

    # Verify all events comply with Charter v1.0
    for event in event_stream.events:
        # Required fields
        assert hasattr(event, 'id'), "Event missing 'id' field"
        assert hasattr(event, 'type'), "Event missing 'type' field"
        assert hasattr(event, 'source'), "Event missing 'source' field"
        assert hasattr(event, 'target'), "Event missing 'target' field"
        assert hasattr(event, 'timestamp'), "Event missing 'timestamp' field"
        assert hasattr(event, 'payload'), "Event missing 'payload' field"
        assert hasattr(event, 'meta'), "Event missing 'meta' field"

        # Field types
        assert isinstance(event.id, str), "Event 'id' must be string"
        assert isinstance(event.type, str), "Event 'type' must be string"
        assert isinstance(event.source, str), "Event 'source' must be string"
        assert isinstance(event.timestamp, float), "Event 'timestamp' must be float"
        assert isinstance(event.payload, dict), "Event 'payload' must be dict"
        assert isinstance(event.meta, dict), "Event 'meta' must be dict"

        # Namespaced type
        assert event.type.startswith("supervisor."), "Event type must be namespaced"

        # Consistent source
        assert event.source == "supervisor_service", "Event source must be 'supervisor_service'"

        # Broadcast target
        assert event.target is None, "Supervisor events should be broadcast (target=None)"
