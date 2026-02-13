"""Add credit_snapshots table for faster replay

Revision ID: 003_credit_snapshots
Revises: 002_credit_events
Create Date: 2024-12-30

Migration for Phase 6a: Event Snapshots
- Creates credit_snapshots table for projection snapshots
- Optimized for fast replay (load snapshot + replay delta)
- Supports multiple snapshot types (balance, ledger, approval, synergie)
- Retention policy: Keep last N snapshots per type
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003_credit_snapshots'
down_revision = '002_credit_events'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create credit_snapshots table for Projection Snapshots.

    Design:
    - One row per snapshot per projection type
    - snapshot_type: "balance", "ledger", "approval", "synergie", "all"
    - sequence_number: Last processed event_id (from credit_events.id)
    - state_data: JSONB (serialized projection state)
    - Retention: DELETE old snapshots when creating new ones

    Replay Strategy:
    1. Load latest snapshot for projection type
    2. Replay events with id > snapshot.sequence_number
    3. 100× faster for large event logs (1M events → 1K events)
    """
    op.create_table(
        'credit_snapshots',

        # Primary Key
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True,
                  comment='Auto-incrementing sequence'),

        # Snapshot Identity
        sa.Column('snapshot_id', sa.String(36), nullable=False, unique=True,
                  comment='UUID v4 - Unique snapshot identifier'),

        # Snapshot Type (which projection)
        sa.Column('snapshot_type', sa.String(50), nullable=False,
                  comment='Projection type: balance, ledger, approval, synergie, all'),

        # Event Sequence Tracking
        sa.Column('sequence_number', sa.BigInteger(), nullable=False,
                  comment='Last processed event id (from credit_events.id)'),

        sa.Column('event_count', sa.Integer(), nullable=False, default=0,
                  comment='Total events processed at snapshot time'),

        # Snapshot State
        sa.Column('state_data', postgresql.JSONB(), nullable=False,
                  comment='Serialized projection state (JSONB)'),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  comment='Snapshot creation time'),

        sa.Column('size_bytes', sa.Integer(), nullable=True,
                  comment='Snapshot size in bytes (for monitoring)'),

        # Table metadata
        comment='Projection Snapshots for fast replay (Phase 6a)'
    )

    # === Indexes ===

    # Latest snapshot per type (for replay)
    op.create_index(
        'idx_credit_snapshots_type_sequence',
        'credit_snapshots',
        ['snapshot_type', 'sequence_number'],
        postgresql_using='btree'
    )

    # Cleanup old snapshots (retention policy)
    op.create_index(
        'idx_credit_snapshots_created',
        'credit_snapshots',
        ['snapshot_type', 'created_at'],
        postgresql_using='btree'
    )

    # Sequence number lookup (for delta replay)
    op.create_index(
        'idx_credit_snapshots_sequence',
        'credit_snapshots',
        ['sequence_number'],
        postgresql_using='btree'
    )


def downgrade():
    """
    Drop credit_snapshots table and all indexes.

    WARNING: This will delete all snapshots! Replay will be slower.
    """
    op.drop_index('idx_credit_snapshots_sequence', table_name='credit_snapshots')
    op.drop_index('idx_credit_snapshots_created', table_name='credit_snapshots')
    op.drop_index('idx_credit_snapshots_type_sequence', table_name='credit_snapshots')
    op.drop_table('credit_snapshots')
