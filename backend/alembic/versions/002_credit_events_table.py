"""Add credit_events table for Postgres Event Store

Revision ID: 002_credit_events
Revises: 001_initial_schema
Create Date: 2024-12-30

Migration for Phase 5a: Postgres Event Store
- Creates credit_events table for Event Sourcing
- Optimized for append-only operations
- Idempotency via unique constraint on idempotency_key
- Indexes for efficient replay and querying
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_credit_events'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create credit_events table for Event Sourcing.

    Design:
    - Append-only (no UPDATE/DELETE)
    - event_id: Primary key (UUID)
    - idempotency_key: Unique constraint (duplicate prevention)
    - sequence: Auto-incrementing for ordering
    - event_type: Indexed for filtering
    - timestamp: Indexed for time-range queries
    - payload: JSONB for flexible querying
    """
    op.create_table(
        'credit_events',

        # Primary Key
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True,
                  comment='Auto-incrementing sequence (ordering)'),

        # Event Identity
        sa.Column('event_id', sa.String(36), nullable=False, unique=True,
                  comment='UUID v4 - Unique event identifier'),

        sa.Column('idempotency_key', sa.String(255), nullable=False, unique=True,
                  comment='Unique key for duplicate prevention'),

        # Event Metadata
        sa.Column('event_type', sa.String(50), nullable=False,
                  comment='Event type (CREDIT_ALLOCATED, CREDIT_CONSUMED, etc.)'),

        sa.Column('schema_version', sa.Integer(), nullable=False, default=1,
                  comment='Event schema version for evolution'),

        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False,
                  comment='Event timestamp (UTC)'),

        # Causality
        sa.Column('actor_id', sa.String(100), nullable=False,
                  comment='Who/what caused this event'),

        sa.Column('correlation_id', sa.String(36), nullable=False,
                  comment='Groups related events (UUID)'),

        sa.Column('causation_id', sa.String(36), nullable=True,
                  comment='Parent event ID (event chain tracking)'),

        # Event Payload
        sa.Column('payload', postgresql.JSONB(), nullable=False,
                  comment='Event data (JSONB for querying)'),

        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  comment='Database insertion time'),

        # Table metadata
        comment='Event Store for Credit System (append-only)'
    )

    # === Indexes ===

    # Primary ordering (replay by sequence)
    op.create_index(
        'idx_credit_events_sequence',
        'credit_events',
        ['id'],
        postgresql_using='btree'
    )

    # Event type filtering (e.g., get all CREDIT_CONSUMED)
    op.create_index(
        'idx_credit_events_type',
        'credit_events',
        ['event_type'],
        postgresql_using='btree'
    )

    # Time-range queries
    op.create_index(
        'idx_credit_events_timestamp',
        'credit_events',
        ['timestamp'],
        postgresql_using='btree'
    )

    # Correlation tracking (all events in transaction)
    op.create_index(
        'idx_credit_events_correlation',
        'credit_events',
        ['correlation_id'],
        postgresql_using='btree'
    )

    # Entity queries (e.g., all events for agent_id)
    # JSONB GIN index for efficient payload queries
    op.create_index(
        'idx_credit_events_payload_gin',
        'credit_events',
        ['payload'],
        postgresql_using='gin'
    )

    # Composite index for entity + time queries
    op.execute("""
        CREATE INDEX idx_credit_events_entity_time
        ON credit_events (
            (payload->>'entity_id'),
            timestamp DESC
        )
    """)


def downgrade():
    """
    Drop credit_events table and all indexes.

    WARNING: This will delete all event history!
    """
    op.drop_index('idx_credit_events_entity_time', table_name='credit_events')
    op.drop_index('idx_credit_events_payload_gin', table_name='credit_events')
    op.drop_index('idx_credit_events_correlation', table_name='credit_events')
    op.drop_index('idx_credit_events_timestamp', table_name='credit_events')
    op.drop_index('idx_credit_events_type', table_name='credit_events')
    op.drop_index('idx_credit_events_sequence', table_name='credit_events')
    op.drop_table('credit_events')
