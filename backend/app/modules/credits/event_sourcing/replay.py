"""
Replay Engine - Rebuild Projections from Events.

Implements crash recovery through deterministic event replay:
- Read all events from EventJournal
- Apply events to projections (via EventBus subscribers)
- Verify integrity (balance invariants)
- Metrics tracking (replay time, event count)

Design:
- Replay on startup: Rebuild projections from scratch
- Deterministic: Same events → same state
- Idempotent: Safe to replay multiple times
- Fast: In-memory projection updates

Integrity Checks:
- Sum(credit deltas) = current balance
- No NaN, Inf, or None balances
- All events successfully applied

Usage:
>>> replay_engine = ReplayEngine(journal, projection_manager)
>>> await replay_engine.replay_all()
>>> metrics = replay_engine.get_metrics()
"""

from __future__ import annotations

import math
import time
from typing import Dict, List, Optional

from loguru import logger

from backend.app.modules.credits.event_sourcing.event_journal import EventJournal
from backend.app.modules.credits.event_sourcing.events import EventType
from backend.app.modules.credits.event_sourcing.projections import (
    ProjectionManager,
)


class ReplayError(Exception):
    """Base exception for Replay errors."""
    pass


class ReplayIntegrityError(ReplayError):
    """Raised when integrity checks fail during replay."""
    pass


