"""
Sprint 5: EventStream Integration Tests for Missions Module

Tests verify that Missions module correctly publishes events to EventStream
following Charter v1.0 specification.

Test Coverage:
- Missions Module: 6 tests
- Total: 6 tests

Run with: pytest backend/tests/test_missions_sprint5_events.py -v
"""

import sys
import os
import uuid
import time
import pytest
from typing import List, Dict, Any, Optional, Set
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


class MockRedis:
    """Mock Redis client with comprehensive operations for testing."""

    def __init__(self):
        self.data: Dict[str, str] = {}      # Key-value store (GET/SET)
        self.sets: Dict[str, Set[str]] = {} # Set storage (SADD/SMEMBERS)
        self.lists: Dict[str, List[str]] = {}  # List storage (RPUSH/LRANGE)

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return self.data.get(key)

    async def set(self, key: str, value: str) -> None:
        """Set key-value pair."""
        self.data[key] = value

    async def sadd(self, key: str, value: str) -> None:
        """Add value to set."""
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].add(value)

    async def smembers(self, key: str) -> Set[str]:
        """Get all members of set."""
        return self.sets.get(key, set())

    async def rpush(self, key: str, value: str) -> None:
        """Append value to list (right push)."""
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].append(value)

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        """Get range from list."""
        lst = self.lists.get(key, [])
        if stop == -1:
            return lst[start:]
        return lst[start:stop+1]


# Global MockRedis instance for test isolation
_mock_redis_instance: Optional[MockRedis] = None


async def mock_get_redis():
    """Mock get_redis function that returns persistent MockRedis instance."""
    global _mock_redis_instance
    if _mock_redis_instance is None:
        _mock_redis_instance = MockRedis()
    return _mock_redis_instance


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_event_stream():
    """Provide MockEventStream instance."""
    return MockEventStream()


@pytest.fixture
def setup_missions_module(mock_event_stream, monkeypatch):
    """Setup Missions module with mocked EventStream and Redis."""
    import backend.app.modules.missions.service as service_module

    # Reset global MockRedis instance
    global _mock_redis_instance
    _mock_redis_instance = MockRedis()

    # Store original Event class and get_redis function
    original_event = getattr(service_module, 'Event', None)
    original_get_redis = service_module.get_redis

    # Mock Event class
    service_module.Event = MockEvent

    # Mock get_redis function
    service_module.get_redis = mock_get_redis

    # Set event stream
    service_module.set_event_stream(mock_event_stream)

    yield service_module, mock_event_stream

    # Cleanup
    if original_event:
        service_module.Event = original_event
    service_module.get_redis = original_get_redis
    service_module.set_event_stream(None)
    mock_event_stream.clear()
    _mock_redis_instance = None


# =============================================================================
# Missions Module Tests
# =============================================================================

@pytest.mark.asyncio
async def test_mission_created(setup_missions_module):
    """Test mission.created event emission."""
    service_module, event_stream = setup_missions_module

    # Import models after module setup
    from backend.app.modules.missions.models import MissionCreate

    # Create mission
    payload = MissionCreate(
        name="Test Mission",
        description="Testing mission.created event",
        data={"key": "value"}
    )
    mission = await service_module.create_mission(payload)

    # Verify mission created
    assert mission is not None
    assert mission.name == "Test Mission"
    assert mission.description == "Testing mission.created event"
    assert mission.status.value == "PENDING"

    # Verify event emitted
    created_events = event_stream.get_events_by_type("mission.created")
    assert len(created_events) == 1

    event = created_events[0]
    assert event.type == "mission.created"
    assert event.source == "missions_service"
    assert event.target is None  # Broadcast event

    # Verify payload
    assert "mission_id" in event.payload
    assert event.payload["mission_id"] == mission.id
    assert event.payload["name"] == "Test Mission"
    assert event.payload["description"] == "Testing mission.created event"
    assert event.payload["status"] == "PENDING"
    assert "created_at" in event.payload
    assert isinstance(event.payload["created_at"], float)


@pytest.mark.asyncio
async def test_mission_status_changed(setup_missions_module):
    """Test mission.status_changed event emission."""
    service_module, event_stream = setup_missions_module

    # Import models
    from backend.app.modules.missions.models import MissionCreate, MissionStatus

    # Create mission first
    payload = MissionCreate(
        name="Status Test Mission",
        description="Testing status changes",
        data={}
    )
    mission = await service_module.create_mission(payload)
    event_stream.clear()  # Clear creation events

    # Update status PENDING → RUNNING
    updated_mission = await service_module.update_status(mission.id, MissionStatus.RUNNING)

    # Verify mission updated
    assert updated_mission is not None
    assert updated_mission.status == MissionStatus.RUNNING

    # Verify event emitted
    status_events = event_stream.get_events_by_type("mission.status_changed")
    assert len(status_events) == 1

    event = status_events[0]
    assert event.type == "mission.status_changed"
    assert event.source == "missions_service"
    assert event.target is None

    # Verify payload
    assert event.payload["mission_id"] == mission.id
    assert event.payload["old_status"] == "PENDING"
    assert event.payload["new_status"] == "RUNNING"
    assert "changed_at" in event.payload
    assert isinstance(event.payload["changed_at"], float)


