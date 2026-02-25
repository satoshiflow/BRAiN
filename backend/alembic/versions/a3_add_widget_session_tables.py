"""Add AXE_WIDGET Phase 1 persistence tables for web widget sessions and credentials

Revision ID: a3_add_widget_session_tables
Revises: a2_add_autonomous_pipeline_tables
Create Date: 2026-02-25 12:00:00.000000

Tables:
- widget_sessions: Web chat sessions for the embedded AXE widget
- widget_messages: Message history within sessions
- widget_credentials: API credentials for website projects
- widget_analytics: Event tracking and metrics (optional extensibility)
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a3_add_widget_session_tables'
down_revision: Union[str, None] = 'a2_add_autonomous_pipeline_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create widget_sessions table
    op.create_table(
        'widget_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('owner_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(50), nullable=False, server_default='active'),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id'),
        sa.CheckConstraint(
            "status IN ('active', 'expired', 'revoked')",
            name='ck_widget_sessions_status'
        ),
    )
    op.create_index(op.f('ix_widget_sessions_session_id'), 'widget_sessions', ['session_id'], unique=True)
    op.create_index(op.f('ix_widget_sessions_project_id'), 'widget_sessions', ['project_id'])
    op.create_index(op.f('ix_widget_sessions_expires_at'), 'widget_sessions', ['expires_at'])
    op.create_index(op.f('ix_widget_sessions_created_at'), 'widget_sessions', ['created_at'])
    op.create_index(op.f('ix_widget_sessions_status'), 'widget_sessions', ['status'])

    # Create widget_messages table
    op.create_table(
        'widget_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['widget_sessions.id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "role IN ('user', 'assistant')",
            name='ck_widget_messages_role'
        ),
    )
    op.create_index(op.f('ix_widget_messages_session_id'), 'widget_messages', ['session_id'])
    op.create_index(op.f('ix_widget_messages_created_at'), 'widget_messages', ['created_at'])

    # Create widget_credentials table
    op.create_table(
        'widget_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('project_id', sa.String(255), nullable=False),
        sa.Column('api_key_hash', sa.String(255), nullable=False),
        sa.Column('secret_hash', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('rate_limit', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(255), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id'),
        sa.UniqueConstraint('api_key_hash'),
    )
    op.create_index(op.f('ix_widget_credentials_project_id'), 'widget_credentials', ['project_id'], unique=True)
    op.create_index(op.f('ix_widget_credentials_api_key_hash'), 'widget_credentials', ['api_key_hash'], unique=True)
    op.create_index(op.f('ix_widget_credentials_is_active'), 'widget_credentials', ['is_active'])

    # Create widget_analytics table
    op.create_table(
        'widget_analytics',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_value', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['widget_sessions.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_widget_analytics_session_id'), 'widget_analytics', ['session_id'])
    op.create_index(op.f('ix_widget_analytics_event_type'), 'widget_analytics', ['event_type'])
    op.create_index(op.f('ix_widget_analytics_created_at'), 'widget_analytics', ['created_at'])


def downgrade() -> None:
    # Drop widget_analytics table
    op.drop_index(op.f('ix_widget_analytics_created_at'), table_name='widget_analytics')
    op.drop_index(op.f('ix_widget_analytics_event_type'), table_name='widget_analytics')
    op.drop_index(op.f('ix_widget_analytics_session_id'), table_name='widget_analytics')
    op.drop_table('widget_analytics')

    # Drop widget_credentials table
    op.drop_index(op.f('ix_widget_credentials_is_active'), table_name='widget_credentials')
    op.drop_index(op.f('ix_widget_credentials_api_key_hash'), table_name='widget_credentials')
    op.drop_index(op.f('ix_widget_credentials_project_id'), table_name='widget_credentials')
    op.drop_table('widget_credentials')

    # Drop widget_messages table
    op.drop_index(op.f('ix_widget_messages_created_at'), table_name='widget_messages')
    op.drop_index(op.f('ix_widget_messages_session_id'), table_name='widget_messages')
    op.drop_table('widget_messages')

    # Drop widget_sessions table
    op.drop_index(op.f('ix_widget_sessions_status'), table_name='widget_sessions')
    op.drop_index(op.f('ix_widget_sessions_created_at'), table_name='widget_sessions')
    op.drop_index(op.f('ix_widget_sessions_expires_at'), table_name='widget_sessions')
    op.drop_index(op.f('ix_widget_sessions_project_id'), table_name='widget_sessions')
    op.drop_index(op.f('ix_widget_sessions_session_id'), table_name='widget_sessions')
    op.drop_table('widget_sessions')
