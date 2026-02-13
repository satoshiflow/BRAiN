"""Memory persistence - PostgreSQL tables for memory module

Revision ID: 010_memory_persistence
Revises: 009_skills_system
Create Date: 2025-02-12 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '010_memory_persistence'
down_revision: Union[str, None] = '009_skills_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create memory persistence tables for BRAIN's memory module.
    
    Tables:
        - memory_entries: Stores all memory entries (working, episodic, semantic)
        - session_contexts: Stores active session contexts
        - conversation_turns: Stores conversation turns within sessions
    """
    
    # Create memory_entries table
    op.create_table(
        'memory_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('memory_id', sa.String(32), unique=True, nullable=False),
        sa.Column('layer', sa.String(20), nullable=False),
        sa.Column('memory_type', sa.String(30), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('agent_id', sa.String(100), nullable=True),
        sa.Column('session_id', sa.String(32), nullable=True),
        sa.Column('mission_id', sa.String(100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String(50)), nullable=False, server_default='{}'),
        sa.Column('importance', sa.Float(), nullable=False, server_default='50.0'),
        sa.Column('karma_score', sa.Float(), nullable=False, server_default='50.0'),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed_at', sa.DateTime(timezone=False), nullable=True),
        sa.Column('compression', sa.String(20), nullable=False, server_default='raw'),
        sa.Column('created_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=False), nullable=True),
        sa.Column('embedding', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
    )
    
    # Create indexes for memory_entries
    op.create_index('idx_memory_entries_memory_id', 'memory_entries', ['memory_id'])
    op.create_index('idx_memory_entries_layer', 'memory_entries', ['layer'])
    op.create_index('idx_memory_entries_memory_type', 'memory_entries', ['memory_type'])
    op.create_index('idx_memory_entries_agent_id', 'memory_entries', ['agent_id'])
    op.create_index('idx_memory_entries_session_id', 'memory_entries', ['session_id'])
    op.create_index('idx_memory_entries_mission_id', 'memory_entries', ['mission_id'])
    op.create_index('idx_memory_entries_created_at', 'memory_entries', ['created_at'])
    op.create_index('idx_memory_entries_importance', 'memory_entries', ['importance'])
    op.create_index('idx_memory_entries_karma', 'memory_entries', ['karma_score'])
    op.create_index('idx_memory_entries_expires', 'memory_entries', ['expires_at'])
    
    # Composite indexes for common query patterns
    op.create_index('idx_memory_entries_agent_layer', 'memory_entries', ['agent_id', 'layer'])
    op.create_index('idx_memory_entries_agent_type', 'memory_entries', ['agent_id', 'memory_type'])
    
    # GIN indexes for array and JSONB columns
    op.execute("CREATE INDEX idx_memory_entries_tags ON memory_entries USING GIN (tags);")
    op.execute("CREATE INDEX idx_memory_entries_metadata ON memory_entries USING GIN (metadata);")
    
    # Create session_contexts table
    op.create_table(
        'session_contexts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('session_id', sa.String(32), unique=True, nullable=False),
        sa.Column('agent_id', sa.String(100), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('last_activity_at', sa.DateTime(timezone=False), nullable=False, server_default=sa.func.now()),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_tokens', sa.Integer(), nullable=False, server_default='8000'),
        sa.Column('active_mission_id', sa.String(100), nullable=True),
        sa.Column('context_vars', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('compressed_summary', sa.Text(), nullable=True),
        sa.Column('compressed_turn_count', sa.Integer(), nullable=False, server_default='0'),
    )
    
    # Create indexes for session_contexts
    op.create_index('idx_session_contexts_session_id', 'session_contexts', ['session_id'])
    op.create_index('idx_session_contexts_agent_id', 'session_contexts', ['agent_id'])
    op.create_index('idx_session_contexts_started', 'session_contexts', ['started_at'])
    
    # Create conversation_turns table
    op.create_table(
        'conversation_turns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('turn_id', sa.String(32), unique=True, nullable=False),
        sa.Column('session_id', sa.String(32), sa.ForeignKey('session_contexts.session_id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.Float(), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
    )
    
    # Create indexes for conversation_turns
    op.create_index('idx_conversation_turns_turn_id', 'conversation_turns', ['turn_id'])
    op.create_index('idx_conversation_turns_session_id', 'conversation_turns', ['session_id'])
    
    logger.info("✅ Memory persistence tables created successfully")


def downgrade() -> None:
    """
    Drop memory persistence tables.
    """
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('conversation_turns')
    op.drop_table('session_contexts')
    op.drop_table('memory_entries')
    
    logger.info("✅ Memory persistence tables dropped")


# Import logger for upgrade/downgrade messages
import logging
logger = logging.getLogger("alembic.runtime.migration")
