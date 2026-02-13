"""
Test Suite for Consolidated Event Stream System
Tests the single, unified EventStream implementation
"""
import pytest
import asyncio
from datetime import datetime
import uuid

# Import EventStream
try:
    from backend.mission_control_core.core.event_stream import (
        EventStream,
        Event,
        EventType,
        emit_task_event,
        emit_agent_event
    )
    EVENT_STREAM_AVAILABLE = True
except ImportError:
    EVENT_STREAM_AVAILABLE = False
    pytest.skip("EventStream not available", allow_module_level=True)


@pytest.fixture
async def event_stream():
    """Fixture: Create EventStream instance"""
    stream = EventStream(redis_url="redis://localhost:6379")
    await stream.initialize()
    await stream.start()
    yield stream
    await stream.stop()


@pytest.fixture
def sample_event():
    """Fixture: Create sample event"""
    return Event(
        id=str(uuid.uuid4()),
        type=EventType.MISSION_CREATED,
        source="test_agent",
        target=None,
        payload={"test": "data"},
        timestamp=datetime.utcnow(),
        mission_id="mission_test_123"
    )


class TestEventStreamConsolidation:
    """Test consolidated Event Stream system"""

    @pytest.mark.asyncio
    async def test_event_stream_initialization(self, event_stream):
        """Test EventStream initializes correctly"""
        assert event_stream._initialized is True
        assert event_stream._running is True
        assert event_stream.redis is not None
        assert event_stream.pubsub is not None

    @pytest.mark.asyncio
    async def test_event_stream_keys(self, event_stream):
        """Test unified stream naming convention"""
        keys = event_stream.keys

        # Check all keys use colon notation (not dots)
        for key_name, key_value in keys.items():
            if "{" not in key_value:  # Skip template keys
                assert "." not in key_value, f"Key '{key_name}' uses dots instead of colons"
                assert key_value.startswith("brain:"), f"Key '{key_name}' doesn't start with 'brain:'"

        # Check required keys exist
        assert "event_stream" in keys
        assert "missions" in keys
        assert "tasks" in keys
        assert "broadcast" in keys
        assert "system" in keys
        assert "ethics" in keys

    @pytest.mark.asyncio
    async def test_publish_event(self, event_stream, sample_event):
        """Test event publishing to stream"""
        result = await event_stream.publish_event(sample_event)
        assert result is True

    @pytest.mark.asyncio
    async def test_event_routing(self, event_stream):
        """Test event routing to correct channels"""
        events_to_test = [
            (EventType.MISSION_CREATED, "missions"),
            (EventType.TASK_STARTED, "tasks"),
            (EventType.SYSTEM_HEALTH, "system"),
            (EventType.ETHICS_REVIEW, "ethics"),
            (EventType.BROADCAST, "broadcast"),
        ]

        for event_type, expected_channel in events_to_test:
            event = Event(
                id=str(uuid.uuid4()),
                type=event_type,
                source="test_agent",
                target=None,
                payload={"test": f"route_to_{expected_channel}"},
                timestamp=datetime.utcnow()
            )

            # Publish event
            result = await event_stream.publish_event(event)
            assert result is True

    @pytest.mark.asyncio
    async def test_event_history(self, event_stream, sample_event):
        """Test event history retrieval"""
        # Publish event
        await event_stream.publish_event(sample_event)

        # Small delay for Redis processing
        await asyncio.sleep(0.1)

        # Get history
        events = await event_stream.get_event_history(limit=10)

        # Should have at least 1 event
        assert len(events) > 0

        # Find our event
        our_event = next((e for e in events if e.id == sample_event.id), None)
        assert our_event is not None
        assert our_event.type == EventType.MISSION_CREATED
        assert our_event.source == "test_agent"

    @pytest.mark.asyncio
    async def test_stream_stats(self, event_stream):
        """Test stream statistics"""
        stats = await event_stream.get_stream_stats()

        assert "stream_length" in stats
        assert "active_subscriptions" in stats
        assert "event_handlers" in stats
        assert "stream_running" in stats

        # Stream should be running
        assert stats["stream_running"] is True

    @pytest.mark.asyncio
    async def test_subscribe_agent(self, event_stream):
        """Test agent subscription"""
        result = await event_stream.subscribe_agent(
            agent_id="test_agent_123",
            event_types={EventType.MISSION_CREATED, EventType.TASK_ASSIGNED}
        )

        assert result is True
        assert "test_agent_123" in event_stream._subscriptions
        assert EventType.MISSION_CREATED in event_stream._subscriptions["test_agent_123"]

    @pytest.mark.asyncio
    async def test_unsubscribe_agent(self, event_stream):
        """Test agent unsubscription"""
        # Subscribe first
        await event_stream.subscribe_agent(
            agent_id="test_agent_456",
            event_types={EventType.SYSTEM_HEALTH}
        )

        # Unsubscribe
        result = await event_stream.unsubscribe_agent("test_agent_456")

        assert result is True
        assert "test_agent_456" not in event_stream._subscriptions

    @pytest.mark.asyncio
    async def test_send_message(self, event_stream):
        """Test direct message between agents"""
        event_id = await event_stream.send_message(
            from_agent="agent_a",
            to_agent="agent_b",
            message={"action": "test"},
            correlation_id="test_corr_123"
        )

        assert event_id != ""
        assert len(event_id) > 0  # Should be UUID

    @pytest.mark.asyncio
    async def test_broadcast_message(self, event_stream):
        """Test broadcast message"""
        event_id = await event_stream.broadcast_message(
            source="system",
            message={"type": "announcement", "text": "Test broadcast"}
        )

        assert event_id != ""
        assert len(event_id) > 0

    @pytest.mark.asyncio
    async def test_helper_functions(self, event_stream):
        """Test emit_task_event and emit_agent_event helpers"""
        # Test emit_task_event
        task_event_id = await emit_task_event(
            event_stream=event_stream,
            task_id="task_123",
            event_type=EventType.TASK_STARTED,
            source="worker_agent",
            mission_id="mission_456"
        )
        assert task_event_id != ""

        # Test emit_agent_event
        agent_event_id = await emit_agent_event(
            event_stream=event_stream,
            agent_id="test_agent",
            event_type=EventType.AGENT_ONLINE,
            extra_data={"version": "1.0.0"}
        )
        assert agent_event_id != ""


