"""
Test Suite for Threats Module EventStream Integration

Sprint 3: Threats EventStream Migration
Tests all 4 event types for Charter v1.0 compliance.
"""

import sys
import os
import pytest
import time
from typing import List, Dict, Any
from unittest.mock import AsyncMock, patch, MagicMock
import json

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.threats.models import (
    ThreatCreate,
    ThreatSeverity,
    ThreatStatus,
)


# ============================================================================
# Mock Redis Client
# ============================================================================

class MockRedis:
    """Mock Redis client for testing"""
    def __init__(self):
        self.data = {}
        self.sets = {}

    async def set(self, key: str, value: str):
        """Mock SET operation"""
        self.data[key] = value

    async def get(self, key: str):
        """Mock GET operation"""
        return self.data.get(key)

    async def sadd(self, key: str, *values):
        """Mock SADD operation"""
        if key not in self.sets:
            self.sets[key] = set()
        self.sets[key].update(values)

    async def smembers(self, key: str):
        """Mock SMEMBERS operation"""
        return self.sets.get(key, set())


# ============================================================================
# Mock EventStream
# ============================================================================

class MockEvent:
    """Mock Event for testing"""
    def __init__(self, type: str, source: str, target: str, payload: Dict[str, Any]):
        self.id = f"evt_test_{time.time()}"
        self.type = type
        self.source = source
        self.target = target
        self.timestamp = time.time()
        self.payload = payload
        self.meta = {"correlation_id": None, "version": "1.0"}


class MockEventStream:
    """Mock EventStream that captures published events"""
    def __init__(self):
        self.events: List[MockEvent] = []

    async def publish(self, event: MockEvent):
        """Capture event for later verification"""
        self.events.append(event)

    def get_events_by_type(self, event_type: str) -> List[MockEvent]:
        """Get all events of a specific type"""
        return [e for e in self.events if e.type == event_type]

    def clear(self):
        """Clear all captured events"""
        self.events.clear()


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    return MockRedis()


@pytest.fixture
def mock_event_stream():
    """Mock EventStream for testing"""
    return MockEventStream()


@pytest.fixture
def setup_threats_module(mock_redis, mock_event_stream):
    """Setup threats module with mocks"""
    # Import service module first
    import backend.app.modules.threats.service as service_module

    # Patch get_redis in the service module
    original_get_redis = service_module.get_redis
    service_module.get_redis = AsyncMock(return_value=mock_redis)

    # Patch Event class
    original_event = service_module.Event
    service_module.Event = MockEvent

    # Set event stream
    from app.modules.threats.service import set_event_stream
    set_event_stream(mock_event_stream)

    yield mock_redis, mock_event_stream

    # Cleanup
    service_module.get_redis = original_get_redis
    service_module.Event = original_event
    set_event_stream(None)


@pytest.fixture
def sql_injection_threat():
    """Sample SQL injection threat payload"""
    return ThreatCreate(
        type="sql_injection",
        source="api_gateway",
        severity=ThreatSeverity.HIGH,
        description="Detected SQL injection attempt in query parameter",
        metadata={
            "ip": "192.168.1.100",
            "endpoint": "/api/users/search",
            "parameter": "username",
            "payload": "' OR '1'='1"
        }
    )


@pytest.fixture
def xss_threat():
    """Sample XSS threat payload"""
    return ThreatCreate(
        type="xss",
        source="web_application_firewall",
        severity=ThreatSeverity.MEDIUM,
        description="XSS attempt detected in user input",
        metadata={
            "ip": "203.0.113.45",
            "user_agent": "Mozilla/5.0..."
        }
    )


# ============================================================================
# Test 1: threat.detected Event
# ============================================================================

