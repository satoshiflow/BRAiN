"""
Event Sourcing MVP Tests.

Tests for Hard Gates:
- Gate 1: Idempotency (duplicate events prevented)
- Gate 2: Ledger Invariants (Sum(deltas) = balance)
- Gate 4: Crash Recovery (replay produces same state)
- Gate 5: Failure Safety (subscriber errors don't crash system)
"""

import sys
import os
from pathlib import Path
import pytest
import tempfile
import shutil

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.modules.credits.event_sourcing import (
    # Core
    EventEnvelope,
    EventType,
    # Journal
    EventJournal,
    # Bus
    EventBus,
    # Projections
    ProjectionManager,
    # Replay
    ReplayEngine,
    # Event creators
    create_credit_allocated_event,
    create_credit_consumed_event,
    create_credit_refunded_event,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def temp_journal():
    """Create temporary event journal for testing."""
    temp_dir = tempfile.mkdtemp()
    journal_path = Path(temp_dir) / "test_events.jsonl"

    journal = EventJournal(file_path=journal_path, enable_fsync=False)
    await journal.initialize()

    yield journal

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
async def event_bus(temp_journal):
    """Create EventBus with temporary journal."""
    bus = EventBus(temp_journal)
    yield bus


@pytest.fixture
def projection_manager():
    """Create ProjectionManager."""
    manager = ProjectionManager()
    yield manager
    manager.clear_all()


@pytest.fixture
async def replay_engine(temp_journal, projection_manager):
    """Create ReplayEngine."""
    engine = ReplayEngine(temp_journal, projection_manager, verify_integrity=True)
    yield engine


# ============================================================================
# Gate 1: Idempotency
# ============================================================================


@pytest.mark.asyncio
async def test_idempotency_duplicate_events_ignored(temp_journal, event_bus):
    """
    Gate 1: Idempotency Test

    Verify:
    - Same event published twice
    - Second publish returns False (duplicate)
    - Only one event in journal
    """
    # Create event
    event = create_credit_allocated_event(
        entity_id="agent_123",
        entity_type="agent",
        amount=100.0,
        reason="Initial allocation",
        balance_after=100.0,
    )

    # Publish first time
    published1 = await event_bus.publish(event)
    assert published1 is True, "First publish should succeed"

    # Publish second time (duplicate)
    published2 = await event_bus.publish(event)
    assert published2 is False, "Second publish should be blocked (duplicate)"

    # Verify only one event in journal
    event_count = await temp_journal.count()
    assert event_count == 1, "Journal should contain exactly one event"


@pytest.mark.asyncio
async def test_idempotency_balance_not_doubled(
    temp_journal, event_bus, projection_manager, replay_engine
):
    """
    Gate 1: Idempotency Test (Balance)

    Verify:
    - Duplicate event doesn't double balance
    - Balance = 100.0 (not 200.0)
    """
    # Subscribe projections
    await projection_manager.subscribe_all(event_bus)

    # Create and publish event
    event = create_credit_allocated_event(
        entity_id="agent_123",
        entity_type="agent",
        amount=100.0,
        reason="Test",
        balance_after=100.0,
    )

    await event_bus.publish(event)
    await event_bus.publish(event)  # Duplicate

    # Replay to rebuild projections
    await replay_engine.replay_all()

    # Verify balance is not doubled
    balance = projection_manager.balance.get_balance("agent_123")
    assert balance == 100.0, f"Balance should be 100.0, got {balance}"


# ============================================================================
# Gate 2: Ledger Invariants
# ============================================================================


@pytest.mark.asyncio
async def test_ledger_invariants_sum_equals_balance(
    temp_journal, event_bus, projection_manager, replay_engine
):
    """
    Gate 2: Ledger Invariants Test

    Verify:
    - Sum(ledger deltas) = balance
    - Multiple operations (allocate, consume, refund)
    """
    await projection_manager.subscribe_all(event_bus)

    # Scenario: Allocate 100, consume 30, refund 10
    events = [
        create_credit_allocated_event(
            entity_id="agent_X",
            entity_type="agent",
            amount=100.0,
            reason="Initial",
            balance_after=100.0,
        ),
        create_credit_consumed_event(
            entity_id="agent_X",
            entity_type="agent",
            amount=30.0,
            reason="Mission",
            balance_after=70.0,
            mission_id="mission_1",
        ),
        create_credit_refunded_event(
            entity_id="agent_X",
            entity_type="agent",
            amount=10.0,
            reason="Failed mission",
            balance_after=80.0,
            mission_id="mission_1",
        ),
    ]

    for event in events:
        await event_bus.publish(event)

    # Replay
    metrics = await replay_engine.replay_all()

    # Verify integrity passed
    assert metrics["integrity_valid"] is True, "Integrity check should pass"
    assert len(metrics["integrity_errors"]) == 0, "No integrity errors expected"

    # Verify final balance
    balance = projection_manager.balance.get_balance("agent_X")
    assert balance == 80.0, f"Expected balance 80.0, got {balance}"

    # Verify ledger history
    history = projection_manager.ledger.get_history("agent_X")
    assert len(history) == 3, "Should have 3 ledger entries"

    # Compute sum of deltas
    total_delta = sum(entry.amount for entry in history)
    assert abs(total_delta - 80.0) < 0.01, f"Sum of deltas should be 80.0, got {total_delta}"


@pytest.mark.asyncio
async def test_ledger_invariants_no_nan_inf(
    temp_journal, event_bus, projection_manager, replay_engine
):
    """
    Gate 2: Ledger Invariants Test (NaN/Inf)

    Verify:
    - No NaN, Inf, or None balances
    - Valid numeric values only
    """
    await projection_manager.subscribe_all(event_bus)

    # Create events with valid numbers
    event = create_credit_allocated_event(
        entity_id="agent_Y",
        entity_type="agent",
        amount=50.0,
        reason="Test",
        balance_after=50.0,
    )

    await event_bus.publish(event)

    # Replay with integrity check
    metrics = await replay_engine.replay_all()

    assert metrics["integrity_valid"] is True
    assert metrics["integrity_errors_count"] == 0


# ============================================================================
# Gate 4: Crash Recovery
# ============================================================================


@pytest.mark.asyncio
async def test_crash_recovery_replay_restores_state(
    temp_journal, event_bus, projection_manager, replay_engine
):
    """
    Gate 4: Crash Recovery Test

    Verify:
    - Publish events
    - Clear projections (simulate crash)
    - Replay events
    - State restored correctly
    """
    await projection_manager.subscribe_all(event_bus)

    # Step 1: Publish events
    events = [
        create_credit_allocated_event(
            entity_id="agent_Z",
            entity_type="agent",
            amount=100.0,
            reason="Initial",
            balance_after=100.0,
        ),
        create_credit_consumed_event(
            entity_id="agent_Z",
            entity_type="agent",
            amount=40.0,
            reason="Mission",
            balance_after=60.0,
        ),
    ]

    for event in events:
        await event_bus.publish(event)

    # Verify initial balance
    balance_before = projection_manager.balance.get_balance("agent_Z")
    assert balance_before == 60.0

    # Step 2: Simulate crash (clear projections)
    projection_manager.clear_all()

    # Verify balance is cleared
    balance_after_crash = projection_manager.balance.get_balance("agent_Z")
    assert balance_after_crash == 0.0, "Balance should be 0 after crash"

    # Step 3: Replay events
    await projection_manager.subscribe_all(event_bus)  # Re-subscribe
    metrics = await replay_engine.replay_all()

    # Step 4: Verify state restored
    balance_after_replay = projection_manager.balance.get_balance("agent_Z")
    assert balance_after_replay == 60.0, f"Balance should be restored to 60.0, got {balance_after_replay}"

    # Verify metrics
    assert metrics["total_events"] == 2, "Should replay 2 events"
    assert metrics["integrity_valid"] is True


# ============================================================================
# Gate 5: Failure Safety
# ============================================================================


@pytest.mark.asyncio
async def test_failure_safety_subscriber_error_doesnt_crash(
    temp_journal, event_bus
):
    """
    Gate 5: Failure Safety Test

    Verify:
    - Subscriber raises exception
    - Event still persisted to journal
    - Other subscribers still notified
    - System doesn't crash
    """

    # Create failing subscriber
    async def failing_handler(event: EventEnvelope):
        raise ValueError("Subscriber error (intentional)")

    # Create working subscriber
    successful_calls = []

    async def working_handler(event: EventEnvelope):
        successful_calls.append(event.event_id)

    # Subscribe both
    event_bus.subscribe(EventType.CREDIT_ALLOCATED, failing_handler)
    event_bus.subscribe(EventType.CREDIT_ALLOCATED, working_handler)

    # Publish event
    event = create_credit_allocated_event(
        entity_id="agent_F",
        entity_type="agent",
        amount=100.0,
        reason="Test",
        balance_after=100.0,
    )

    published = await event_bus.publish(event)

    # Verify event was published (despite subscriber failure)
    assert published is True, "Event should be published"

    # Verify event in journal
    event_count = await temp_journal.count()
    assert event_count == 1, "Event should be in journal"

    # Verify working subscriber was called
    assert len(successful_calls) == 1, "Working subscriber should be called"

    # Verify metrics tracked subscriber error
    metrics = event_bus.get_metrics()
    assert metrics["total_subscriber_errors"] == 1, "Subscriber error should be tracked"


# ============================================================================
# Integration Test: Full Flow
# ============================================================================


@pytest.mark.asyncio
async def test_full_flow_publish_replay_verify(
    temp_journal, event_bus, projection_manager, replay_engine
):
    """
    Integration Test: Full Event Sourcing Flow

    Steps:
    1. Publish multiple events
    2. Verify projections updated
    3. Clear projections
    4. Replay events
    5. Verify state identical
    """
    await projection_manager.subscribe_all(event_bus)

    # Step 1: Publish events for multiple entities
    events = [
        # Agent A
        create_credit_allocated_event("agent_A", "agent", 100.0, "Initial", 100.0),
        create_credit_consumed_event("agent_A", "agent", 20.0, "Mission", 80.0),
        # Agent B
        create_credit_allocated_event("agent_B", "agent", 150.0, "Initial", 150.0),
        create_credit_consumed_event("agent_B", "agent", 50.0, "Mission", 100.0),
        create_credit_refunded_event("agent_B", "agent", 10.0, "Failed", 110.0),
    ]

    for event in events:
        await event_bus.publish(event)

    # Step 2: Verify projections
    balance_A = projection_manager.balance.get_balance("agent_A")
    balance_B = projection_manager.balance.get_balance("agent_B")

    assert balance_A == 80.0
    assert balance_B == 110.0

    # Step 3: Clear projections (simulate crash)
    projection_manager.clear_all()

    # Step 4: Replay events
    await projection_manager.subscribe_all(event_bus)
    metrics = await replay_engine.replay_all()

    # Step 5: Verify state identical
    balance_A_after = projection_manager.balance.get_balance("agent_A")
    balance_B_after = projection_manager.balance.get_balance("agent_B")

    assert balance_A_after == 80.0
    assert balance_B_after == 110.0

    # Verify metrics
    assert metrics["total_events"] == 5
    assert metrics["integrity_valid"] is True
    assert metrics["integrity_errors_count"] == 0


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