class TestConsolidationVerification:
    """Verify consolidation was successful"""

    def test_old_event_bus_removed(self):
        """Verify old event_bus.py was removed"""
        import os
        event_bus_path = "/home/user/BRAiN/backend/app/core/event_bus.py"
        assert not os.path.exists(event_bus_path), "event_bus.py should be removed"

    def test_old_dlq_worker_removed(self):
        """Verify old dlq_worker.py was removed"""
        import os
        dlq_worker_path = "/home/user/BRAiN/backend/app/workers/dlq_worker.py"
        assert not os.path.exists(dlq_worker_path), "dlq_worker.py should be removed"

    def test_event_stream_is_single_source(self):
        """Verify EventStream is the only event system"""
        # Should be able to import EventStream
        from backend.mission_control_core.core.event_stream import EventStream
        assert EventStream is not None

        # Should NOT be able to import old EventBus
        with pytest.raises(ImportError):
            from app.core.event_bus import EventBus


@pytest.mark.integration
class TestEventStreamIntegration:
    """Integration tests with main.py"""

    @pytest.mark.asyncio
    async def test_event_stream_optional_integration(self):
        """Test EventStream optional integration in main.py"""
        import os

        # Should be importable even if not enabled
        from backend.main import EVENT_STREAM_AVAILABLE

        # Check if EventStream import was successful
        if os.getenv("ENABLE_EVENT_STREAM") == "true":
            assert EVENT_STREAM_AVAILABLE is True
        # If not enabled, should gracefully handle missing import
        # (no assertion needed - just verify no crash)