@pytest.mark.asyncio
async def test_threat_detected_event(setup_threats_module, sql_injection_threat):
    """Test that threat.detected event is published when new threat is created"""
    mock_redis, mock_event_stream = setup_threats_module

    # Import service functions after patching
    from app.modules.threats.service import create_threat

    # Execute
    threat = await create_threat(sql_injection_threat)

    # Verify threat was created
    assert threat.id is not None
    assert threat.type == "sql_injection"
    assert threat.severity == ThreatSeverity.HIGH
    assert threat.status == ThreatStatus.OPEN

    # Verify event was published
    events = mock_event_stream.get_events_by_type("threat.detected")
    assert len(events) == 1

    event = events[0]
    assert event.type == "threat.detected"
    assert event.source == "threat_service"
    assert event.target is None
    assert event.payload["threat_id"] == threat.id
    assert event.payload["type"] == "sql_injection"
    assert event.payload["source"] == "api_gateway"
    assert event.payload["severity"] == "HIGH"
    assert event.payload["status"] == "OPEN"
    assert event.payload["description"] == "Detected SQL injection attempt in query parameter"
    assert "metadata" in event.payload
    assert event.payload["metadata"]["ip"] == "192.168.1.100"
    assert "detected_at" in event.payload
    assert event.payload["detected_at"] == threat.created_at


# ============================================================================
# Test 2: threat.status_changed Event
# ============================================================================

@pytest.mark.asyncio
async def test_threat_status_changed_event(setup_threats_module, sql_injection_threat):
    """Test that threat.status_changed event is published when status is updated"""
    mock_redis, mock_event_stream = setup_threats_module

    # Import service functions after patching
    from app.modules.threats.service import create_threat, update_threat_status

    # Create threat first
    threat = await create_threat(sql_injection_threat)

    # Clear creation events
    mock_event_stream.clear()

    # Update status
    updated_threat = await update_threat_status(threat.id, ThreatStatus.INVESTIGATING)

    # Verify status was updated
    assert updated_threat is not None
    assert updated_threat.status == ThreatStatus.INVESTIGATING

    # Verify event was published
    events = mock_event_stream.get_events_by_type("threat.status_changed")
    assert len(events) == 1

    event = events[0]
    assert event.type == "threat.status_changed"
    assert event.source == "threat_service"
    assert event.payload["threat_id"] == threat.id
    assert event.payload["type"] == "sql_injection"
    assert event.payload["severity"] == "HIGH"
    assert event.payload["old_status"] == "OPEN"
    assert event.payload["new_status"] == "INVESTIGATING"
    assert "changed_at" in event.payload


# ============================================================================
# Test 3: threat.escalated Event
# ============================================================================

@pytest.mark.asyncio
async def test_threat_escalated_event(setup_threats_module, sql_injection_threat):
    """Test that threat.escalated event is published when status changes to ESCALATED"""
    mock_redis, mock_event_stream = setup_threats_module

    # Import service functions after patching
    from app.modules.threats.service import create_threat, update_threat_status

    # Create threat and start investigation
    threat = await create_threat(sql_injection_threat)
    await update_threat_status(threat.id, ThreatStatus.INVESTIGATING)

    # Clear previous events
    mock_event_stream.clear()

    # Escalate threat
    escalated_threat = await update_threat_status(threat.id, ThreatStatus.ESCALATED)

    # Verify status was updated
    assert escalated_threat is not None
    assert escalated_threat.status == ThreatStatus.ESCALATED

    # Verify both events were published
    status_changed_events = mock_event_stream.get_events_by_type("threat.status_changed")
    escalated_events = mock_event_stream.get_events_by_type("threat.escalated")

    assert len(status_changed_events) == 1
    assert len(escalated_events) == 1

    # Verify threat.escalated event
    event = escalated_events[0]
    assert event.type == "threat.escalated"
    assert event.source == "threat_service"
    assert event.payload["threat_id"] == threat.id
    assert event.payload["type"] == "sql_injection"
    assert event.payload["severity"] == "HIGH"
    assert event.payload["old_status"] == "INVESTIGATING"
    assert "escalated_at" in event.payload


# ============================================================================
# Test 4: threat.mitigated Event
# ============================================================================

