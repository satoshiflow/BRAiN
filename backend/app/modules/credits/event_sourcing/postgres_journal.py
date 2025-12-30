"""
Postgres Event Journal - Database-Backed Event Storage.

Implements crash-safe event persistence with:
- PostgreSQL backend (ACID guarantees)
- Idempotency via UNIQUE constraint
- Efficient querying with JSONB + indexes
- Async operations with asyncpg

Design Principles:
1. Single Source of Truth: Postgres table is authoritative
2. Append-Only: Events are never modified or deleted
3. Crash-Safe: PostgreSQL ACID guarantees
4. Idempotent: Unique constraint on idempotency_key
5. Queryable: JSONB + GIN indexes for flexible queries

Table Schema (see alembic/versions/002_credit_events_table.py):
- id: Auto-incrementing sequence (ordering)
- event_id: UUID (unique)
- idempotency_key: Duplicate prevention (unique)
- event_type, timestamp, actor_id, correlation_id, causation_id
- payload: JSONB
"""

from __future__ import annotations

import json
import os
from typing import AsyncIterator, Dict, Optional, Set

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.app.modules.credits.event_sourcing.base_journal import BaseEventJournal
from backend.app.modules.credits.event_sourcing.events import EventEnvelope


class PostgresEventJournalError(Exception):
    """Base exception for PostgresEventJournal errors."""
    pass


