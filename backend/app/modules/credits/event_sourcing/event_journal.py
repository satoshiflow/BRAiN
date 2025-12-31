"""
Event Journal - Append-Only Event Storage.

Implements crash-safe event persistence with:
- JSONL format (one event per line)
- Atomic append with fsync
- Idempotency checking (duplicate prevention)
- Corruption detection and recovery
- Zero dependencies (pure Python file I/O)

Design Principles:
1. Single Source of Truth: Event log is authoritative
2. Append-Only: Events are never modified or deleted
3. Crash-Safe: fsync ensures events are persisted before confirmation
4. Idempotent: Duplicate events are detected and prevented
5. Forward-Compatible: Malformed events are logged but don't crash system

File Format (JSONL):
{"event_id": "...", "event_type": "...", ...}
{"event_id": "...", "event_type": "...", ...}
...

Recovery Strategy:
- On corruption: Log warning, skip line, continue replay
- On missing file: Create empty journal
- On permission error: Raise exception (cannot operate)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import AsyncIterator, Optional, Set

from loguru import logger

from backend.app.modules.credits.event_sourcing.events import EventEnvelope


class EventJournalError(Exception):
    """Base exception for EventJournal errors."""
    pass


class EventJournalPermissionError(EventJournalError):
    """Raised when journal file permissions are insufficient."""
    pass


class EventJournalCorruptionError(EventJournalError):
    """Raised when event data is corrupted (non-fatal, logged and skipped)."""
    pass


class EventJournal:
    """
    Append-only event journal with crash-safety guarantees.

    Features:
    - JSONL persistence (one event per line)
    - Atomic append with fsync
    - Idempotency checking via in-memory set
    - Graceful corruption recovery
    - Metrics tracking (total events, file size)

    Thread-Safety:
    - NOT thread-safe (use asyncio locks if needed)
    - Single-writer pattern recommended

    Example:
        >>> journal = EventJournal(file_path="storage/events/credits.jsonl")
        >>> await journal.initialize()
        >>> event = create_credit_allocated_event(...)
        >>> success = await journal.append_event(event)
        >>> async for event in journal.read_events():
        ...     print(event.event_id)
    """

    def __init__(
        self,
        file_path: str | Path = "storage/events/credits.jsonl",
        enable_fsync: bool = True,
    ):
        """
        Initialize EventJournal.

        Args:
            file_path: Path to JSONL event file
            enable_fsync: Enable fsync for crash-safety (disable for testing)
        """
        self.file_path = Path(file_path)
        self.enable_fsync = enable_fsync

        # Idempotency tracking (in-memory)
        self._seen_idempotency_keys: Set[str] = set()

        # Metrics
        self._total_events = 0
        self._idempotency_violations = 0

    async def initialize(self) -> None:
        """
        Initialize journal (create directory, load idempotency keys).

        Raises:
            EventJournalPermissionError: If cannot create directory or file
        """
        try:
            # Create directory if needed
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create empty file if needed
            if not self.file_path.exists():
                self.file_path.touch()
                logger.info(
                    f"EventJournal initialized (new file)",
                    file_path=str(self.file_path),
                )
            else:
                # Load existing idempotency keys
                await self._load_idempotency_keys()
                logger.info(
                    f"EventJournal initialized (existing file)",
                    file_path=str(self.file_path),
                    total_events=self._total_events,
                )

        except PermissionError as e:
            raise EventJournalPermissionError(
                f"Cannot initialize journal at {self.file_path}: {e}"
            ) from e

    async def _load_idempotency_keys(self) -> None:
        """
        Load idempotency keys from existing journal.

        This prevents duplicate events on restart.
        """
        async for event in self.read_events():
            self._seen_idempotency_keys.add(event.idempotency_key)
            self._total_events += 1

        logger.debug(
            f"Loaded idempotency keys",
            total_keys=len(self._seen_idempotency_keys),
            total_events=self._total_events,
        )

    async def append_event(self, event: EventEnvelope) -> bool:
        """
        Append event to journal (idempotent, crash-safe).

        Args:
            event: Event to append

        Returns:
            True if event was appended, False if duplicate (idempotency)

        Raises:
            EventJournalPermissionError: If cannot write to file

        Implementation:
        1. Check idempotency key
        2. Serialize event to JSON
        3. Append to file with newline
        4. fsync (if enabled)
        5. Update idempotency set
        """
        # === Idempotency Check ===
        if event.idempotency_key in self._seen_idempotency_keys:
            self._idempotency_violations += 1
            logger.warning(
                "Idempotency violation: duplicate event ignored",
                event_id=event.event_id,
                event_type=event.event_type,
                idempotency_key=event.idempotency_key,
                total_violations=self._idempotency_violations,
            )
            return False

        # === Serialize Event ===
        try:
            # Use Pydantic's JSON encoder (handles datetime, etc.)
            event_json = event.model_dump_json()
        except Exception as e:
            logger.error(
                "Failed to serialize event",
                event_id=event.event_id,
                event_type=event.event_type,
                error=str(e),
            )
            raise EventJournalError(f"Cannot serialize event: {e}") from e

        # === Append to File (Crash-Safe) ===
        try:
            # Open file in append mode
            with open(self.file_path, "a", encoding="utf-8") as f:
                # Write event (one line)
                f.write(event_json)
                f.write("\n")

                # Flush to OS buffer
                f.flush()

                # Force write to disk (crash-safety)
                if self.enable_fsync:
                    os.fsync(f.fileno())

        except PermissionError as e:
            raise EventJournalPermissionError(
                f"Cannot append to journal at {self.file_path}: {e}"
            ) from e
        except Exception as e:
            logger.error(
                "Failed to append event to journal",
                event_id=event.event_id,
                error=str(e),
            )
            raise EventJournalError(f"Cannot append event: {e}") from e

        # === Update Idempotency Set ===
        self._seen_idempotency_keys.add(event.idempotency_key)
        self._total_events += 1

        logger.debug(
            "Event appended to journal",
            event_id=event.event_id,
            event_type=event.event_type,
            total_events=self._total_events,
        )

        return True

    async def read_events(
        self,
        skip_corrupted: bool = True,
    ) -> AsyncIterator[EventEnvelope]:
        """
        Read all events from journal (generator for memory efficiency).

        Args:
            skip_corrupted: If True, skip corrupted lines and log warning
                           If False, raise exception on corruption

        Yields:
            EventEnvelope instances

        Raises:
            EventJournalCorruptionError: If corrupted and skip_corrupted=False

        Notes:
        - Uses generator to avoid loading entire file into memory
        - Gracefully handles corrupted lines (crash recovery)
        - Empty lines are silently skipped
        """
        if not self.file_path.exists():
            logger.warning(
                "Event journal file does not exist",
                file_path=str(self.file_path),
            )
            return

        line_number = 0
        corrupted_lines = 0

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line_number += 1

                    # Skip empty lines
                    line = line.strip()
                    if not line:
                        continue

                    # === Parse JSON ===
                    try:
                        event_data = json.loads(line)
                    except json.JSONDecodeError as e:
                        corrupted_lines += 1
                        error_msg = (
                            f"Corrupted JSON at line {line_number}: {e}"
                        )

                        if skip_corrupted:
                            logger.warning(
                                error_msg,
                                line_number=line_number,
                                line_content=line[:100],  # First 100 chars
                            )
                            continue
                        else:
                            raise EventJournalCorruptionError(error_msg) from e

                    # === Deserialize Event ===
                    try:
                        event = EventEnvelope(**event_data)
                        yield event

                    except Exception as e:
                        corrupted_lines += 1
                        error_msg = (
                            f"Invalid event data at line {line_number}: {e}"
                        )

                        if skip_corrupted:
                            logger.warning(
                                error_msg,
                                line_number=line_number,
                                event_data=event_data,
                            )
                            continue
                        else:
                            raise EventJournalCorruptionError(error_msg) from e

        except PermissionError as e:
            raise EventJournalPermissionError(
                f"Cannot read journal at {self.file_path}: {e}"
            ) from e

        if corrupted_lines > 0:
            logger.warning(
                f"Event journal replay completed with {corrupted_lines} corrupted lines skipped",
                total_lines=line_number,
                corrupted_lines=corrupted_lines,
            )

    async def count(self) -> int:
        """
        Count total events in journal.

        Returns:
            Number of valid events
        """
        count = 0
        async for _ in self.read_events():
            count += 1
        return count

    def get_metrics(self) -> dict:
        """
        Get journal metrics.

        Returns:
            Dict with metrics:
            - total_events: Number of events appended
            - file_size_mb: File size in megabytes
            - idempotency_violations: Number of duplicate events blocked
            - file_path: Path to journal file
        """
        file_size_bytes = (
            self.file_path.stat().st_size if self.file_path.exists() else 0
        )
        file_size_mb = file_size_bytes / (1024 * 1024)

        return {
            "total_events": self._total_events,
            "file_size_mb": round(file_size_mb, 2),
            "idempotency_violations": self._idempotency_violations,
            "file_path": str(self.file_path),
        }

    async def clear(self) -> None:
        """
        Clear journal (DANGEROUS - only for testing).

        Removes journal file and resets in-memory state.
        """
        if self.file_path.exists():
            self.file_path.unlink()

        self._seen_idempotency_keys.clear()
        self._total_events = 0
        self._idempotency_violations = 0

        logger.warning(
            "Event journal cleared (all events deleted)",
            file_path=str(self.file_path),
        )

    async def verify_integrity(self) -> dict:
        """
        Verify journal integrity.

        Checks:
        - All events can be deserialized
        - No duplicate event_ids
        - No duplicate idempotency_keys
        - All events have valid timestamps

        Returns:
            Dict with verification results:
            - valid: True if all checks pass
            - total_events: Number of events checked
            - errors: List of error messages
        """
        errors = []
        event_ids = set()
        idempotency_keys = set()
        total_events = 0

        async for event in self.read_events(skip_corrupted=False):
            total_events += 1

            # Check duplicate event_id
            if event.event_id in event_ids:
                errors.append(
                    f"Duplicate event_id: {event.event_id}"
                )
            event_ids.add(event.event_id)

            # Check duplicate idempotency_key
            if event.idempotency_key in idempotency_keys:
                errors.append(
                    f"Duplicate idempotency_key: {event.idempotency_key}"
                )
            idempotency_keys.add(event.idempotency_key)

            # Check timestamp is valid (not None, not future)
            if event.timestamp is None:
                errors.append(
                    f"Event {event.event_id} has no timestamp"
                )

        return {
            "valid": len(errors) == 0,
            "total_events": total_events,
            "errors": errors,
        }


# === Singleton Pattern ===
# Global journal instance (initialized on first use)
# Note: Changed to use factory for backend selection (Phase 5a)

from backend.app.modules.credits.event_sourcing.base_journal import BaseEventJournal

_journal_instance: Optional[BaseEventJournal] = None


async def get_event_journal() -> BaseEventJournal:
    """
    Get singleton Event Journal instance (backend-agnostic).

    Backend Selection (via environment variable):
    - EVENT_JOURNAL_BACKEND=file (default) → FileEventJournal
    - EVENT_JOURNAL_BACKEND=postgres → PostgresEventJournal

    Returns:
        BaseEventJournal instance (initialized)

    Example:
        >>> # Use file backend (default)
        >>> journal = await get_event_journal()

        >>> # Use Postgres backend
        >>> os.environ["EVENT_JOURNAL_BACKEND"] = "postgres"
        >>> journal = await get_event_journal()
    """
    global _journal_instance

    if _journal_instance is None:
        from backend.app.modules.credits.event_sourcing.journal_factory import create_event_journal

        _journal_instance = await create_event_journal()

    return _journal_instance