@pytest.mark.asyncio
async def test_threat_mitigated_event(setup_threats_module, sql_injection_threat):
    """Test that threat.mitigated event is published when status changes to MITIGATED"""
    mock_redis, mock_event_stream = setup_threats_module

    # Import service functions after patching
    from app.modules.threats.service import create_threat, update_threat_status

    # Create threat and start investigation
    threat = await create_threat(sql_injection_threat)
    await update_threat_status(threat.id, ThreatStatus.INVESTIGATING)

    # Clear previous events
    mock_event_stream.clear()

    # Mitigate threat
    mitigated_threat = await update_threat_status(threat.id, ThreatStatus.MITIGATED)

    # Verify status was updated
    assert mitigated_threat is not None
    assert mitigated_threat.status == ThreatStatus.MITIGATED

    # Verify both events were published
    status_changed_events = mock_event_stream.get_events_by_type("threat.status_changed")
    mitigated_events = mock_event_stream.get_events_by_type("threat.mitigated")

    assert len(status_changed_events) == 1
    assert len(mitigated_events) == 1

    # Verify threat.mitigated event
    event = mitigated_events[0]
    assert event.type == "threat.mitigated"
    assert event.source == "threat_service"
    assert event.payload["threat_id"] == threat.id
    assert event.payload["type"] == "sql_injection"
    assert event.payload["severity"] == "HIGH"
    assert event.payload["old_status"] == "INVESTIGATING"
    assert "mitigated_at" in event.payload
    assert "duration_seconds" in event.payload
    assert event.payload["duration_seconds"] > 0  # Should have some duration


# ============================================================================
# Test 5: Full Lifecycle (OPEN → INVESTIGATING → MITIGATED)
# ============================================================================

@pytest.mark.asyncio
async def test_event_lifecycle_full(setup_threats_module, sql_injection_threat):
    """Test full event lifecycle: detected → investigating → mitigated"""
    mock_redis, mock_event_stream = setup_threats_module

    # Import service functions after patching
    from app.modules.threats.service import create_threat, update_threat_status

    # Clear events
    mock_event_stream.clear()

    # Step 1: Create threat
    threat = await create_threat(sql_injection_threat)

    # Step 2: Start investigation
    await update_threat_status(threat.id, ThreatStatus.INVESTIGATING)

    # Step 3: Mitigate threat
    await update_threat_status(threat.id, ThreatStatus.MITIGATED)

    # Verify event sequence
    all_events = mock_event_stream.events

    # Should have 6 events:
    # 1. threat.detected
    # 2. threat.status_changed (OPEN → INVESTIGATING)
    # 3. threat.status_changed (INVESTIGATING → MITIGATED)
    # 4. threat.mitigated
    assert len(all_events) >= 4

    # Event 1: threat.detected
    detected_events = mock_event_stream.get_events_by_type("threat.detected")
    assert len(detected_events) == 1
    assert detected_events[0].payload["status"] == "OPEN"

    # Event 2-3: threat.status_changed (2 transitions)
    status_changed_events = mock_event_stream.get_events_by_type("threat.status_changed")
    assert len(status_changed_events) == 2

    # First status change: OPEN → INVESTIGATING
    assert status_changed_events[0].payload["old_status"] == "OPEN"
    assert status_changed_events[0].payload["new_status"] == "INVESTIGATING"

    # Second status change: INVESTIGATING → MITIGATED
    assert status_changed_events[1].payload["old_status"] == "INVESTIGATING"
    assert status_changed_events[1].payload["new_status"] == "MITIGATED"

    # Event 4: threat.mitigated
    mitigated_events = mock_event_stream.get_events_by_type("threat.mitigated")
    assert len(mitigated_events) == 1
    assert mitigated_events[0].payload["threat_id"] == threat.id


# ============================================================================
# Test 6: Escalation Lifecycle (OPEN → INVESTIGATING → ESCALATED → MITIGATED)
# ============================================================================

