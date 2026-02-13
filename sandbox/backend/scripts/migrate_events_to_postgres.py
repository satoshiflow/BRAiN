#!/usr/bin/env python3
"""
Migrate Event Journal from JSONL to Postgres.

Usage:
    python migrate_events_to_postgres.py

    # With custom source file
    python migrate_events_to_postgres.py --source storage/events/backup.jsonl

    # Dry run (count events without migrating)
    python migrate_events_to_postgres.py --dry-run

Environment Variables:
    DATABASE_URL: Target Postgres database
    EVENT_JOURNAL_BACKEND: Set to "postgres" after migration

Example:
    export DATABASE_URL="postgresql+asyncpg://brain:password@localhost/brain"
    python migrate_events_to_postgres.py
    # Migrated 1,234 events from JSONL to Postgres
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.modules.credits.event_sourcing.journal_factory import migrate_file_to_postgres


async def main():
    """CLI entry point for migration."""
    parser = argparse.ArgumentParser(
        description="Migrate Credit System events from JSONL to Postgres"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="storage/events/credits.jsonl",
        help="Source JSONL file path (default: storage/events/credits.jsonl)",
    )
    parser.add_argument(
        "--database-url",
        type=str,
        default=None,
        help="Target Postgres URL (default: DATABASE_URL env var)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Events per batch (default: 1000)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count events without migrating",
    )

    args = parser.parse_args()

    # Validate source file
    source_path = Path(args.source)
    if not source_path.exists():
        logger.error(f"Source file not found: {args.source}")
        sys.exit(1)

    # Validate database URL
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set. Provide via --database-url or env var")
        sys.exit(1)

    # Dry run: Count events
    if args.dry_run:
        logger.info(f"Dry run: Counting events in {args.source}...")

        from app.modules.credits.event_sourcing.event_journal import EventJournal

        journal = EventJournal(file_path=args.source)
        await journal.initialize()

        count = 0
        async for _ in journal.read_events():
            count += 1

        logger.info(f"Found {count:,} events in {args.source}")
        logger.info("Dry run complete (no migration performed)")
        sys.exit(0)

    # Actual migration
    logger.info("=" * 80)
    logger.info("Event Journal Migration: JSONL → Postgres")
    logger.info("=" * 80)
    logger.info(f"Source: {args.source}")
    logger.info(f"Target: {database_url.split('@')[-1]}")  # Hide credentials
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("=" * 80)

    try:
        events_migrated = await migrate_file_to_postgres(
            source_file_path=args.source,
            target_database_url=database_url,
            batch_size=args.batch_size,
        )

        logger.info("=" * 80)
        logger.info(f"✅ Migration complete: {events_migrated:,} events migrated")
        logger.info("=" * 80)

        # Remind user to switch backend
        logger.info("")
        logger.info("⚠️  Next steps:")
        logger.info("1. Verify data in Postgres:")
        logger.info("   SELECT COUNT(*) FROM credit_events;")
        logger.info("")
        logger.info("2. Switch to Postgres backend:")
        logger.info("   export EVENT_JOURNAL_BACKEND=postgres")
        logger.info("")
        logger.info("3. Restart application")
        logger.info("")
        logger.info("4. Optional: Backup JSONL file:")
        logger.info(f"   mv {args.source} {args.source}.backup")
        logger.info("")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
