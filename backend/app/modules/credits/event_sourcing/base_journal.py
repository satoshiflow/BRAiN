"""
Base Event Journal Interface.

Defines the contract for Event Journal implementations:
- FileEventJournal (JSONL)
- PostgresEventJournal (SQL)

All implementations must support:
- Append-only operations
- Idempotency (duplicate prevention)
- Async iteration for replay
- Metrics tracking
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict

from backend.app.modules.credits.event_sourcing.events import EventEnvelope


class BaseEventJournal(ABC):
    """
    Abstract base class for Event Journal implementations.

    Contract:
    1. initialize() — Setup (create tables, files, etc.)
    2. append_event(event) — Append with idempotency
    3. read_events() — Async generator for replay
    4. get_metrics() — Stats for monitoring
    """

    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the event journal.

        For file-based: Create directory and file
        For Postgres: Create tables (or check schema)
        """
        pass

    @abstractmethod
    async def append_event(self, event: EventEnvelope) -> bool:
        """
        Append event to journal (idempotent).

        Args:
            event: Event to append

        Returns:
            True if event was appended
            False if duplicate (idempotency)

        Raises:
            EventJournalError: On write failure
        """
        pass

    @abstractmethod
    async def read_events(
        self,
        skip_corrupted: bool = True,
    ) -> AsyncIterator[EventEnvelope]:
        """
        Read all events from journal (async generator).

        Args:
            skip_corrupted: If True, skip corrupted events and log warning

        Yields:
            EventEnvelope instances in order

        Raises:
            EventJournalCorruptionError: If corrupted and skip_corrupted=False
        """
        pass

    @abstractmethod
    def get_metrics(self) -> Dict:
        """
        Get journal metrics for monitoring.

        Returns:
            Dict with metrics (total_events, size, idempotency_violations, etc.)
        """
        pass
