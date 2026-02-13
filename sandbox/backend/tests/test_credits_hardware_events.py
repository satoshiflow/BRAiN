"""
Sprint 5: EventStream Integration Tests for Credits & Hardware Modules

Tests verify that Credits and Hardware modules correctly publish events to EventStream
following Charter v1.0 specification.

Test Coverage:
- Credits Module: 2 tests
- Hardware Module: 4 tests
- Total: 6 tests

Run with: pytest backend/tests/test_credits_hardware_events.py -v
"""

import sys
import os
import uuid
import time
import pytest
from typing import List, Dict, Any

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


class MockMovementCommand:
    """Mock MovementCommand for testing."""

    def __init__(self, linear_x: float = 1.0, linear_y: float = 0.0, angular_z: float = 0.5):
        self.linear_x = linear_x
        self.linear_y = linear_y
        self.angular_z = angular_z

    def model_dump(self) -> dict:
        """Return dict representation."""
        return {
            "linear_x": self.linear_x,
            "linear_y": self.linear_y,
            "angular_z": self.angular_z,
        }


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_event_stream():
    """Provide MockEventStream instance."""
    return MockEventStream()


@pytest.fixture
def setup_credits_module(mock_event_stream):
    """Setup Credits module with mocked EventStream."""
    import backend.app.modules.credits.service as service_module

    # Store original Event class
    original_event = getattr(service_module, 'Event', None)

    # Mock Event class
    service_module.Event = MockEvent

    # Set event stream
    service_module.set_event_stream(mock_event_stream)

    yield service_module, mock_event_stream

    # Cleanup
    if original_event:
        service_module.Event = original_event
    service_module.set_event_stream(None)
    mock_event_stream.clear()


@pytest.fixture
def setup_hardware_module(mock_event_stream):
    """Setup Hardware module with mocked EventStream."""
    import backend.app.modules.hardware.router as router_module

    # Store original Event class
    original_event = getattr(router_module, 'Event', None)

    # Mock Event class
    router_module.Event = MockEvent

    # Set event stream
    router_module.set_event_stream(mock_event_stream)

    # Create mock command
    mock_command = MockMovementCommand()

    yield router_module, mock_event_stream, mock_command

    # Cleanup
    if original_event:
        router_module.Event = original_event
    router_module.set_event_stream(None)
    mock_event_stream.clear()


# =============================================================================
# Credits Module Tests
# =============================================================================

@pytest.mark.asyncio
async def test_credits_health_checked(setup_credits_module):
    """Test credits.health_checked event emission."""
    service_module, event_stream = setup_credits_module

    # Call health function
    result = await service_module.get_health()

    # Verify result
    assert result is not None
    assert result.status == "ok"

    # Verify event emitted
    health_events = event_stream.get_events_by_type("credits.health_checked")
    assert len(health_events) == 1

    event = health_events[0]
    assert event.type == "credits.health_checked"
    assert event.source == "credits_service"
    assert event.target is None  # Broadcast event

    # Verify payload
    assert "status" in event.payload
    assert event.payload["status"] == "ok"
    assert "checked_at" in event.payload
    assert isinstance(event.payload["checked_at"], float)


@pytest.mark.asyncio
async def test_credits_charter_compliance(setup_credits_module):
    """Test Credits events comply with Charter v1.0."""
    service_module, event_stream = setup_credits_module

    # Generate event
    await service_module.get_health()

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
        assert event.type.startswith("credits."), "Event type must be namespaced"


# =============================================================================
# Hardware Module Tests
# =============================================================================