@pytest.mark.asyncio
async def test_event_lifecycle_escalation(setup_threats_module, xss_threat):
    """Test escalation lifecycle: detected → investigating → escalated → mitigated"""
    mock_redis, mock_event_stream = setup_threats_module

    # Import service functions after patching
    from app.modules.threats.service import create_threat, update_threat_status

    # Clear events
    mock_event_stream.clear()

    # Step 1: Create threat
    threat = await create_threat(xss_threat)

    # Step 2: Start investigation
    await update_threat_status(threat.id, ThreatStatus.INVESTIGATING)

    # Step 3: Escalate threat
    await update_threat_status(threat.id, ThreatStatus.ESCALATED)

    # Step 4: Mitigate escalated threat
    await update_threat_status(threat.id, ThreatStatus.MITIGATED)

    # Verify event sequence
    all_events = mock_event_stream.events

    # Should have 8 events:
    # 1. threat.detected
    # 2. threat.status_changed (OPEN → INVESTIGATING)
    # 3. threat.status_changed (INVESTIGATING → ESCALATED)
    # 4. threat.escalated
    # 5. threat.status_changed (ESCALATED → MITIGATED)
    # 6. threat.mitigated
    assert len(all_events) >= 6

    # Verify threat.detected
    detected_events = mock_event_stream.get_events_by_type("threat.detected")
    assert len(detected_events) == 1

    # Verify threat.status_changed (3 transitions)
    status_changed_events = mock_event_stream.get_events_by_type("threat.status_changed")
    assert len(status_changed_events) == 3

    # Verify threat.escalated
    escalated_events = mock_event_stream.get_events_by_type("threat.escalated")
    assert len(escalated_events) == 1
    assert escalated_events[0].payload["old_status"] == "INVESTIGATING"

    # Verify threat.mitigated
    mitigated_events = mock_event_stream.get_events_by_type("threat.mitigated")
    assert len(mitigated_events) == 1
    assert mitigated_events[0].payload["old_status"] == "ESCALATED"


# ============================================================================
# Test 7: Graceful Degradation (No EventStream)
# ============================================================================

@pytest.mark.asyncio
async def test_threats_work_without_eventstream(mock_redis, sql_injection_threat):
    """Test that threats module works correctly without EventStream (graceful degradation)"""
    # Import service module
    import backend.app.modules.threats.service as service_module

    # Patch get_redis in the service module
    original_get_redis = service_module.get_redis
    service_module.get_redis = AsyncMock(return_value=mock_redis)

    try:
        # Import service functions after patching
        from app.modules.threats.service import create_threat, update_threat_status, set_event_stream

        # Set EventStream to None
        set_event_stream(None)

        # Execute threat operations - should work normally
        threat = await create_threat(sql_injection_threat)

        # Verify threat was created
        assert threat.id is not None
        assert threat.type == "sql_injection"
        assert threat.status == ThreatStatus.OPEN

        # Update status - should work normally
        updated_threat = await update_threat_status(threat.id, ThreatStatus.INVESTIGATING)
        assert updated_threat is not None
        assert updated_threat.status == ThreatStatus.INVESTIGATING

        # Escalate - should work normally
        escalated_threat = await update_threat_status(threat.id, ThreatStatus.ESCALATED)
        assert escalated_threat is not None
        assert escalated_threat.status == ThreatStatus.ESCALATED

        # Mitigate - should work normally
        mitigated_threat = await update_threat_status(threat.id, ThreatStatus.MITIGATED)
        assert mitigated_threat is not None
        assert mitigated_threat.status == ThreatStatus.MITIGATED
    finally:
        # Restore get_redis
        service_module.get_redis = original_get_redis


# ============================================================================
# Test 8: Charter v1.0 Compliance - Event Envelope Structure
# ============================================================================

@pytest.mark.asyncio
async def test_event_envelope_charter_compliance(setup_threats_module, sql_injection_threat):
    """Test that events follow Charter v1.0 envelope specification"""
    mock_redis, mock_event_stream = setup_threats_module

    # Import service functions after patching
    from app.modules.threats.service import create_threat

    # Execute action
    threat = await create_threat(sql_injection_threat)

    # Get any event
    events = mock_event_stream.events
    assert len(events) > 0

    event = events[0]

    # Verify Charter v1.0 envelope structure
    assert hasattr(event, 'id'), "Event must have id"
    assert hasattr(event, 'type'), "Event must have type"
    assert hasattr(event, 'source'), "Event must have source"
    assert hasattr(event, 'target'), "Event must have target"
    assert hasattr(event, 'timestamp'), "Event must have timestamp"
    assert hasattr(event, 'payload'), "Event must have payload"
    assert hasattr(event, 'meta'), "Event must have meta"

    # Verify source
    assert event.source == "threat_service"

    # Verify meta structure
    assert "correlation_id" in event.meta
    assert "version" in event.meta
    assert event.meta["version"] == "1.0"

    # Verify payload contains expected fields
    assert isinstance(event.payload, dict)
    assert "threat_id" in event.payload
    assert "type" in event.payload
    assert "severity" in event.payload
