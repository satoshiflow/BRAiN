"""Event Dedup via Stream Message ID (Charter v1.0)

Revision ID: 002
Revises: 001
Create Date: 2025-12-28

Charter Compliance:
- Primary dedup key: (subscriber_name, stream_message_id)
- event.id stored as secondary (audit/trace)
- TTL handled at application level (30+ days retention)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    """Create processed_events table for idempotent event processing"""
    op.create_table(
        'processed_events',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('subscriber_name', sa.String(255), nullable=False,
                  comment='Name of the event subscriber/consumer'),
        sa.Column('stream_name', sa.String(255), nullable=False,
                  comment='Redis stream name (e.g. brain:events:stream)'),
        sa.Column('stream_message_id', sa.String(50), nullable=False,
                  comment='Redis Stream Message ID (PRIMARY dedup key per Charter)'),
        sa.Column('event_id', sa.String(50), nullable=True,
                  comment='Event UUID (SECONDARY, audit/trace only)'),
        sa.Column('event_type', sa.String(100), nullable=True,
                  comment='Event type for debugging'),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now(),
                  comment='Timestamp when event was processed'),
        sa.Column('tenant_id', sa.String(100), nullable=True,
                  comment='Tenant ID for multi-tenancy isolation'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True,
                  comment='Additional metadata (payload hash, etc.)'),

        # Constraints
        sa.UniqueConstraint('subscriber_name', 'stream_message_id',
                            name='uq_subscriber_stream_msg_id'),
        sa.Index('idx_processed_events_subscriber', 'subscriber_name'),
        sa.Index('idx_processed_events_event_id', 'event_id'),
        sa.Index('idx_processed_events_processed_at', 'processed_at'),
        sa.Index('idx_processed_events_tenant', 'tenant_id'),

        comment='Idempotency tracking table (Charter v1.0 compliant)'
    )

    # Create cleanup index for TTL enforcement (app-level)
    op.create_index(
        'idx_processed_events_cleanup',
        'processed_events',
        ['processed_at'],
        postgresql_where=sa.text("processed_at < NOW() - INTERVAL '90 days'")
    )


def downgrade():
    """Drop processed_events table"""
    op.drop_index('idx_processed_events_cleanup', table_name='processed_events')
    op.drop_table('processed_events')