@pytest.mark.asyncio
async def test_hardware_command_sent(setup_hardware_module):
    """Test hardware.command_sent event emission."""
    router_module, event_stream, mock_command = setup_hardware_module

    # Send movement command
    result = await router_module.send_movement_command("robot_001", mock_command)

    # Verify result
    assert result is not None
    assert result["robot_id"] == "robot_001"
    assert result["status"] == "command_sent"

    # Verify event emitted
    command_events = event_stream.get_events_by_type("hardware.command_sent")
    assert len(command_events) == 1

    event = command_events[0]
    assert event.type == "hardware.command_sent"
    assert event.source == "hardware_router"
    assert event.target is None  # Not targeted in current implementation

    # Verify payload
    assert "robot_id" in event.payload
    assert event.payload["robot_id"] == "robot_001"
    assert "command_type" in event.payload
    assert event.payload["command_type"] == "movement"
    assert "command" in event.payload
    assert isinstance(event.payload["command"], dict)
    assert "linear_x" in event.payload["command"]
    assert "linear_y" in event.payload["command"]
    assert "angular_z" in event.payload["command"]
    assert "sent_at" in event.payload
    assert isinstance(event.payload["sent_at"], float)


@pytest.mark.asyncio
async def test_hardware_state_queried(setup_hardware_module):
    """Test hardware.state_queried event emission."""
    router_module, event_stream, _ = setup_hardware_module

    # Query robot state
    result = await router_module.get_robot_state("robot_001")

    # Verify result
    assert result is not None
    assert result["robot_id"] == "robot_001"

    # Verify event emitted
    state_events = event_stream.get_events_by_type("hardware.state_queried")
    assert len(state_events) == 1

    event = state_events[0]
    assert event.type == "hardware.state_queried"
    assert event.source == "hardware_router"

    # Verify payload
    assert "robot_id" in event.payload
    assert event.payload["robot_id"] == "robot_001"
    assert "queried_at" in event.payload
    assert isinstance(event.payload["queried_at"], float)


@pytest.mark.asyncio
async def test_hardware_info_queried(setup_hardware_module):
    """Test hardware.info_queried event emission."""
    router_module, event_stream, _ = setup_hardware_module

    # Query hardware info
    result = await router_module.get_hardware_info()

    # Verify result
    assert result is not None
    assert "name" in result
    assert "version" in result

    # Verify event emitted
    info_events = event_stream.get_events_by_type("hardware.info_queried")
    assert len(info_events) == 1

    event = info_events[0]
    assert event.type == "hardware.info_queried"
    assert event.source == "hardware_router"
    assert event.target is None  # Broadcast event

    # Verify payload
    assert "version" in event.payload
    assert event.payload["version"] == "1.0.0"
    assert "queried_at" in event.payload
    assert isinstance(event.payload["queried_at"], float)


@pytest.mark.asyncio
async def test_hardware_charter_compliance(setup_hardware_module):
    """Test Hardware events comply with Charter v1.0."""
    router_module, event_stream, mock_command = setup_hardware_module

    # Generate multiple events
    await router_module.send_movement_command("robot_001", mock_command)
    await router_module.get_robot_state("robot_002")
    await router_module.get_hardware_info()

    # Verify all events comply with Charter v1.0
    assert len(event_stream.events) == 3, "Expected 3 events"

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
        assert event.type.startswith("hardware."), "Event type must be namespaced"

        # Consistent source
        assert event.source == "hardware_router", "Event source must be 'hardware_router'"


# =============================================================================
# Integration Test
# =============================================================================

@pytest.mark.asyncio
async def test_combined_modules_integration(setup_credits_module, setup_hardware_module):
    """Test that both modules can coexist and emit events independently."""
    credits_service, credits_stream = setup_credits_module
    hardware_router, hardware_stream, mock_command = setup_hardware_module

    # Call functions from both modules
    await credits_service.get_health()
    await hardware_router.send_movement_command("robot_001", mock_command)

    # Verify Credits events
    credits_events = credits_stream.get_events_by_type("credits.health_checked")
    assert len(credits_events) == 1

    # Verify Hardware events
    hardware_events = hardware_stream.get_events_by_type("hardware.command_sent")
    assert len(hardware_events) == 1

    # Verify event independence
    assert credits_events[0].source == "credits_service"
    assert hardware_events[0].source == "hardware_router"
