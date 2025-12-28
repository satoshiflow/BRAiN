"""
Idempotency Guard

Ensures events are processed exactly once using database-backed deduplication.
"""

from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlalchemy import Column, String, DateTime, PrimaryKeyConstraint, Index
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.db import Base


class ProcessedEvent(Base):
    """
    Tracks processed events for idempotency.

    Primary key: (subscriber_name, trace_id)
    Ensures each subscriber processes each event exactly once.
    """

    __tablename__ = "processed_events"

    subscriber_name = Column(String(100), nullable=False)
    trace_id = Column(String(100), nullable=False)
    event_type = Column(String(100), nullable=False)
    tenant_id = Column(String(100), nullable=True)  # For auditing
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        PrimaryKeyConstraint("subscriber_name", "trace_id"),
        Index("idx_processed_events_tenant", "tenant_id"),
        Index("idx_processed_events_type", "event_type"),
    )


class IdempotencyGuard:
    """
    Idempotency guard using database deduplication.

    Usage:
        guard = IdempotencyGuard(db_session)
        if await guard.should_process(subscriber, event):
            # Process event
            await guard.mark_processed(subscriber, event)
    """

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def should_process(self, subscriber_name: str, event: dict) -> bool:
        """
        Check if event should be processed.

        Args:
            subscriber_name: Subscriber identifier
            event: Event dict (must have trace_id)

        Returns:
            bool: True if should process, False if already processed
        """
        trace_id = event.get("trace_id")
        if not trace_id:
            logger.warning(
                f"[IdempotencyGuard] Event missing trace_id, allowing processing",
                subscriber=subscriber_name,
            )
            return True  # Allow if no trace_id (shouldn't happen)

        try:
            # Attempt to insert
            processed_event = ProcessedEvent(
                subscriber_name=subscriber_name,
                trace_id=trace_id,
                event_type=event.get("event_type", "unknown"),
                tenant_id=event.get("tenant_id"),
            )
            self.db.add(processed_event)
            await self.db.commit()

            logger.debug(
                f"[IdempotencyGuard] Event marked for processing",
                subscriber=subscriber_name,
                trace_id=trace_id,
            )
            return True

        except IntegrityError:
            # Duplicate key: already processed
            await self.db.rollback()
            logger.info(
                f"[IdempotencyGuard] Event already processed (idempotent skip)",
                subscriber=subscriber_name,
                trace_id=trace_id,
            )
            return False

    async def mark_processed(self, subscriber_name: str, event: dict) -> None:
        """
        Mark event as processed (for cases where should_process wasn't called).

        This is idempotent - safe to call multiple times.
        """
        trace_id = event.get("trace_id")
        if not trace_id:
            return  # Can't mark without trace_id

        try:
            processed_event = ProcessedEvent(
                subscriber_name=subscriber_name,
                trace_id=trace_id,
                event_type=event.get("event_type", "unknown"),
                tenant_id=event.get("tenant_id"),
            )
            self.db.add(processed_event)
            await self.db.commit()
        except IntegrityError:
            # Already marked
            await self.db.rollback()

    async def rollback_processing(self, subscriber_name: str, event: dict) -> None:
        """
        Rollback event processing (for retry scenarios).

        Deletes the processed_events record to allow retry.
        """
        trace_id = event.get("trace_id")
        if not trace_id:
            return

        from sqlalchemy import delete

        stmt = delete(ProcessedEvent).where(
            ProcessedEvent.subscriber_name == subscriber_name,
            ProcessedEvent.trace_id == trace_id,
        )
        await self.db.execute(stmt)
        await self.db.commit()

        logger.warning(
            f"[IdempotencyGuard] Processing rolled back (will retry)",
            subscriber=subscriber_name,
            trace_id=trace_id,
        )
