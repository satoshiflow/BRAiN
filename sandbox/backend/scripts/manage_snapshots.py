#!/usr/bin/env python3
"""
Snapshot Management CLI - Manual Snapshot Operations.

Provides command-line interface for managing projection snapshots:
- Create snapshots on demand
- List existing snapshots
- Delete old snapshots
- Show snapshot statistics
- Verify snapshot integrity

Usage:
    # Create snapshot of all projections
    python manage_snapshots.py create

    # Create snapshot with custom type
    python manage_snapshots.py create --type balance

    # List all snapshots
    python manage_snapshots.py list

    # Show snapshot statistics
    python manage_snapshots.py stats

    # Delete snapshots older than N days
    python manage_snapshots.py cleanup --days 30

    # Dry run (preview without executing)
    python manage_snapshots.py create --dry-run

Environment Variables:
    DATABASE_URL: Target Postgres database for snapshots
    EVENT_JOURNAL_BACKEND: "file" or "postgres"

Examples:
    export DATABASE_URL="postgresql+asyncpg://brain:password@localhost/brain"
    python manage_snapshots.py create
    # Created snapshot snapshot_20231220_143022 (1,234 events, 1.2 MB)

    python manage_snapshots.py list
    # Snapshot ID                  | Type | Sequence | Events | Size    | Created
    # snapshot_20231220_143022     | all  | 1234     | 1234   | 1.2 MB  | 2023-12-20 14:30:22
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

from app.modules.credits.event_sourcing.journal_factory import create_event_journal
from app.modules.credits.event_sourcing.projections import get_projection_manager
from app.modules.credits.event_sourcing.snapshot_manager import (
    get_snapshot_manager,
    ProjectionSnapshot,
)
from app.modules.credits.event_sourcing.replay import get_replay_engine


async def create_snapshot_command(args):
    """Create a new snapshot of projections."""
    logger.info("=" * 80)
    logger.info("Creating Projection Snapshot")
    logger.info("=" * 80)
    logger.info(f"Snapshot type: {args.type}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 80)

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")

    try:
        # Initialize components
        journal = await create_event_journal()
        projection_manager = get_projection_manager()
        snapshot_manager = await get_snapshot_manager()

        # First, replay events to ensure projections are up-to-date
        logger.info("Replaying events to ensure projections are current...")
        replay_engine = await get_replay_engine(
            journal=journal,
            projection_manager=projection_manager,
            snapshot_manager=snapshot_manager,
        )
        replay_metrics = await replay_engine.replay_all()

        logger.info(
            f"Replay completed: {replay_metrics['total_events']} events processed "
            f"in {replay_metrics['replay_duration_seconds']:.2f}s"
        )

        # Get current sequence number (total events in journal)
        event_count = 0
        async for _ in journal.read_events():
            event_count += 1

        if args.dry_run:
            logger.info(f"[DRY RUN] Would create snapshot at sequence {event_count}")
            logger.info(f"[DRY RUN] Projection states would be serialized")
            logger.info(f"[DRY RUN] Snapshot type: {args.type}")
            return

        # Create snapshot
        logger.info(f"Creating snapshot at sequence {event_count}...")
        snapshot = await snapshot_manager.create_snapshot(
            projection_manager=projection_manager,
            sequence_number=event_count,
            event_count=event_count,
        )

        logger.info("=" * 80)
        logger.info("✅ Snapshot Created Successfully")
        logger.info("=" * 80)
        logger.info(f"Snapshot ID: {snapshot.snapshot_id}")
        logger.info(f"Snapshot Type: {snapshot.snapshot_type}")
        logger.info(f"Sequence Number: {snapshot.sequence_number}")
        logger.info(f"Event Count: {snapshot.event_count}")
        logger.info(f"Size: {snapshot.size_bytes / 1024 / 1024:.2f} MB")
        logger.info(f"Created At: {snapshot.created_at}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Failed to create snapshot: {e}")
        sys.exit(1)


async def list_snapshots_command(args):
    """List all existing snapshots."""
    try:
        snapshot_manager = await get_snapshot_manager()

        # Get all snapshots
        snapshots = await snapshot_manager.list_snapshots(
            snapshot_type=args.type if args.type != "all" else None,
            limit=args.limit,
        )

        if not snapshots:
            logger.info("No snapshots found")
            return

        logger.info("=" * 120)
        logger.info(
            f"{'Snapshot ID':<30} | {'Type':<8} | {'Sequence':<10} | {'Events':<8} | {'Size':<10} | {'Created':<20}"
        )
        logger.info("=" * 120)

        for snapshot in snapshots:
            size_mb = snapshot.size_bytes / 1024 / 1024 if snapshot.size_bytes else 0
            created_str = snapshot.created_at.strftime("%Y-%m-%d %H:%M:%S")

            logger.info(
                f"{snapshot.snapshot_id:<30} | "
                f"{snapshot.snapshot_type:<8} | "
                f"{snapshot.sequence_number:<10} | "
                f"{snapshot.event_count:<8} | "
                f"{size_mb:<10.2f} | "
                f"{created_str:<20}"
            )

        logger.info("=" * 120)
        logger.info(f"Total snapshots: {len(snapshots)}")

    except Exception as e:
        logger.error(f"❌ Failed to list snapshots: {e}")
        sys.exit(1)


async def stats_command(args):
    """Show snapshot statistics."""
    try:
        snapshot_manager = await get_snapshot_manager()

        # Get all snapshots
        snapshots = await snapshot_manager.list_snapshots()

        if not snapshots:
            logger.info("No snapshots found")
            return

        # Calculate statistics
        total_snapshots = len(snapshots)
        total_size_bytes = sum(s.size_bytes or 0 for s in snapshots)
        total_size_mb = total_size_bytes / 1024 / 1024

        # Latest snapshot
        latest_snapshot = max(snapshots, key=lambda s: s.created_at)

        # Average size
        avg_size_mb = total_size_mb / total_snapshots if total_snapshots > 0 else 0

        # Snapshots by type
        by_type = {}
        for snapshot in snapshots:
            by_type[snapshot.snapshot_type] = by_type.get(snapshot.snapshot_type, 0) + 1

        logger.info("=" * 80)
        logger.info("Snapshot Statistics")
        logger.info("=" * 80)
        logger.info(f"Total Snapshots: {total_snapshots}")
        logger.info(f"Total Size: {total_size_mb:.2f} MB")
        logger.info(f"Average Size: {avg_size_mb:.2f} MB")
        logger.info("")
        logger.info("Snapshots by Type:")
        for snapshot_type, count in by_type.items():
            logger.info(f"  - {snapshot_type}: {count}")
        logger.info("")
        logger.info(f"Latest Snapshot:")
        logger.info(f"  - ID: {latest_snapshot.snapshot_id}")
        logger.info(f"  - Type: {latest_snapshot.snapshot_type}")
        logger.info(f"  - Sequence: {latest_snapshot.sequence_number}")
        logger.info(f"  - Events: {latest_snapshot.event_count}")
        logger.info(f"  - Created: {latest_snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Failed to get statistics: {e}")
        sys.exit(1)


async def cleanup_command(args):
    """Delete old snapshots based on retention policy."""
    logger.info("=" * 80)
    logger.info("Cleaning Up Old Snapshots")
    logger.info("=" * 80)
    logger.info(f"Retention days: {args.days}")
    logger.info(f"Keep minimum: {args.keep}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info("=" * 80)

    try:
        snapshot_manager = await get_snapshot_manager()

        # Get all snapshots
        snapshots = await snapshot_manager.list_snapshots()

        if not snapshots:
            logger.info("No snapshots found")
            return

        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=args.days)

        # Find snapshots to delete
        snapshots_to_delete = []
        snapshots_to_keep = []

        # Sort by created_at descending
        sorted_snapshots = sorted(snapshots, key=lambda s: s.created_at, reverse=True)

        for i, snapshot in enumerate(sorted_snapshots):
            if i < args.keep:
                # Keep minimum number of snapshots
                snapshots_to_keep.append(snapshot)
            elif snapshot.created_at < cutoff_date:
                # Delete if older than cutoff
                snapshots_to_delete.append(snapshot)
            else:
                # Keep if within retention period
                snapshots_to_keep.append(snapshot)

        if not snapshots_to_delete:
            logger.info("No snapshots to delete (all within retention policy)")
            return

        logger.info(f"Found {len(snapshots_to_delete)} snapshots to delete:")
        for snapshot in snapshots_to_delete:
            age_days = (datetime.utcnow() - snapshot.created_at).days
            logger.info(
                f"  - {snapshot.snapshot_id} "
                f"(age: {age_days} days, "
                f"created: {snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S')})"
            )

        if args.dry_run:
            logger.info("")
            logger.info("[DRY RUN] Would delete these snapshots")
            logger.info(f"[DRY RUN] Would keep {len(snapshots_to_keep)} snapshots")
            return

        # Delete snapshots
        deleted_count = 0
        for snapshot in snapshots_to_delete:
            try:
                await snapshot_manager.delete_snapshot(snapshot.snapshot_id)
                deleted_count += 1
                logger.info(f"Deleted: {snapshot.snapshot_id}")
            except Exception as e:
                logger.error(f"Failed to delete {snapshot.snapshot_id}: {e}")

        logger.info("=" * 80)
        logger.info(f"✅ Cleanup Complete")
        logger.info(f"Deleted: {deleted_count} snapshots")
        logger.info(f"Kept: {len(snapshots_to_keep)} snapshots")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Cleanup failed: {e}")
        sys.exit(1)


async def verify_command(args):
    """Verify snapshot integrity by restoring and comparing."""
    logger.info("=" * 80)
    logger.info("Verifying Snapshot Integrity")
    logger.info("=" * 80)

    try:
        snapshot_manager = await get_snapshot_manager()
        journal = await create_event_journal()
        projection_manager = get_projection_manager()

        # Load snapshot
        if args.snapshot_id:
            snapshot = await snapshot_manager.load_snapshot(args.snapshot_id)
        else:
            snapshot = await snapshot_manager.load_latest_snapshot("all")

        if not snapshot:
            logger.error("No snapshot found")
            sys.exit(1)

        logger.info(f"Verifying snapshot: {snapshot.snapshot_id}")
        logger.info(f"Sequence number: {snapshot.sequence_number}")

        # Restore projections from snapshot
        snapshot_manager.restore_balance_projection(
            projection_manager.balance,
            snapshot.state_data["balance"]
        )
        snapshot_manager.restore_ledger_projection(
            projection_manager.ledger,
            snapshot.state_data["ledger"]
        )
        snapshot_manager.restore_approval_projection(
            projection_manager.approval,
            snapshot.state_data["approval"]
        )
        snapshot_manager.restore_synergie_projection(
            projection_manager.synergie,
            snapshot.state_data["synergie"]
        )

        logger.info("Restored projections from snapshot")

        # Replay delta events
        event_count = 0
        events_processed = 0

        async for event in journal.read_events():
            event_count += 1

            if event_count <= snapshot.sequence_number:
                continue  # Skip events before snapshot

            await projection_manager.balance.handle_event(event)
            await projection_manager.ledger.handle_event(event)
            await projection_manager.approval.handle_event(event)
            await projection_manager.synergie.handle_event(event)

            events_processed += 1

        logger.info(f"Replayed {events_processed} delta events")

        # Verify balances
        balances = projection_manager.balance.get_all_balances()
        ledger_entries = projection_manager.ledger.get_all_entries()

        logger.info(f"Total entities with balances: {len(balances)}")
        logger.info(f"Total ledger entries: {len(ledger_entries)}")

        # Check balance invariants
        errors = []
        for entity_id, balance in balances.items():
            entries = projection_manager.ledger.get_history(entity_id)
            computed_balance = sum(entry.amount for entry in entries)

            if abs(balance - computed_balance) > 0.01:
                errors.append(
                    f"Entity {entity_id}: balance={balance}, ledger_sum={computed_balance}"
                )

        if errors:
            logger.error("=" * 80)
            logger.error("❌ Snapshot Verification Failed")
            logger.error(f"Found {len(errors)} integrity errors:")
            for error in errors[:10]:  # Show first 10
                logger.error(f"  - {error}")
            logger.error("=" * 80)
            sys.exit(1)
        else:
            logger.info("=" * 80)
            logger.info("✅ Snapshot Verified Successfully")
            logger.info("All balance invariants passed")
            logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        sys.exit(1)


async def main():
    """CLI entry point for snapshot management."""
    parser = argparse.ArgumentParser(
        description="Snapshot Management CLI for Credit System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new snapshot")
    create_parser.add_argument(
        "--type",
        type=str,
        default="all",
        choices=["all", "balance", "ledger", "approval", "synergie"],
        help="Snapshot type (default: all)",
    )
    create_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without creating snapshot",
    )

    # List command
    list_parser = subparsers.add_parser("list", help="List all snapshots")
    list_parser.add_argument(
        "--type",
        type=str,
        default="all",
        help="Filter by snapshot type",
    )
    list_parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum snapshots to list (default: 100)",
    )

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show snapshot statistics")

    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Delete old snapshots")
    cleanup_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Delete snapshots older than N days (default: 30)",
    )
    cleanup_parser.add_argument(
        "--keep",
        type=int,
        default=10,
        help="Always keep N most recent snapshots (default: 10)",
    )
    cleanup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without deleting",
    )

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify snapshot integrity")
    verify_parser.add_argument(
        "--snapshot-id",
        type=str,
        default=None,
        help="Snapshot ID to verify (default: latest)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Validate database URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL not set. Snapshots require Postgres backend.")
        logger.error("Set via environment: export DATABASE_URL='postgresql+asyncpg://...'")
        sys.exit(1)

    # Execute command
    try:
        if args.command == "create":
            await create_snapshot_command(args)
        elif args.command == "list":
            await list_snapshots_command(args)
        elif args.command == "stats":
            await stats_command(args)
        elif args.command == "cleanup":
            await cleanup_command(args)
        elif args.command == "verify":
            await verify_command(args)
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)


if __name__ == "__main__":
    asyncio.run(main())
