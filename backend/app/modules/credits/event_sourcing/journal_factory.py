"""
Event Journal Factory - Backend Selection.

Provides factory function for creating appropriate Event Journal backend:
- file: JSONL file-based (default, zero dependencies)
- postgres: PostgreSQL-backed (ACID, queryable, production)

Configuration via environment variables or explicit parameters.

Usage:
    # Use environment variable EVENT_JOURNAL_BACKEND
    journal = await create_event_journal()

    # Or specify backend explicitly
    journal = await create_event_journal(backend="postgres")
"""

from __future__ import annotations

import os
from typing import Literal, Optional

from loguru import logger

from app.modules.credits.event_sourcing.base_journal import BaseEventJournal


EventJournalBackend = Literal["file", "postgres"]


async def create_event_journal(
    backend: Optional[EventJournalBackend] = None,
    **kwargs,
) -> BaseEventJournal:
    """
    Factory function to create Event Journal with selected backend.

    Args:
        backend: Backend type ("file" or "postgres")
                If None, uses EVENT_JOURNAL_BACKEND env var (default: "file")
        **kwargs: Backend-specific parameters:
                 For file: file_path, enable_fsync
                 For postgres: database_url, pool_size, max_overflow

    Returns:
        Initialized Event Journal instance (BaseEventJournal)

    Raises:
        ValueError: If backend is unknown

    Environment Variables:
        EVENT_JOURNAL_BACKEND: "file" or "postgres" (default: "file")
        DATABASE_URL: PostgreSQL connection string (for postgres backend)

    Examples:
        # File backend (default)
        journal = await create_event_journal()

        # Postgres backend (from env)
        os.environ["EVENT_JOURNAL_BACKEND"] = "postgres"
        journal = await create_event_journal()

        # Explicit backend
        journal = await create_event_journal(backend="postgres")

        # With custom parameters
        journal = await create_event_journal(
            backend="file",
            file_path="custom/path/events.jsonl"
        )
    """
    # Determine backend
    if backend is None:
        backend = os.getenv("EVENT_JOURNAL_BACKEND", "file")  # type: ignore

    backend = backend.lower()  # type: ignore

    # === File Backend ===
    if backend == "file":
        from app.modules.credits.event_sourcing.event_journal import EventJournal

        # Extract file-specific kwargs
        file_path = kwargs.get("file_path", "storage/events/credits.jsonl")
        enable_fsync = kwargs.get("enable_fsync", True)

        journal = EventJournal(
            file_path=file_path,
            enable_fsync=enable_fsync,
        )

        await journal.initialize()

        logger.info(
            "Event Journal created (file backend)",
            file_path=file_path,
            enable_fsync=enable_fsync,
        )

        return journal

    # === Postgres Backend ===
    elif backend == "postgres":
        from app.modules.credits.event_sourcing.postgres_journal import PostgresEventJournal

        # Extract postgres-specific kwargs
        database_url = kwargs.get("database_url", None)
        pool_size = kwargs.get("pool_size", 10)
        max_overflow = kwargs.get("max_overflow", 20)

        journal = PostgresEventJournal(
            database_url=database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

        await journal.initialize()

        logger.info(
            "Event Journal created (postgres backend)",
            pool_size=pool_size,
            max_overflow=max_overflow,
        )

        return journal

    else:
        raise ValueError(
            f"Unknown EVENT_JOURNAL_BACKEND: {backend}. "
            f"Must be 'file' or 'postgres'"
        )


async def migrate_file_to_postgres(
    source_file_path: str = "storage/events/credits.jsonl",
    target_database_url: Optional[str] = None,
    batch_size: int = 1000,
) -> int:
    """
    Migrate events from JSONL file to Postgres.

    Args:
        source_file_path: Path to JSONL file
        target_database_url: Postgres connection string (or use DATABASE_URL env)
        batch_size: Events per batch (for performance)

    Returns:
        Number of events migrated

    Example:
        # Migrate to Postgres (from env DATABASE_URL)
        count = await migrate_file_to_postgres()
        print(f"Migrated {count} events")

        # Custom target
        count = await migrate_file_to_postgres(
            target_database_url="postgresql+asyncpg://..."
        )
    """
    from app.modules.credits.event_sourcing.event_journal import EventJournal
    from app.modules.credits.event_sourcing.postgres_journal import PostgresEventJournal

    logger.info("Starting migration from JSONL to Postgres...")

    # Source: File journal
    file_journal = EventJournal(file_path=source_file_path)
    await file_journal.initialize()

    # Target: Postgres journal
    postgres_journal = PostgresEventJournal(database_url=target_database_url)
    await postgres_journal.initialize()

    # Migrate events
    events_migrated = 0
    batch = []

    async for event in file_journal.read_events():
        batch.append(event)

        # Flush batch
        if len(batch) >= batch_size:
            for event in batch:
                success = await postgres_journal.append_event(event)
                if success:
                    events_migrated += 1
            batch = []

            logger.info(f"Migrated {events_migrated} events...")

    # Flush remaining
    for event in batch:
        success = await postgres_journal.append_event(event)
        if success:
            events_migrated += 1

    logger.info(
        f"Migration complete: {events_migrated} events migrated",
        source=source_file_path,
        target="postgres",
    )

    # Close connections
    await postgres_journal.close()

    return events_migrated