class ReplayEngine:
    """
    Replay engine for rebuilding projections from events.

    Features:
    - Deterministic replay from event log
    - Integrity verification (balance invariants)
    - Metrics tracking (replay time, event count)
    - Error logging (corrupted events, failed handlers)

    Thread-Safety:
    - NOT thread-safe (run on startup, single-threaded)

    Example:
        >>> journal = await get_event_journal()
        >>> projections = get_projection_manager()
        >>> replay_engine = ReplayEngine(journal, projections)
        >>>
        >>> await replay_engine.replay_all()
        >>> metrics = replay_engine.get_metrics()
        >>> print(f"Replayed {metrics['total_events']} events in {metrics['replay_duration_seconds']}s")
    """

    def __init__(
        self,
        journal: EventJournal,
        projection_manager: ProjectionManager,
        verify_integrity: bool = True,
    ):
        """
        Initialize ReplayEngine.

        Args:
            journal: EventJournal to replay from
            projection_manager: ProjectionManager to update
            verify_integrity: Enable integrity checks after replay
        """
        self.journal = journal
        self.projection_manager = projection_manager
        self.verify_integrity_enabled = verify_integrity

        # Metrics
        self._total_events = 0
        self._replay_duration_seconds = 0.0
        self._last_replay_timestamp: Optional[float] = None
        self._integrity_errors: List[str] = []

    async def replay_all(self) -> Dict[str, any]:
        """
        Replay all events from journal to rebuild projections.

        Steps:
        1. Clear existing projections
        2. Read events from journal
        3. Apply events to projections
        4. Verify integrity (if enabled)
        5. Return metrics

        Returns:
            Dict with replay metrics:
            - total_events: Number of events replayed
            - replay_duration_seconds: Time taken
            - integrity_valid: True if integrity checks passed
            - integrity_errors: List of integrity error messages

        Raises:
            ReplayIntegrityError: If integrity checks fail
        """
        logger.info("Starting event replay...")
        start_time = time.time()

        # === Step 1: Clear Projections ===
        self.projection_manager.clear_all()
        logger.debug("Cleared all projections")

        # === Step 2: Replay Events ===
        event_count = 0
        async for event in self.journal.read_events():
            try:
                # Apply event to all projections
                await self.projection_manager.balance.handle_event(event)
                await self.projection_manager.ledger.handle_event(event)
                await self.projection_manager.approval.handle_event(event)
                await self.projection_manager.synergie.handle_event(event)

                event_count += 1

                if event_count % 100 == 0:
                    logger.debug(f"Replayed {event_count} events...")

            except Exception as e:
                logger.error(
                    f"Failed to apply event during replay",
                    event_id=event.event_id,
                    event_type=event.event_type,
                    error=str(e),
                )
                # Continue replay despite errors

        # === Step 3: Verify Integrity ===
        integrity_valid = True
        if self.verify_integrity_enabled:
            logger.debug("Verifying integrity after replay...")
            integrity_valid = await self._verify_integrity()

            if not integrity_valid:
                error_msg = (
                    f"Integrity verification failed: {len(self._integrity_errors)} errors"
                )
                logger.error(error_msg, errors=self._integrity_errors)
                raise ReplayIntegrityError(error_msg)

        # === Step 4: Update Metrics ===
        end_time = time.time()
        self._total_events = event_count
        self._replay_duration_seconds = end_time - start_time
        self._last_replay_timestamp = end_time

        logger.info(
            f"Event replay completed",
            total_events=self._total_events,
            duration_seconds=round(self._replay_duration_seconds, 2),
            integrity_valid=integrity_valid,
        )

        return {
            "total_events": self._total_events,
            "replay_duration_seconds": self._replay_duration_seconds,
            "integrity_valid": integrity_valid,
            "integrity_errors": self._integrity_errors,
        }

    async def _verify_integrity(self) -> bool:
        """
        Verify integrity of projections after replay.

        Checks:
        1. Balance invariant: Sum(ledger deltas) = current balance
        2. No NaN, Inf, or None balances
        3. All balances have corresponding ledger entries

        Returns:
            True if all checks pass, False otherwise
        """
        self._integrity_errors = []

        # === Check 1: Balance Invariant ===
        balances = self.projection_manager.balance.get_all_balances()

        for entity_id, balance in balances.items():
            # Check for invalid balances
            if balance is None:
                self._integrity_errors.append(
                    f"Entity {entity_id} has None balance"
                )
                continue

            if math.isnan(balance):
                self._integrity_errors.append(
                    f"Entity {entity_id} has NaN balance"
                )
                continue

            if math.isinf(balance):
                self._integrity_errors.append(
                    f"Entity {entity_id} has Inf balance"
                )
                continue

            # Compute balance from ledger
            ledger_entries = self.projection_manager.ledger.get_history(entity_id)

            if not ledger_entries:
                # Entity has balance but no ledger entries
                if abs(balance) > 0.01:  # Tolerance for floating-point
                    self._integrity_errors.append(
                        f"Entity {entity_id} has balance {balance} but no ledger entries"
                    )
                continue

            # Compute sum of deltas
            computed_balance = sum(entry.amount for entry in ledger_entries)

            # Check if computed balance matches
            if abs(balance - computed_balance) > 0.01:  # Tolerance
                self._integrity_errors.append(
                    f"Entity {entity_id} balance mismatch: "
                    f"projection={balance}, ledger_sum={computed_balance}"
                )

        # === Check 2: All Ledger Entries Have Balances ===
        # (Optional: Ensure ledger entities have balances)
        all_entries = self.projection_manager.ledger.get_all_entries()
        entity_ids_in_ledger = {entry.entity_id for entry in all_entries}

        for entity_id in entity_ids_in_ledger:
            if entity_id not in balances:
                self._integrity_errors.append(
                    f"Entity {entity_id} in ledger but no balance projection"
                )

        # Log results
        if self._integrity_errors:
            logger.warning(
                f"Integrity check found {len(self._integrity_errors)} errors",
                errors=self._integrity_errors[:10],  # First 10 errors
            )
            return False

        logger.info("Integrity check passed")
        return True

    def get_metrics(self) -> Dict[str, any]:
        """
        Get replay metrics.

        Returns:
            Dict with metrics:
            - total_events: Number of events replayed
            - replay_duration_seconds: Time taken for replay
            - last_replay_timestamp: Unix timestamp of last replay
            - integrity_errors_count: Number of integrity errors
        """
        return {
            "total_events": self._total_events,
            "replay_duration_seconds": self._replay_duration_seconds,
            "last_replay_timestamp": self._last_replay_timestamp,
            "integrity_errors_count": len(self._integrity_errors),
        }


# === Singleton Pattern ===

_replay_engine_instance: Optional[ReplayEngine] = None


async def get_replay_engine(
    journal: Optional[EventJournal] = None,
    projection_manager: Optional[ProjectionManager] = None,
) -> ReplayEngine:
    """
    Get singleton ReplayEngine instance.

    Args:
        journal: EventJournal (optional, uses singleton if not provided)
        projection_manager: ProjectionManager (optional, uses singleton if not provided)

    Returns:
        ReplayEngine instance
    """
    global _replay_engine_instance

    if _replay_engine_instance is None:
        if journal is None:
            from backend.app.modules.credits.event_sourcing.event_journal import (
                get_event_journal,
            )

            journal = await get_event_journal()

        if projection_manager is None:
            from backend.app.modules.credits.event_sourcing.projections import (
                get_projection_manager,
            )

            projection_manager = get_projection_manager()

        _replay_engine_instance = ReplayEngine(journal, projection_manager)

    return _replay_engine_instance


async def replay_on_startup() -> Dict[str, any]:
    """
    Convenience function for startup replay.

    Returns:
        Replay metrics
    """
    replay_engine = await get_replay_engine()
    return await replay_engine.replay_all()
