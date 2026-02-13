"""
Test Suite for MissionQueueManager EventStream Integration
Tests the migration from legacy MISSION_STREAM to unified EventStream
"""
import pytest
import asyncio
import os
from datetime import datetime
import uuid

# Set environment variable BEFORE importing queue module
os.environ["USE_EVENT_STREAM"] = "true"

# Import MissionQueueManager
try:
    from modules.mission_system.queue import MissionQueueManager
    from modules.mission_system.models import (
        Mission, MissionStatus, MissionPriority, MissionType, AgentRequirements
    )
    MISSION_SYSTEM_AVAILABLE = True
except ImportError:
    MISSION_SYSTEM_AVAILABLE = False
    pytest.skip("Mission System not available", allow_module_level=True)

# Import EventStream
try:
    from backend.mission_control_core.core.event_stream import EventType
    EVENT_STREAM_AVAILABLE = True
except ImportError:
    EVENT_STREAM_AVAILABLE = False
    pytest.skip("EventStream not available", allow_module_level=True)


@pytest.fixture
async def queue_manager():
    """Fixture: Create MissionQueueManager with EventStream enabled"""
    manager = MissionQueueManager(redis_url="redis://localhost:6379")
    await manager.connect()
    yield manager
    await manager.disconnect()


@pytest.fixture
def sample_mission():
    """Fixture: Create sample mission"""
    return Mission(
        id=f"mission_{uuid.uuid4().hex[:8]}",
        name="Test Mission",
        description="Testing EventStream integration",
        mission_type=MissionType.GENERAL,
        priority=MissionPriority.NORMAL,
        status=MissionStatus.PENDING,
        agent_requirements=AgentRequirements(
            skills_required=["python", "async"],
            min_experience=1
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


class TestEventStreamIntegration:
    """Test EventStream integration in MissionQueueManager"""

    @pytest.mark.asyncio
    async def test_queue_manager_eventstream_enabled(self, queue_manager):
        """Test that EventStream is enabled and initialized"""
        assert queue_manager.use_event_stream is True
        assert queue_manager.event_stream is not None
        assert queue_manager.event_stream._initialized is True
        assert queue_manager.event_stream._running is True

    @pytest.mark.asyncio
    async def test_enqueue_mission_publishes_to_eventstream(self, queue_manager, sample_mission):
        """Test that enqueue_mission publishes MISSION_CREATED event"""
        # Enqueue mission
        result = await queue_manager.enqueue_mission(sample_mission)
        assert result is True

        # Small delay for event processing
        await asyncio.sleep(0.1)

        # Verify event was published to EventStream
        events = await queue_manager.event_stream.get_event_history(limit=10)

        # Find our MISSION_CREATED event
        mission_event = next(
            (e for e in events
             if e.type == EventType.MISSION_CREATED
             and e.payload.get("mission_id") == sample_mission.id),
            None
        )

        assert mission_event is not None, "MISSION_CREATED event not found in EventStream"
        assert mission_event.source == "mission_queue_manager"
        assert mission_event.mission_id == sample_mission.id
        assert mission_event.payload["mission_name"] == sample_mission.name
        assert mission_event.payload["priority"] == sample_mission.priority.value

    @pytest.mark.asyncio
    async def test_status_update_publishes_events(self, queue_manager, sample_mission):
        """Test that update_mission_status publishes status events"""
        # Enqueue mission first
        await queue_manager.enqueue_mission(sample_mission)
        await asyncio.sleep(0.1)

        # Update to RUNNING (should publish MISSION_STARTED)
        result = await queue_manager.update_mission_status(
            sample_mission.id,
            MissionStatus.RUNNING
        )
        assert result is True
        await asyncio.sleep(0.1)

        # Verify MISSION_STARTED event
        events = await queue_manager.event_stream.get_event_history(limit=20)
        started_event = next(
            (e for e in events
             if e.type == EventType.MISSION_STARTED
             and e.mission_id == sample_mission.id),
            None
        )
        assert started_event is not None, "MISSION_STARTED event not found"
        assert started_event.payload["old_status"] == MissionStatus.PENDING.value
        assert started_event.payload["new_status"] == MissionStatus.RUNNING.value

        # Update to COMPLETED (should publish MISSION_COMPLETED)
        result = await queue_manager.update_mission_status(
            sample_mission.id,
            MissionStatus.COMPLETED,
            result={"success": True, "output": "Test completed"}
        )
        assert result is True
        await asyncio.sleep(0.1)

        # Verify MISSION_COMPLETED event
        events = await queue_manager.event_stream.get_event_history(limit=20)
        completed_event = next(
            (e for e in events
             if e.type == EventType.MISSION_COMPLETED
             and e.mission_id == sample_mission.id),
            None
        )
        assert completed_event is not None, "MISSION_COMPLETED event not found"
        assert completed_event.payload["new_status"] == MissionStatus.COMPLETED.value
        assert completed_event.payload["result"] == {"success": True, "output": "Test completed"}

    @pytest.mark.asyncio
    async def test_failed_mission_publishes_event(self, queue_manager, sample_mission):
        """Test that failed missions publish MISSION_FAILED event"""
        # Enqueue and start mission
        await queue_manager.enqueue_mission(sample_mission)
        await queue_manager.update_mission_status(sample_mission.id, MissionStatus.RUNNING)
        await asyncio.sleep(0.1)

        # Fail mission
        result = await queue_manager.update_mission_status(
            sample_mission.id,
            MissionStatus.FAILED,
            error_message="Test failure"
        )
        assert result is True
        await asyncio.sleep(0.1)

        # Verify MISSION_FAILED event
        events = await queue_manager.event_stream.get_event_history(limit=20)
        failed_event = next(
            (e for e in events
             if e.type == EventType.MISSION_FAILED
             and e.mission_id == sample_mission.id),
            None
        )
        assert failed_event is not None, "MISSION_FAILED event not found"
        assert failed_event.payload["error_message"] == "Test failure"

    @pytest.mark.asyncio
    async def test_cancelled_mission_publishes_event(self, queue_manager, sample_mission):
        """Test that cancelled missions publish MISSION_CANCELLED event"""
        # Enqueue mission
        await queue_manager.enqueue_mission(sample_mission)
        await asyncio.sleep(0.1)

        # Cancel mission
        result = await queue_manager.update_mission_status(
            sample_mission.id,
            MissionStatus.CANCELLED
        )
        assert result is True
        await asyncio.sleep(0.1)

        # Verify MISSION_CANCELLED event
        events = await queue_manager.event_stream.get_event_history(limit=20)
        cancelled_event = next(
            (e for e in events
             if e.type == EventType.MISSION_CANCELLED
             and e.mission_id == sample_mission.id),
            None
        )
        assert cancelled_event is not None, "MISSION_CANCELLED event not found"

    @pytest.mark.asyncio
    async def test_statistics_include_eventstream_stats(self, queue_manager):
        """Test that get_queue_statistics includes EventStream stats"""
        stats = await queue_manager.get_queue_statistics()

        # Should have event_stream fields
        assert "event_stream_enabled" in stats
        assert stats["event_stream_enabled"] is True
        assert "event_stream_stats" in stats
        assert stats["event_stream_stats"] is not None

        # EventStream stats should have expected fields
        event_stats = stats["event_stream_stats"]
        assert "stream_length" in event_stats
        assert "stream_running" in event_stats
        assert event_stats["stream_running"] is True


class TestBackwardCompatibility:
    """Test backward compatibility with legacy MISSION_STREAM"""

    @pytest.mark.asyncio
    async def test_legacy_mode_when_eventstream_disabled(self):
        """Test that queue works with EventStream disabled"""
        # Temporarily disable EventStream
        os.environ["USE_EVENT_STREAM"] = "false"

        manager = MissionQueueManager(redis_url="redis://localhost:6379")
        await manager.connect()

        # Should NOT have EventStream enabled
        assert manager.use_event_stream is False or manager.event_stream is None

        # But should still work with legacy MISSION_STREAM
        mission = Mission(
            id=f"mission_{uuid.uuid4().hex[:8]}",
            name="Legacy Test Mission",
            description="Testing legacy mode",
            mission_type=MissionType.GENERAL,
            priority=MissionPriority.NORMAL,
            status=MissionStatus.PENDING,
            agent_requirements=AgentRequirements(
                skills_required=[],
                min_experience=0
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        result = await manager.enqueue_mission(mission)
        assert result is True

        # Cleanup
        await manager.disconnect()
        os.environ["USE_EVENT_STREAM"] = "true"

    @pytest.mark.asyncio
    async def test_eventstream_failure_fallback(self, queue_manager, sample_mission):
        """Test fallback to legacy stream if EventStream fails"""
        # Simulate EventStream failure by stopping it
        if queue_manager.event_stream:
            await queue_manager.event_stream.stop()
            queue_manager.use_event_stream = False

        # Enqueue should still work with legacy stream
        result = await queue_manager.enqueue_mission(sample_mission)
        assert result is True


class TestMissionLifecycle:
    """Test complete mission lifecycle with EventStream events"""

    @pytest.mark.asyncio
    async def test_full_mission_lifecycle_events(self, queue_manager, sample_mission):
        """Test that all lifecycle events are published"""
        # 1. Enqueue (MISSION_CREATED)
        await queue_manager.enqueue_mission(sample_mission)
        await asyncio.sleep(0.1)

        # 2. Start (MISSION_STARTED)
        await queue_manager.update_mission_status(sample_mission.id, MissionStatus.RUNNING)
        await asyncio.sleep(0.1)

        # 3. Complete (MISSION_COMPLETED)
        await queue_manager.update_mission_status(
            sample_mission.id,
            MissionStatus.COMPLETED,
            result={"output": "Success"}
        )
        await asyncio.sleep(0.1)

        # Verify all 3 events
        events = await queue_manager.event_stream.get_event_history(
            mission_id=sample_mission.id,
            limit=50
        )

        mission_events = [e for e in events if e.mission_id == sample_mission.id]

        # Should have at least 3 events: CREATED, STARTED, COMPLETED
        assert len(mission_events) >= 3, f"Expected at least 3 events, got {len(mission_events)}"

        event_types = {e.type for e in mission_events}
        assert EventType.MISSION_CREATED in event_types
        assert EventType.MISSION_STARTED in event_types
        assert EventType.MISSION_COMPLETED in event_types


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