class PostgresEventJournal(BaseEventJournal):
    """
    Postgres-backed event journal with ACID guarantees.

    Features:
    - PostgreSQL persistence with JSONB
    - Idempotency via UNIQUE constraint
    - Efficient replay via sequence ordering
    - Flexible querying with GIN indexes
    - Async operations (asyncpg/SQLAlchemy)

    Example:
        >>> journal = PostgresEventJournal(database_url="postgresql+asyncpg://...")
        >>> await journal.initialize()
        >>> event = create_credit_allocated_event(...)
        >>> success = await journal.append_event(event)
        >>> async for event in journal.read_events():
        ...     print(event.event_id)
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        pool_size: int = 10,
        max_overflow: int = 20,
    ):
        """
        Initialize PostgresEventJournal.

        Args:
            database_url: PostgreSQL connection string (async)
                         If None, uses DATABASE_URL from env
            pool_size: Connection pool size
            max_overflow: Max overflow connections
        """
        # Get database URL
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "postgresql://brain:brain@localhost/brain")

            # Convert psycopg2 URL to asyncpg if needed
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif not database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("DATABASE_URL must be postgresql+asyncpg:// for async support")

        self.database_url = database_url

        # SQLAlchemy async engine
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None

        # Pool configuration
        self._pool_size = pool_size
        self._max_overflow = max_overflow

        # Idempotency tracking (in-memory cache for performance)
        # Note: DB has UNIQUE constraint as source of truth
        self._seen_idempotency_keys: Set[str] = set()

        # Metrics
        self._total_events = 0
        self._idempotency_violations = 0

    async def initialize(self) -> None:
        """
        Initialize Postgres connection and load idempotency keys.

        Creates async engine and verifies table exists.
        Loads existing idempotency keys into memory cache.

        Raises:
            PostgresEventJournalError: If connection fails
        """
        try:
            # Create async engine
            self._engine = create_async_engine(
                self.database_url,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                echo=False,  # Set to True for SQL logging
            )

            # Create session factory
            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Verify table exists
            async with self._engine.begin() as conn:
                result = await conn.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'credit_events'
                        )
                    """)
                )
                table_exists = result.scalar()

                if not table_exists:
                    logger.warning(
                        "credit_events table does not exist. "
                        "Run: alembic upgrade head"
                    )

            # Load idempotency keys (performance optimization)
            await self._load_idempotency_keys()

            logger.info(
                "PostgresEventJournal initialized",
                database_url=self.database_url.split("@")[-1],  # Hide credentials
                total_events=self._total_events,
            )

        except Exception as e:
            logger.error(f"Failed to initialize PostgresEventJournal: {e}")
            raise PostgresEventJournalError(
                f"Cannot initialize Postgres journal: {e}"
            ) from e

    async def _load_idempotency_keys(self) -> None:
        """
        Load idempotency keys from database into memory cache.

        This prevents duplicate events on restart without hitting DB every time.
        """
        if not self._engine:
            return

        try:
            async with self._engine.begin() as conn:
                result = await conn.execute(
                    text("SELECT idempotency_key FROM credit_events")
                )
                keys = result.fetchall()

                for (key,) in keys:
                    self._seen_idempotency_keys.add(key)
                    self._total_events += 1

            logger.debug(
                "Loaded idempotency keys from Postgres",
                total_keys=len(self._seen_idempotency_keys),
                total_events=self._total_events,
            )

        except Exception as e:
            logger.warning(f"Failed to load idempotency keys: {e}")
            # Non-fatal: UNIQUE constraint is source of truth

    async def append_event(self, event: EventEnvelope) -> bool:
        """
        Append event to Postgres (idempotent, ACID-safe).

        Args:
            event: Event to append

        Returns:
            True if event was appended
            False if duplicate (idempotency)

        Raises:
            PostgresEventJournalError: If database write fails

        Implementation:
        1. Check in-memory cache (fast path)
        2. INSERT with ON CONFLICT DO NOTHING (DB-level idempotency)
        3. Update cache if inserted
        """
        if not self._engine or not self._session_factory:
            raise PostgresEventJournalError("Journal not initialized")

        # === Fast Path: In-Memory Cache ===
        if event.idempotency_key in self._seen_idempotency_keys:
            self._idempotency_violations += 1
            logger.warning(
                "Idempotency violation (cached): duplicate event ignored",
                event_id=event.event_id,
                event_type=event.event_type,
                idempotency_key=event.idempotency_key,
            )
            return False

        # === Insert into Postgres ===
        try:
            async with self._session_factory() as session:
                # Use raw SQL for better control
                result = await session.execute(
                    text("""
                        INSERT INTO credit_events (
                            event_id,
                            idempotency_key,
                            event_type,
                            schema_version,
                            timestamp,
                            actor_id,
                            correlation_id,
                            causation_id,
                            payload
                        ) VALUES (
                            :event_id,
                            :idempotency_key,
                            :event_type,
                            :schema_version,
                            :timestamp,
                            :actor_id,
                            :correlation_id,
                            :causation_id,
                            :payload::jsonb
                        )
                        ON CONFLICT (idempotency_key) DO NOTHING
                        RETURNING id
                    """),
                    {
                        "event_id": event.event_id,
                        "idempotency_key": event.idempotency_key,
                        "event_type": event.event_type.value,
                        "schema_version": event.schema_version,
                        "timestamp": event.timestamp,
                        "actor_id": event.actor_id,
                        "correlation_id": event.correlation_id,
                        "causation_id": event.causation_id,
                        "payload": json.dumps(event.payload),  # JSONB
                    }
                )

                await session.commit()

                # Check if inserted (ON CONFLICT returns no rows if duplicate)
                inserted = result.fetchone()

                if inserted:
                    # Update cache
                    self._seen_idempotency_keys.add(event.idempotency_key)
                    self._total_events += 1

                    logger.debug(
                        "Event appended to Postgres",
                        event_id=event.event_id,
                        event_type=event.event_type,
                        sequence_id=inserted[0],
                    )
                    return True
                else:
                    # Duplicate (caught by UNIQUE constraint)
                    self._idempotency_violations += 1
                    logger.warning(
                        "Idempotency violation (DB): duplicate event ignored",
                        event_id=event.event_id,
                        event_type=event.event_type,
                        idempotency_key=event.idempotency_key,
                    )
                    # Add to cache to speed up future checks
                    self._seen_idempotency_keys.add(event.idempotency_key)
                    return False

        except Exception as e:
            logger.error(
                "Failed to append event to Postgres",
                event_id=event.event_id,
                error=str(e),
            )
            raise PostgresEventJournalError(f"Cannot append event: {e}") from e

    async def read_events(
        self,
        skip_corrupted: bool = True,
    ) -> AsyncIterator[EventEnvelope]:
        """
        Read all events from Postgres (ordered by sequence).

        Args:
            skip_corrupted: If True, skip corrupted events and log warning

        Yields:
            EventEnvelope instances in insertion order

        Raises:
            PostgresEventJournalError: If query fails

        Notes:
        - Uses streaming (server-side cursor) to avoid loading all events into memory
        - Events are yielded in sequence order (id column)
        """
        if not self._engine:
            raise PostgresEventJournalError("Journal not initialized")

        try:
            async with self._engine.begin() as conn:
                # Stream results (server-side cursor)
                result = await conn.stream(
                    text("""
                        SELECT
                            event_id,
                            idempotency_key,
                            event_type,
                            schema_version,
                            timestamp,
                            actor_id,
                            correlation_id,
                            causation_id,
                            payload
                        FROM credit_events
                        ORDER BY id ASC
                    """)
                )

                corrupted_count = 0

                async for row in result:
                    try:
                        # Reconstruct EventEnvelope
                        event = EventEnvelope(
                            event_id=row[0],
                            idempotency_key=row[1],
                            event_type=row[2],
                            schema_version=row[3],
                            timestamp=row[4],
                            actor_id=row[5],
                            correlation_id=row[6],
                            causation_id=row[7],
                            payload=row[8],  # Already deserialized from JSONB
                        )
                        yield event

                    except Exception as e:
                        corrupted_count += 1
                        error_msg = f"Corrupted event data: {e}"

                        if skip_corrupted:
                            logger.warning(
                                error_msg,
                                event_id=row[0] if len(row) > 0 else "unknown",
                            )
                            continue
                        else:
                            raise PostgresEventJournalError(error_msg) from e

                if corrupted_count > 0:
                    logger.warning(
                        f"Skipped {corrupted_count} corrupted events during replay"
                    )

        except Exception as e:
            logger.error(f"Failed to read events from Postgres: {e}")
            raise PostgresEventJournalError(f"Cannot read events: {e}") from e

    def get_metrics(self) -> Dict:
        """
        Get journal metrics for monitoring.

        Returns:
            Dict with:
            - total_events: Total events in journal
            - idempotency_violations: Duplicate attempts
            - cache_size: In-memory cache size
        """
        return {
            "total_events": self._total_events,
            "idempotency_violations": self._idempotency_violations,
            "cache_size": len(self._seen_idempotency_keys),
            "backend": "postgres",
        }

    async def close(self) -> None:
        """Close database connections gracefully."""
        if self._engine:
            await self._engine.dispose()
            logger.info("PostgresEventJournal connections closed")
