"""
Test Suite for EventConsumer Idempotency (Charter v1.0)

Tests Charter compliance:
- Primary dedup key: (subscriber_name, stream_message_id)
- Replay same message → no duplicate effect
- New message with same payload → processed
- event.id is SECONDARY (audit only)
"""
import pytest
import asyncio
import uuid
import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

# Set environment for testing
os.environ["BRAIN_EVENTSTREAM_MODE"] = "required"

from backend.mission_control_core.core.event_stream import (
    EventStream, Event, EventType, EventConsumer
)


@pytest.fixture
async def event_stream():
    """Fixture: EventStream instance"""
    stream = EventStream(redis_url="redis://localhost:6379")
    await stream.initialize()
    await stream.start()
    yield stream
    await stream.stop()


@pytest.fixture
def mock_db_session():
    """Fixture: Mock DB session factory"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()

    def factory():
        return session

    return factory, session


@pytest.fixture
async def event_consumer(event_stream, mock_db_session):
    """Fixture: EventConsumer instance"""
    factory, session = mock_db_session

    consumer = EventConsumer(
        subscriber_name="test_subscriber",
        event_stream=event_stream,
        db_session_factory=factory,
        stream_name="brain:events:test",
        batch_size=5,
        block_ms=1000
    )

    yield consumer, session

    await consumer.stop()


class TestEventConsumerIdempotency:
    """Test idempotent event processing (Charter v1.0)"""

    @pytest.mark.asyncio
    async def test_dedup_key_is_stream_message_id(self, event_consumer):
        """
        Test: Primary dedup key is stream_message_id (NOT event.id)
        """
        consumer, mock_session = event_consumer

        # Simulate duplicate check
        mock_session.execute.return_value.scalar.return_value = None  # Not duplicate

        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_CREATED,
            source="test",
            target=None,
            payload={"test": "data"},
            timestamp=datetime.utcnow(),
            meta={"schema_version": 1, "producer": "test", "source_module": "test"}
        )

        stream_msg_id = "1735390000000-0"

        # Check that dedup query uses stream_message_id
        is_dup = await consumer._check_duplicate(
            mock_session,
            stream_msg_id,
            event.id
        )

        # Verify query was called with stream_message_id
        assert mock_session.execute.called
        call_args = mock_session.execute.call_args
        assert "stream_msg_id" in call_args[0][1]
        assert call_args[0][1]["stream_msg_id"] == stream_msg_id

    @pytest.mark.asyncio
    async def test_replay_same_stream_message_id_is_idempotent(
        self, event_stream, mock_db_session
    ):
        """
        Test: Replaying same stream_message_id → no duplicate effect
        """
        factory, mock_session = mock_db_session

        # First call: not duplicate
        # Second call: duplicate
        mock_session.execute.return_value.scalar.side_effect = [None, 1]

        consumer = EventConsumer(
            subscriber_name="test_idempotency",
            event_stream=event_stream,
            db_session_factory=factory,
            stream_name="brain:events:test"
        )

        handler_call_count = 0

        async def test_handler(event: Event):
            nonlocal handler_call_count
            handler_call_count += 1

        consumer.register_handler(EventType.MISSION_CREATED, test_handler)

        stream_msg_id = "1735390000000-0"
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_CREATED,
            source="test",
            target=None,
            payload={"mission_id": "test_mission"},
            timestamp=datetime.utcnow(),
            meta={"schema_version": 1, "producer": "test", "source_module": "missions"}
        )

        # Process message twice (same stream_message_id)
        await consumer._process_message(stream_msg_id, event.to_dict())
        await consumer._process_message(stream_msg_id, event.to_dict())

        # Handler should only be called ONCE
        assert handler_call_count == 1, "Duplicate message should not trigger handler"

    @pytest.mark.asyncio
    async def test_new_message_same_payload_is_processed(
        self, event_stream, mock_db_session
    ):
        """
        Test: New stream_message_id with same payload → processed
        """
        factory, mock_session = mock_db_session

        # Both messages are NOT duplicates (different stream_message_id)
        mock_session.execute.return_value.scalar.return_value = None

        consumer = EventConsumer(
            subscriber_name="test_new_message",
            event_stream=event_stream,
            db_session_factory=factory,
            stream_name="brain:events:test"
        )

        handler_call_count = 0

        async def test_handler(event: Event):
            nonlocal handler_call_count
            handler_call_count += 1

        consumer.register_handler(EventType.MISSION_CREATED, test_handler)

        # Same payload, different stream_message_id
        stream_msg_id_1 = "1735390000000-0"
        stream_msg_id_2 = "1735390000001-0"  # Different!

        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_CREATED,
            source="test",
            target=None,
            payload={"mission_id": "test_mission"},  # Same payload
            timestamp=datetime.utcnow(),
            meta={"schema_version": 1, "producer": "test", "source_module": "missions"}
        )

        # Process both messages
        await consumer._process_message(stream_msg_id_1, event.to_dict())
        await consumer._process_message(stream_msg_id_2, event.to_dict())

        # Handler should be called TWICE (different messages)
        assert handler_call_count == 2, "New message should be processed"

    @pytest.mark.asyncio
    async def test_dedup_record_contains_stream_message_id(self, event_consumer):
        """
        Test: Dedup record stores stream_message_id as PRIMARY key
        """
        consumer, mock_session = event_consumer

        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_CREATED,
            source="test",
            target=None,
            payload={"test": "data"},
            timestamp=datetime.utcnow(),
            tenant_id="tenant_123",
            meta={"schema_version": 1, "producer": "test", "source_module": "missions"}
        )

        stream_msg_id = "1735390000000-0"

        # Mark as processed
        await consumer._mark_processed(
            mock_session,
            stream_msg_id,
            event
        )

        # Verify INSERT query includes stream_message_id
        assert mock_session.execute.called
        call_args = mock_session.execute.call_args
        assert "stream_msg_id" in call_args[0][1]
        assert call_args[0][1]["stream_msg_id"] == stream_msg_id
        assert call_args[0][1]["subscriber"] == "test_subscriber"

        # Verify event.id is stored as SECONDARY (audit)
        assert call_args[0][1]["event_id"] == event.id

    @pytest.mark.asyncio
    async def test_permanent_error_acks_message(self, event_stream, mock_db_session):
        """
        Test: Permanent error → ACK message (avoid infinite retry)
        """
        factory, mock_session = mock_db_session
        mock_session.execute.return_value.scalar.return_value = None  # Not duplicate

        consumer = EventConsumer(
            subscriber_name="test_error_handling",
            event_stream=event_stream,
            db_session_factory=factory,
            stream_name="brain:events:test"
        )

        async def failing_handler(event: Event):
            raise ValueError("Permanent error")  # Permanent

        consumer.register_handler(EventType.MISSION_CREATED, failing_handler)

        stream_msg_id = "1735390000000-0"
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_CREATED,
            source="test",
            target=None,
            payload={"test": "data"},
            timestamp=datetime.utcnow(),
            meta={"schema_version": 1, "producer": "test", "source_module": "missions"}
        )

        # Mock ACK
        consumer._ack_message = AsyncMock()

        # Process message (should fail but ACK)
        await consumer._process_message(stream_msg_id, event.to_dict())

        # Verify ACK was called (permanent error)
        assert consumer._ack_message.called

    @pytest.mark.asyncio
    async def test_transient_error_no_ack(self, event_stream, mock_db_session):
        """
        Test: Transient error → NO ACK (will retry)
        """
        factory, mock_session = mock_db_session
        mock_session.execute.return_value.scalar.return_value = None  # Not duplicate

        consumer = EventConsumer(
            subscriber_name="test_transient_error",
            event_stream=event_stream,
            db_session_factory=factory,
            stream_name="brain:events:test"
        )

        async def failing_handler(event: Event):
            raise ConnectionError("Transient error")  # Transient

        consumer.register_handler(EventType.MISSION_CREATED, failing_handler)

        stream_msg_id = "1735390000000-0"
        event = Event(
            id=str(uuid.uuid4()),
            type=EventType.MISSION_CREATED,
            source="test",
            target=None,
            payload={"test": "data"},
            timestamp=datetime.utcnow(),
            meta={"schema_version": 1, "producer": "test", "source_module": "missions"}
        )

        # Mock ACK
        consumer._ack_message = AsyncMock()

        # Process message (should fail but NOT ACK)
        await consumer._process_message(stream_msg_id, event.to_dict())

        # Verify ACK was NOT called (transient error → retry)
        assert not consumer._ack_message.called


class TestEventConsumerIntegration:
    """Integration tests with real Redis (if available)"""

    @pytest.mark.asyncio
    async def test_consumer_registers_handler(self, event_consumer):
        """Test: Handler registration works"""
        consumer, _ = event_consumer

        async def test_handler(event: Event):
            pass

        consumer.register_handler(EventType.MISSION_CREATED, test_handler)

        assert EventType.MISSION_CREATED in consumer._handlers
        assert consumer._handlers[EventType.MISSION_CREATED] == test_handler


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])
