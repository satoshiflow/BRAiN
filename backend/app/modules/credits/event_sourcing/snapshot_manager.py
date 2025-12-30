"""
Snapshot Manager for Projection Snapshots.

Implements periodic snapshots of projection states for faster replay:
- Save projection state at event N
- Replay from last snapshot + delta events
- 100× faster replay for large event logs

Design:
- Snapshots stored in Postgres (credit_snapshots table)
- One snapshot per projection type (balance, ledger, approval, synergie)
- Retention policy: Keep last N snapshots
- Automatic snapshot on every M events

Usage:
    snapshot_mgr = SnapshotManager(database_url="...")
    await snapshot_mgr.initialize()

    # Create snapshot
    await snapshot_mgr.create_snapshot(
        projection_manager,
        sequence_number=1000
    )

    # Load latest snapshot
    snapshot = await snapshot_mgr.load_latest_snapshot("balance")

    # Replay from snapshot
    await replay_engine.replay_from_snapshot(snapshot)
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from pydantic import BaseModel


class ProjectionSnapshot(BaseModel):
    """
    Projection snapshot model.

    Contains serialized state of one or more projections
    at a specific event sequence number.
    """
    snapshot_id: str
    snapshot_type: str  # "balance", "ledger", "approval", "synergie", "all"
    sequence_number: int  # Last processed event id
    event_count: int  # Total events processed
    state_data: Dict[str, Any]  # Serialized projection state
    created_at: datetime
    size_bytes: Optional[int] = None


class SnapshotManager:
    """
    Manages projection snapshots for fast replay.

    Features:
    - Create snapshots at sequence number N
    - Load latest snapshot for projection type
    - Automatic cleanup (retention policy)
    - Postgres-backed storage
    """

    def __init__(
        self,
        database_url: Optional[str] = None,
        retention_count: int = 10,
    ):
        """
        Initialize SnapshotManager.

        Args:
            database_url: PostgreSQL connection string (async)
                         If None, uses DATABASE_URL from env
            retention_count: Number of snapshots to keep per type (default: 10)
        """
        # Get database URL
        if database_url is None:
            database_url = os.getenv("DATABASE_URL", "postgresql://brain:brain@localhost/brain")

            # Convert to asyncpg if needed
            if database_url.startswith("postgresql://"):
                database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif not database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("DATABASE_URL must be postgresql+asyncpg:// for async support")

        self.database_url = database_url
        self.retention_count = retention_count

        # SQLAlchemy async engine
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker] = None

    async def initialize(self) -> None:
        """
        Initialize Postgres connection.

        Creates async engine and verifies table exists.
        """
        try:
            # Create async engine
            self._engine = create_async_engine(
                self.database_url,
                pool_size=5,
                max_overflow=10,
                echo=False,
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
                            WHERE table_name = 'credit_snapshots'
                        )
                    """)
                )
                table_exists = result.scalar()

                if not table_exists:
                    logger.warning(
                        "credit_snapshots table does not exist. "
                        "Run: alembic upgrade head"
                    )

            logger.info(
                "SnapshotManager initialized",
                database_url=self.database_url.split("@")[-1],  # Hide credentials
                retention=self.retention_count,
            )

        except Exception as e:
            logger.error(f"Failed to initialize SnapshotManager: {e}")
            raise

    async def create_snapshot(
        self,
        projection_manager,
        sequence_number: int,
        event_count: int = 0,
    ) -> ProjectionSnapshot:
        """
        Create snapshot of all projections at sequence number.

        Args:
            projection_manager: ProjectionManager instance
            sequence_number: Last processed event id (from credit_events.id)
            event_count: Total events processed

        Returns:
            ProjectionSnapshot

        Implementation:
        1. Serialize projection states to JSON
        2. Insert into credit_snapshots table
        3. Cleanup old snapshots (retention policy)
        """
        if not self._engine or not self._session_factory:
            raise RuntimeError("SnapshotManager not initialized")

        snapshot_id = str(uuid4())
        snapshot_type = "all"  # Could be per-projection for granularity

        # Serialize projection states
        state_data = {
            "balance": self._serialize_balance_projection(projection_manager.balance),
            "ledger": self._serialize_ledger_projection(projection_manager.ledger),
            "approval": self._serialize_approval_projection(projection_manager.approval),
            "synergie": self._serialize_synergie_projection(projection_manager.synergie),
        }

        # Calculate size
        state_json = json.dumps(state_data)
        size_bytes = len(state_json.encode('utf-8'))

        # Insert snapshot
        async with self._session_factory() as session:
            await session.execute(
                text("""
                    INSERT INTO credit_snapshots (
                        snapshot_id,
                        snapshot_type,
                        sequence_number,
                        event_count,
                        state_data,
                        size_bytes
                    ) VALUES (
                        :snapshot_id,
                        :snapshot_type,
                        :sequence_number,
                        :event_count,
                        :state_data::jsonb,
                        :size_bytes
                    )
                """),
                {
                    "snapshot_id": snapshot_id,
                    "snapshot_type": snapshot_type,
                    "sequence_number": sequence_number,
                    "event_count": event_count,
                    "state_data": state_json,
                    "size_bytes": size_bytes,
                }
            )
            await session.commit()

        logger.info(
            "Snapshot created",
            snapshot_id=snapshot_id,
            sequence_number=sequence_number,
            event_count=event_count,
            size_kb=size_bytes / 1024,
        )

        # Cleanup old snapshots
        await self._cleanup_old_snapshots(snapshot_type)

        return ProjectionSnapshot(
            snapshot_id=snapshot_id,
            snapshot_type=snapshot_type,
            sequence_number=sequence_number,
            event_count=event_count,
            state_data=state_data,
            created_at=datetime.utcnow(),
            size_bytes=size_bytes,
        )

    async def load_latest_snapshot(
        self,
        snapshot_type: str = "all",
    ) -> Optional[ProjectionSnapshot]:
        """
        Load latest snapshot for projection type.

        Args:
            snapshot_type: Projection type ("balance", "ledger", "all", etc.)

        Returns:
            ProjectionSnapshot or None if no snapshots exist
        """
        if not self._engine:
            raise RuntimeError("SnapshotManager not initialized")

        async with self._engine.begin() as conn:
            result = await conn.execute(
                text("""
                    SELECT
                        snapshot_id,
                        snapshot_type,
                        sequence_number,
                        event_count,
                        state_data,
                        created_at,
                        size_bytes
                    FROM credit_snapshots
                    WHERE snapshot_type = :snapshot_type
                    ORDER BY sequence_number DESC
                    LIMIT 1
                """),
                {"snapshot_type": snapshot_type}
            )

            row = result.fetchone()

            if not row:
                logger.debug(f"No snapshots found for type: {snapshot_type}")
                return None

            snapshot = ProjectionSnapshot(
                snapshot_id=row[0],
                snapshot_type=row[1],
                sequence_number=row[2],
                event_count=row[3],
                state_data=row[4],  # Already deserialized from JSONB
                created_at=row[5],
                size_bytes=row[6],
            )

            logger.info(
                "Snapshot loaded",
                snapshot_id=snapshot.snapshot_id,
                sequence_number=snapshot.sequence_number,
                event_count=snapshot.event_count,
            )

            return snapshot

    async def _cleanup_old_snapshots(self, snapshot_type: str) -> int:
        """
        Delete old snapshots beyond retention count.

        Args:
            snapshot_type: Projection type

        Returns:
            Number of snapshots deleted
        """
        if not self._session_factory:
            return 0

        async with self._session_factory() as session:
            # Delete all but last N snapshots
            result = await session.execute(
                text("""
                    DELETE FROM credit_snapshots
                    WHERE snapshot_type = :snapshot_type
                    AND id NOT IN (
                        SELECT id FROM credit_snapshots
                        WHERE snapshot_type = :snapshot_type
                        ORDER BY sequence_number DESC
                        LIMIT :retention_count
                    )
                """),
                {
                    "snapshot_type": snapshot_type,
                    "retention_count": self.retention_count,
                }
            )
            await session.commit()

            deleted = result.rowcount

            if deleted > 0:
                logger.debug(
                    f"Cleaned up {deleted} old snapshots",
                    snapshot_type=snapshot_type,
                )

            return deleted

    # ========================================================================
    # Projection Serialization
    # ========================================================================

    def _serialize_balance_projection(self, balance_projection) -> Dict:
        """Serialize BalanceProjection state."""
        return {
            "balances": dict(balance_projection._balances),
        }

    def _serialize_ledger_projection(self, ledger_projection) -> Dict:
        """Serialize LedgerProjection state."""
        return {
            "ledger": [
                {
                    "entity_id": entry.entity_id,
                    "event_type": entry.event_type,
                    "amount": entry.amount,
                    "balance_after": entry.balance_after,
                    "reason": entry.reason,
                    "timestamp": entry.timestamp.isoformat(),
                    "actor_id": entry.actor_id,
                }
                for entry in ledger_projection._ledger
            ],
        }

    def _serialize_approval_projection(self, approval_projection) -> Dict:
        """Serialize ApprovalProjection state."""
        return {
            "pending_approvals": dict(approval_projection._pending_approvals),
            "approval_history": list(approval_projection._approval_history),
        }

    def _serialize_synergie_projection(self, synergie_projection) -> Dict:
        """Serialize SynergieProjection state."""
        return {
            "team_rewards": dict(synergie_projection._team_rewards),
            "collaboration_count": dict(synergie_projection._collaboration_count),
        }

    # ========================================================================
    # Projection Deserialization
    # ========================================================================

    def restore_balance_projection(
        self,
        balance_projection,
        state_data: Dict,
    ) -> None:
        """Restore BalanceProjection from snapshot."""
        balance_projection._balances = dict(state_data.get("balances", {}))
        logger.debug(f"Restored {len(balance_projection._balances)} balances")

    def restore_ledger_projection(
        self,
        ledger_projection,
        state_data: Dict,
    ) -> None:
        """Restore LedgerProjection from snapshot."""
        from backend.app.modules.credits.event_sourcing.projections import LedgerEntry
        from datetime import datetime

        ledger_projection._ledger = [
            LedgerEntry(
                entity_id=entry["entity_id"],
                event_type=entry["event_type"],
                amount=entry["amount"],
                balance_after=entry["balance_after"],
                reason=entry["reason"],
                timestamp=datetime.fromisoformat(entry["timestamp"]),
                actor_id=entry["actor_id"],
            )
            for entry in state_data.get("ledger", [])
        ]
        logger.debug(f"Restored {len(ledger_projection._ledger)} ledger entries")

    def restore_approval_projection(
        self,
        approval_projection,
        state_data: Dict,
    ) -> None:
        """Restore ApprovalProjection from snapshot."""
        approval_projection._pending_approvals = dict(state_data.get("pending_approvals", {}))
        approval_projection._approval_history = list(state_data.get("approval_history", []))
        logger.debug(
            f"Restored {len(approval_projection._pending_approvals)} pending approvals"
        )

    def restore_synergie_projection(
        self,
        synergie_projection,
        state_data: Dict,
    ) -> None:
        """Restore SynergieProjection from snapshot."""
        synergie_projection._team_rewards = dict(state_data.get("team_rewards", {}))
        synergie_projection._collaboration_count = dict(state_data.get("collaboration_count", {}))
        logger.debug(
            f"Restored synergie data for {len(synergie_projection._team_rewards)} teams"
        )

    # ========================================================================
    # Phase 6b: Snapshot Enhancements
    # ========================================================================

    def calculate_checksum(self, state_data: Dict[str, Any]) -> str:
        """
        Calculate SHA256 checksum of snapshot data for integrity verification.

        Args:
            state_data: Snapshot state dictionary

        Returns:
            Hex digest of SHA256 checksum

        Example:
            >>> checksum = manager.calculate_checksum(snapshot.state_data)
            >>> # Store checksum with snapshot for verification
        """
        state_json = json.dumps(state_data, sort_keys=True)
        return hashlib.sha256(state_json.encode('utf-8')).hexdigest()

    def verify_checksum(self, state_data: Dict[str, Any], expected_checksum: str) -> bool:
        """
        Verify snapshot integrity via checksum.

        Args:
            state_data: Snapshot state to verify
            expected_checksum: Expected SHA256 checksum

        Returns:
            True if checksum matches, False otherwise
        """
        actual_checksum = self.calculate_checksum(state_data)
        return actual_checksum == expected_checksum

    @staticmethod
    def is_milestone_sequence(sequence_number: int) -> bool:
        """
        Check if sequence number is a milestone (strategic snapshot point).

        Milestones: 1000, 10000, 100000, 1000000, etc.
        Also: Every 5000 events between milestones

        Args:
            sequence_number: Event sequence number

        Returns:
            True if milestone, False otherwise

        Example:
            >>> is_milestone_sequence(1000)   # True
            >>> is_milestone_sequence(10000)  # True
            >>> is_milestone_sequence(5000)   # True (every 5000)
            >>> is_milestone_sequence(1234)   # False
        """
        if sequence_number == 0:
            return False

        # Check if power of 10 * 1000 (1000, 10000, 100000, ...)
        if sequence_number >= 1000:
            temp = sequence_number
            while temp >= 1000 and temp % 10 == 0:
                temp //= 10
            if temp == 1:
                return True

        # Check if multiple of 5000
        if sequence_number % 5000 == 0:
            return True

        return False

    async def apply_milestone_retention(
        self,
        snapshot_type: str = "all",
        keep_recent: int = 10,
    ) -> int:
        """
        Apply milestone-based retention policy.

        Keeps:
        - Last N snapshots (keep_recent)
        - All milestone snapshots (1000, 10000, 100000, ...)

        Deletes all other snapshots.

        Args:
            snapshot_type: Snapshot type to apply policy to
            keep_recent: Number of most recent snapshots to keep

        Returns:
            Number of snapshots deleted

        Example:
            >>> deleted = await manager.apply_milestone_retention("all", keep_recent=10)
            >>> print(f"Deleted {deleted} non-milestone snapshots")
        """
        # Get all snapshots
        snapshots = await self.list_snapshots(snapshot_type=snapshot_type, limit=10000)

        if not snapshots:
            return 0

        # Sort by sequence number descending
        sorted_snapshots = sorted(snapshots, key=lambda s: s.sequence_number, reverse=True)

        # Determine which to keep
        to_keep = set()
        to_delete = []

        # Keep recent N
        for i, snapshot in enumerate(sorted_snapshots):
            if i < keep_recent:
                to_keep.add(snapshot.snapshot_id)

        # Keep milestones
        for snapshot in snapshots:
            if self.is_milestone_sequence(snapshot.sequence_number):
                to_keep.add(snapshot.snapshot_id)

        # Determine deletions
        for snapshot in snapshots:
            if snapshot.snapshot_id not in to_keep:
                to_delete.append(snapshot.snapshot_id)

        # Delete
        deleted_count = 0
        for snapshot_id in to_delete:
            try:
                await self.delete_snapshot(snapshot_id)
                deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete snapshot {snapshot_id}: {e}")

        if deleted_count > 0:
            logger.info(
                f"Milestone retention applied",
                snapshot_type=snapshot_type,
                deleted=deleted_count,
                kept=len(to_keep),
            )

        return deleted_count

    def compress_state_data(self, state_data: Dict[str, Any]) -> bytes:
        """
        Compress snapshot state data using gzip.

        Args:
            state_data: Snapshot state dictionary

        Returns:
            Compressed bytes (gzip)

        Example:
            >>> compressed = manager.compress_state_data(snapshot.state_data)
            >>> # Store compressed data (70-80% size reduction)
        """
        state_json = json.dumps(state_data)
        return gzip.compress(state_json.encode('utf-8'), compresslevel=6)

    def decompress_state_data(self, compressed_data: bytes) -> Dict[str, Any]:
        """
        Decompress snapshot state data.

        Args:
            compressed_data: Gzip-compressed snapshot bytes

        Returns:
            Decompressed state dictionary

        Example:
            >>> state_data = manager.decompress_state_data(compressed_bytes)
        """
        decompressed = gzip.decompress(compressed_data)
        return json.loads(decompressed.decode('utf-8'))

    async def close(self) -> None:
        """Close database connections gracefully."""
        if self._engine:
            await self._engine.dispose()
            logger.info("SnapshotManager connections closed")


# ============================================================================
# Singleton Pattern
# ============================================================================

_snapshot_manager_instance: Optional[SnapshotManager] = None


async def get_snapshot_manager() -> SnapshotManager:
    """
    Get singleton SnapshotManager instance.

    Returns:
        SnapshotManager instance (initialized)
    """
    global _snapshot_manager_instance

    if _snapshot_manager_instance is None:
        _snapshot_manager_instance = SnapshotManager()
        await _snapshot_manager_instance.initialize()

    return _snapshot_manager_instance
