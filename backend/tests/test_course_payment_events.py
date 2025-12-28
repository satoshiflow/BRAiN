"""
Tests for Course Payment Event Integration

Tests idempotency, event handling, and enrollment creation from PayCore events.
"""

import pytest
import json
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch, MagicMock

from app.modules.course_factory.events.subscribers import CoursePaymentSubscriber
from app.modules.course_factory.events.handlers import (
    handle_payment_succeeded,
    handle_payment_failed,
    handle_refund_succeeded,
)
from app.core.events.idempotency import IdempotencyGuard, ProcessedEvent
from app.core.events.paycore_simulator import PayCoreSimulator


# ========================================
# Fixtures
# ========================================

@pytest.fixture
def payment_succeeded_event():
    """Sample payment succeeded event."""
    return {
        "event_type": "paycore.payment_succeeded",
        "trace_id": "evt_test123",
        "tenant_id": "tenant_demo",
        "intent_id": "intent_xyz",
        "tx_id": "tx_abc",
        "user_id": "user_456",
        "metadata": {
            "course_id": "course_test_001",
            "language": "de",
        },
        "timestamp": 1234567890.123,
    }


@pytest.fixture
def refund_succeeded_event():
    """Sample refund succeeded event."""
    return {
        "event_type": "paycore.refund_succeeded",
        "trace_id": "evt_refund123",
        "tenant_id": "tenant_demo",
        "intent_id": "intent_xyz",
        "refund_id": "ref_abc",
        "user_id": "user_456",
        "metadata": {
            "course_id": "course_test_001",
            "enrollment_id": "enr_test",
        },
        "timestamp": 1234567890.456,
    }


@pytest.fixture
def mock_monetization_service():
    """Mock MonetizationService."""
    service = AsyncMock()
    service.enroll_course = AsyncMock(
        return_value=MagicMock(
            enrollment_id="enr_mock123",
            course_id="course_test_001",
            actor_id="tenant_demo:user_456",
        )
    )
    return service


# ========================================
# Subscriber Tests
# ========================================

def test_subscriber_properties():
    """Test subscriber has correct properties."""
    subscriber = CoursePaymentSubscriber()

    assert subscriber.subscriber_name == "course_payment_subscriber"
    assert "paycore.payment_succeeded" in subscriber.event_types
    assert "paycore.payment_failed" in subscriber.event_types
    assert "paycore.refund_succeeded" in subscriber.event_types


@pytest.mark.asyncio
async def test_subscriber_dispatches_to_handlers(payment_succeeded_event):
    """Test subscriber dispatches events to correct handlers."""
    subscriber = CoursePaymentSubscriber()

    with patch(
        "app.modules.course_factory.events.handlers.handle_payment_succeeded",
        new=AsyncMock(),
    ) as mock_handler:
        await subscriber.handle(payment_succeeded_event)

        mock_handler.assert_called_once_with(payment_succeeded_event)


@pytest.mark.asyncio
async def test_subscriber_raises_on_missing_event_type():
    """Test subscriber raises ValueError for missing event_type."""
    subscriber = CoursePaymentSubscriber()

    with pytest.raises(ValueError, match="Event missing 'event_type'"):
        await subscriber.handle({})


# ========================================
# Handler Tests
# ========================================

@pytest.mark.asyncio
async def test_handle_payment_succeeded_creates_enrollment(
    payment_succeeded_event, mock_monetization_service
):
    """Test payment_succeeded handler creates enrollment."""
    with patch(
        "app.modules.course_factory.events.handlers.get_monetization_service",
        return_value=mock_monetization_service,
    ):
        await handle_payment_succeeded(payment_succeeded_event)

        # Verify enrollment was created
        mock_monetization_service.enroll_course.assert_called_once_with(
            course_id="course_test_001",
            language="de",
            actor_id="tenant_demo:user_456",
        )


@pytest.mark.asyncio
async def test_handle_payment_succeeded_validates_required_fields():
    """Test payment_succeeded validates required fields."""
    invalid_event = {
        "event_type": "paycore.payment_succeeded",
        "trace_id": "evt_invalid",
        # Missing tenant_id, user_id, metadata
    }

    with pytest.raises(ValueError, match="Missing required fields"):
        await handle_payment_succeeded(invalid_event)


@pytest.mark.asyncio
async def test_handle_payment_failed_logs_without_error(payment_succeeded_event):
    """Test payment_failed logs failure without raising errors."""
    failed_event = payment_succeeded_event.copy()
    failed_event["event_type"] = "paycore.payment_failed"

    # Should not raise
    await handle_payment_failed(failed_event)


@pytest.mark.asyncio
async def test_handle_refund_succeeded_logs_refund(refund_succeeded_event):
    """Test refund_succeeded logs refund (MVP: no revocation)."""
    # Should not raise
    await handle_refund_succeeded(refund_succeeded_event)


