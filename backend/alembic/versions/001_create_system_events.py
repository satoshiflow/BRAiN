"""create system events table

Revision ID: 001
Revises:
Create Date: 2026-01-02 22:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create system_events table"""
    op.create_table(
        'system_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', JSONB(), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('idx_system_events_type', 'system_events', ['event_type'])
    op.create_index('idx_system_events_severity', 'system_events', ['severity'])
    op.create_index('idx_system_events_timestamp', 'system_events', ['timestamp'])


def downgrade() -> None:
    """Drop system_events table"""
    op.drop_index('idx_system_events_timestamp', table_name='system_events')
    op.drop_index('idx_system_events_severity', table_name='system_events')
    op.drop_index('idx_system_events_type', table_name='system_events')
    op.drop_table('system_events')