@pytest.mark.asyncio
async def test_mission_log_appended(setup_missions_module):
    """Test mission.log_appended event emission."""
    service_module, event_stream = setup_missions_module

    # Import models
    from backend.app.modules.missions.models import MissionCreate, MissionLogEntry

    # Create mission first
    payload = MissionCreate(
        name="Log Test Mission",
        description="Testing log entries",
        data={}
    )
    mission = await service_module.create_mission(payload)
    event_stream.clear()  # Clear creation events

    # Append log entry
    log_entry = MissionLogEntry(
        level="info",
        message="Test log message",
        data={"step": 1}
    )
    await service_module.append_log_entry(mission.id, log_entry)

    # Verify event emitted
    log_events = event_stream.get_events_by_type("mission.log_appended")
    assert len(log_events) == 1

    event = log_events[0]
    assert event.type == "mission.log_appended"
    assert event.source == "missions_service"
    assert event.target is None

    # Verify payload
    assert event.payload["mission_id"] == mission.id
    assert event.payload["log_level"] == "info"
    assert event.payload["message"] == "Test log message"
    assert "appended_at" in event.payload
    assert isinstance(event.payload["appended_at"], float)


@pytest.mark.asyncio
async def test_mission_status_transitions(setup_missions_module):
    """Test multiple status transitions emit separate events."""
    service_module, event_stream = setup_missions_module

    # Import models
    from backend.app.modules.missions.models import MissionCreate, MissionStatus

    # Create mission
    payload = MissionCreate(
        name="Transition Test Mission",
        description="Testing multiple status transitions",
        data={}
    )
    mission = await service_module.create_mission(payload)
    event_stream.clear()  # Clear creation events

    # Transition 1: PENDING → RUNNING
    await service_module.update_status(mission.id, MissionStatus.RUNNING)

    # Transition 2: RUNNING → COMPLETED
    await service_module.update_status(mission.id, MissionStatus.COMPLETED)

    # Verify 2 status_changed events emitted
    status_events = event_stream.get_events_by_type("mission.status_changed")
    assert len(status_events) == 2

    # Verify first transition
    event1 = status_events[0]
    assert event1.payload["old_status"] == "PENDING"
    assert event1.payload["new_status"] == "RUNNING"

    # Verify second transition
    event2 = status_events[1]
    assert event2.payload["old_status"] == "RUNNING"
    assert event2.payload["new_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_mission_complete_workflow(setup_missions_module):
    """Test complete mission workflow with all events."""
    service_module, event_stream = setup_missions_module

    # Import models
    from backend.app.modules.missions.models import (
        MissionCreate,
        MissionStatus,
        MissionLogEntry
    )

    # 1. Create mission
    payload = MissionCreate(
        name="Workflow Test Mission",
        description="Complete workflow test",
        data={"workflow": "test"}
    )
    mission = await service_module.create_mission(payload)

    # 2. Add custom log entry
    log_entry = MissionLogEntry(
        level="info",
        message="Starting mission execution",
        data={"phase": "start"}
    )
    await service_module.append_log_entry(mission.id, log_entry)

    # 3. Update status to RUNNING
    await service_module.update_status(mission.id, MissionStatus.RUNNING)

    # 4. Add progress log
    progress_entry = MissionLogEntry(
        level="info",
        message="Mission in progress",
        data={"progress": 50}
    )
    await service_module.append_log_entry(mission.id, progress_entry)

    # 5. Complete mission
    await service_module.update_status(mission.id, MissionStatus.COMPLETED)

    # Verify all events emitted
    assert len(event_stream.events) > 0

    # Verify event types
    created_events = event_stream.get_events_by_type("mission.created")
    status_events = event_stream.get_events_by_type("mission.status_changed")
    log_events = event_stream.get_events_by_type("mission.log_appended")

    assert len(created_events) == 1
    assert len(status_events) == 2  # PENDING→RUNNING, RUNNING→COMPLETED
    # Note: create_mission() also calls append_log_entry() internally
    # So we have: 1 (auto) + 2 (manual) + 2 (from status changes) = 5 log events minimum
    assert len(log_events) >= 5


@pytest.mark.asyncio
async def test_mission_charter_compliance(setup_missions_module):
    """Test Missions events comply with Charter v1.0."""
    service_module, event_stream = setup_missions_module

    # Import models
    from backend.app.modules.missions.models import (
        MissionCreate,
        MissionStatus,
        MissionLogEntry
    )

    # Generate all event types
    payload = MissionCreate(
        name="Charter Test Mission",
        description="Testing Charter v1.0 compliance",
        data={}
    )
    mission = await service_module.create_mission(payload)

    log_entry = MissionLogEntry(
        level="info",
        message="Charter compliance test",
        data={}
    )
    await service_module.append_log_entry(mission.id, log_entry)
    await service_module.update_status(mission.id, MissionStatus.RUNNING)

    # Verify we have all 3 event types
    assert len(event_stream.events) >= 3, "Expected at least 3 events"

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
        assert event.type.startswith("mission."), "Event type must be namespaced"

        # Consistent source
        assert event.source == "missions_service", "Event source must be 'missions_service'"

        # Broadcast target
        assert event.target is None, "Missions events should be broadcast (target=None)"
