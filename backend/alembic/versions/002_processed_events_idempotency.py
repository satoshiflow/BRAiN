"""Add processed_events table for idempotency

Revision ID: 002
Revises: 001
Create Date: 2025-12-28

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
    """Create processed_events table for event idempotency."""
    op.create_table(
        'processed_events',
        sa.Column('subscriber_name', sa.String(100), nullable=False),
        sa.Column('trace_id', sa.String(100), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=True),
        sa.Column('processed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('subscriber_name', 'trace_id', name='pk_processed_events')
    )

    # Indexes for efficient querying
    op.create_index('idx_processed_events_tenant', 'processed_events', ['tenant_id'])
    op.create_index('idx_processed_events_type', 'processed_events', ['event_type'])
    op.create_index('idx_processed_events_processed_at', 'processed_events', ['processed_at'])


def downgrade():
    """Drop processed_events table."""
    op.drop_index('idx_processed_events_processed_at', 'processed_events')
    op.drop_index('idx_processed_events_type', 'processed_events')
    op.drop_index('idx_processed_events_tenant', 'processed_events')
    op.drop_table('processed_events')