@pytest.mark.asyncio
async def test_handle_refund_validates_required_fields():
    """Test refund_succeeded validates required fields."""
    invalid_event = {
        "event_type": "paycore.refund_succeeded",
        "trace_id": "evt_invalid",
        # Missing required fields
    }

    with pytest.raises(ValueError, match="Missing required fields"):
        await handle_refund_succeeded(invalid_event)


# ========================================
# Idempotency Tests
# ========================================

@pytest.mark.asyncio
async def test_idempotency_prevents_duplicate_processing(
    payment_succeeded_event, mock_monetization_service
):
    """Test idempotency prevents duplicate enrollment."""
    # Mock DB session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.rollback = AsyncMock()

    guard = IdempotencyGuard(mock_session)

    with patch(
        "app.modules.course_factory.events.handlers.get_monetization_service",
        return_value=mock_monetization_service,
    ):
        # First call: should process
        should_process = await guard.should_process(
            "course_payment_subscriber", payment_succeeded_event
        )
        assert should_process is True

        # Simulate success
        await handle_payment_succeeded(payment_succeeded_event)

        # Second call: simulate duplicate (IntegrityError)
        from sqlalchemy.exc import IntegrityError

        mock_session.commit.side_effect = IntegrityError("", "", "")

        should_process_2 = await guard.should_process(
            "course_payment_subscriber", payment_succeeded_event
        )
        assert should_process_2 is False


@pytest.mark.asyncio
async def test_idempotency_allows_different_subscribers():
    """Test different subscribers can process same event."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    guard = IdempotencyGuard(mock_session)

    event = {"trace_id": "evt_123", "event_type": "test"}

    # Subscriber 1 can process
    result_1 = await guard.should_process("subscriber_1", event)
    assert result_1 is True

    # Subscriber 2 can also process (different subscriber)
    result_2 = await guard.should_process("subscriber_2", event)
    assert result_2 is True


# ========================================
# PayCore Simulator Tests
# ========================================

@pytest.mark.asyncio
async def test_paycore_simulator_publishes_payment_succeeded():
    """Test PayCore simulator publishes payment_succeeded event."""
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1234567890-0")

    with patch("app.core.events.paycore_simulator.get_redis", return_value=mock_redis):
        simulator = PayCoreSimulator()
        trace_id = await simulator.publish_payment_succeeded(
            tenant_id="tenant_test",
            user_id="user_123",
            course_id="course_456",
            language="en",
        )

        # Verify trace_id format
        assert trace_id.startswith("evt_")

        # Verify xadd was called
        mock_redis.xadd.assert_called_once()
        call_args = mock_redis.xadd.call_args

        # Verify stream name
        assert call_args[0][0] == "brain.events.paycore"

        # Verify event structure
        data_json = call_args[0][1]["data"]
        event = json.loads(data_json)

        assert event["event_type"] == "paycore.payment_succeeded"
        assert event["tenant_id"] == "tenant_test"
        assert event["user_id"] == "user_123"
        assert event["metadata"]["course_id"] == "course_456"
        assert event["metadata"]["language"] == "en"


@pytest.mark.asyncio
async def test_paycore_simulator_publishes_refund():
    """Test PayCore simulator publishes refund event."""
    mock_redis = AsyncMock()
    mock_redis.xadd = AsyncMock(return_value="1234567890-0")

    with patch("app.core.events.paycore_simulator.get_redis", return_value=mock_redis):
        simulator = PayCoreSimulator()
        trace_id = await simulator.publish_refund_succeeded(
            tenant_id="tenant_test",
            user_id="user_123",
            course_id="course_456",
            intent_id="intent_xyz",
            enrollment_id="enr_abc",
        )

        assert trace_id.startswith("evt_")
        mock_redis.xadd.assert_called_once()


# ========================================
# Integration Test (Mocked)
# ========================================

@pytest.mark.asyncio
async def test_end_to_end_payment_flow(
    payment_succeeded_event, mock_monetization_service
):
    """Test end-to-end payment flow from event to enrollment."""
    subscriber = CoursePaymentSubscriber()

    with patch(
        "app.modules.course_factory.events.handlers.get_monetization_service",
        return_value=mock_monetization_service,
    ):
        # Simulate event consumption
        await subscriber.handle(payment_succeeded_event)

        # Verify enrollment was created with correct parameters
        mock_monetization_service.enroll_course.assert_called_once()
        call_args = mock_monetization_service.enroll_course.call_args.kwargs

        assert call_args["course_id"] == "course_test_001"
        assert call_args["language"] == "de"
        assert call_args["actor_id"] == "tenant_demo:user_456"
