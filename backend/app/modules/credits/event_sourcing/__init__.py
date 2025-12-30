"""
Event Sourcing Module for BRAiN Credit System.

Implements CQRS-Light architecture with append-only event journal
and in-memory projections for audit compliance (DSGVO Art. 5).

Architecture:
- Command Side: EventBus publishes events to append-only journal
- Query Side: In-memory projections rebuilt from event replay
- Crash Recovery: Deterministic replay from event log

Exports:
- EventEnvelope: Immutable event wrapper with causality tracking
- EventType: Enum of all event types in the system
- EventJournal: Append-only event storage with crash-safety
- get_event_journal: Singleton journal instance
- Event creation helpers for type-safe event construction
"""

from backend.app.modules.credits.event_sourcing.events import (
    EventEnvelope,
    EventType,
    create_credit_allocated_event,
    create_credit_consumed_event,
    create_credit_refunded_event,
    create_credit_withdrawn_event,
    create_credit_regenerated_event,
    create_approval_requested_event,
    create_approval_approved_event,
    create_approval_rejected_event,
    create_approval_expired_event,
    create_collaboration_recorded_event,
    create_reuse_detected_event,
    create_eoc_regulated_event,
    create_mission_rated_event,
)
from backend.app.modules.credits.event_sourcing.event_journal import (
    EventJournal,
    get_event_journal,
    EventJournalError,
    EventJournalPermissionError,
    EventJournalCorruptionError,
)

__all__ = [
    # Core types
    "EventEnvelope",
    "EventType",
    # Journal
    "EventJournal",
    "get_event_journal",
    "EventJournalError",
    "EventJournalPermissionError",
    "EventJournalCorruptionError",
    # Event creators (Ledger)
    "create_credit_allocated_event",
    "create_credit_consumed_event",
    "create_credit_refunded_event",
    "create_credit_withdrawn_event",
    "create_credit_regenerated_event",
    # Event creators (Approval)
    "create_approval_requested_event",
    "create_approval_approved_event",
    "create_approval_rejected_event",
    "create_approval_expired_event",
    # Event creators (Synergie)
    "create_collaboration_recorded_event",
    "create_reuse_detected_event",
    # Event creators (EoC)
    "create_eoc_regulated_event",
    # Event creators (Mission)
    "create_mission_rated_event",
]