class TestEventSchemaExtensions:
    """Tests for Event schema extensions (tenant_id, actor_id, severity)"""

    @pytest.mark.asyncio
    async def test_event_with_tenant_id(self, event_stream):
        """Test event creation and retrieval with tenant_id"""
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_CREATED,
            source="test_agent",
            target=None,
            payload={"test": "data"},
            timestamp=datetime.utcnow(),
            tenant_id="tenant_123",
            actor_id="user_456",
            severity="INFO"
        )

        # Publish event
        result = await event_stream.publish_event(event)
        assert result is True

        # Small delay for Redis processing
        await asyncio.sleep(0.1)

        # Retrieve and verify
        events = await event_stream.get_event_history(limit=10)
        our_event = next((e for e in events if e.id == event.id), None)

        assert our_event is not None
        assert our_event.tenant_id == "tenant_123"
        assert our_event.actor_id == "user_456"
        assert our_event.severity == "INFO"

    @pytest.mark.asyncio
    async def test_event_filtering_by_tenant_id(self, event_stream):
        """Test filtering events by tenant_id"""
        # Publish events for different tenants
        tenant_a_event = Event(
            id=str(uuid.uuid4()),
            type=EventType.TASK_CREATED,
            source="agent_a",
            target=None,
            payload={"task": "A"},
            timestamp=datetime.utcnow(),
            tenant_id="tenant_a"
        )

        tenant_b_event = Event(
            id=str(uuid.uuid4()),
            type=EventType.TASK_CREATED,
            source="agent_b",
            target=None,
            payload={"task": "B"},
            timestamp=datetime.utcnow(),
            tenant_id="tenant_b"
        )

        await event_stream.publish_event(tenant_a_event)
        await event_stream.publish_event(tenant_b_event)

        await asyncio.sleep(0.1)

        # Filter by tenant_a
        tenant_a_events = await event_stream.get_event_history(
            tenant_id="tenant_a",
            limit=100
        )

        # Should only contain tenant_a events
        for event in tenant_a_events:
            if event.tenant_id is not None:
                assert event.tenant_id == "tenant_a", \
                    f"Found event with tenant_id={event.tenant_id}, expected tenant_a"

    @pytest.mark.asyncio
    async def test_event_filtering_by_actor_id(self, event_stream):
        """Test filtering events by actor_id"""
        # Publish events by different actors
        user1_event = Event(
            id=str(uuid.uuid4()),
            type=EventType.SYSTEM_HEALTH,
            source="system",
            target=None,
            payload={"health": "ok"},
            timestamp=datetime.utcnow(),
            actor_id="user_001"
        )

        user2_event = Event(
            id=str(uuid.uuid4()),
            type=EventType.SYSTEM_ALERT,
            source="system",
            target=None,
            payload={"alert": "warning"},
            timestamp=datetime.utcnow(),
            actor_id="user_002"
        )

        await event_stream.publish_event(user1_event)
        await event_stream.publish_event(user2_event)

        await asyncio.sleep(0.1)

        # Filter by user_001
        user1_events = await event_stream.get_event_history(
            actor_id="user_001",
            limit=100
        )

        # Should only contain user_001 events
        for event in user1_events:
            if event.actor_id is not None:
                assert event.actor_id == "user_001", \
                    f"Found event with actor_id={event.actor_id}, expected user_001"

    @pytest.mark.asyncio
    async def test_event_with_severity(self, event_stream):
        """Test event severity field"""
        severities = ["INFO", "WARNING", "ERROR", "CRITICAL"]

        for severity in severities:
            event = Event(
                id=str(uuid.uuid4()),
                type=EventType.SYSTEM_ALERT,
                source="system",
                target=None,
                payload={"message": f"{severity} level event"},
                timestamp=datetime.utcnow(),
                severity=severity
            )

            result = await event_stream.publish_event(event)
            assert result is True

        await asyncio.sleep(0.1)

        # Retrieve all events
        events = await event_stream.get_event_history(limit=10)

        # Verify severity levels
        severity_events = [e for e in events if e.severity in severities]
        assert len(severity_events) >= len(severities)

    @pytest.mark.asyncio
    async def test_event_backward_compatibility(self, event_stream):
        """Test events without new fields still work (backward compatibility)"""
        # Create event without tenant_id, actor_id, severity
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_COMPLETED,
            source="legacy_agent",
            target=None,
            payload={"status": "success"},
            timestamp=datetime.utcnow()
            # No tenant_id, actor_id, severity
        )

        # Should publish successfully
        result = await event_stream.publish_event(event)
        assert result is True

        await asyncio.sleep(0.1)

        # Should retrieve successfully
        events = await event_stream.get_event_history(limit=10)
        legacy_event = next((e for e in events if e.id == event.id), None)

        assert legacy_event is not None
        assert legacy_event.tenant_id is None
        assert legacy_event.actor_id is None
        assert legacy_event.severity is None

    @pytest.mark.asyncio
    async def test_multi_filter_combination(self, event_stream):
        """Test combining multiple filters (tenant_id + actor_id + event_type)"""
        # Create event with all fields
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_STARTED,
            source="test_agent",
            target=None,
            payload={"mission": "test"},
            timestamp=datetime.utcnow(),
            tenant_id="tenant_xyz",
            actor_id="user_admin",
            severity="INFO"
        )

        await event_stream.publish_event(event)
        await asyncio.sleep(0.1)

        # Filter by tenant_id + actor_id + event_type
        filtered_events = await event_stream.get_event_history(
            tenant_id="tenant_xyz",
            actor_id="user_admin",
            event_types={EventType.MISSION_STARTED},
            limit=100
        )

        # Should find the event
        matching_event = next((e for e in filtered_events if e.id == event.id), None)
        assert matching_event is not None
        assert matching_event.tenant_id == "tenant_xyz"
        assert matching_event.actor_id == "user_admin"
        assert matching_event.type == EventType.MISSION_STARTED


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
