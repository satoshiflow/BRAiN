"""
Fred Bridge Database Migration

Creates tables for:
- fred_tickets (Ticket Lifecycle)
- fred_patches (Patch Artifact Lifecycle)

Revision ID: fred_bridge_v1
Revises: (base)
Create Date: 2026-02-13
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import uuid

# Revision identifiers
revision = 'fred_bridge_v1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    
    # Create fred_tickets table
    op.create_table(
        'fred_tickets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('ticket_id', sa.Text(), nullable=False, unique=True),
        sa.Column('type', sa.Text(), nullable=False),  # incident|feature|refactor|security
        sa.Column('severity', sa.Text(), nullable=False),  # S1|S2|S3|S4
        sa.Column('component', sa.Text(), nullable=False),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='open'),  # open|triaged|in_analysis|patch_submitted|accepted|closed
        sa.Column('environment', sa.Text(), nullable=False, server_default='staging'),  # dev|staging|prod
        sa.Column('reporter', sa.Text(), nullable=False, server_default='brain'),
        sa.Column('constraints', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('observed_symptoms', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('last_known_good', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('recent_changes', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('reproduction_steps', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('expected_outcome', sa.Text(), nullable=False, server_default=''),
        sa.Column('links', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    
    # Indexes for fred_tickets
    op.create_index('idx_fred_tickets_status', 'fred_tickets', ['status'])
    op.create_index('idx_fred_tickets_severity', 'fred_tickets', ['severity'])
    op.create_index('idx_fred_tickets_component', 'fred_tickets', ['component'])
    op.create_index('idx_fred_tickets_created_at', 'fred_tickets', ['created_at'])
    
    # Create fred_patches table
    op.create_table(
        'fred_patches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('patch_id', sa.Text(), nullable=False, unique=True),
        sa.Column('ticket_id', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False, server_default='proposed'),  # proposed|in_review|approved|staging|canary|production|rolled_back|rejected
        sa.Column('author', sa.Text(), nullable=False, server_default='fred'),
        sa.Column('target_repo', sa.Text(), nullable=False, server_default='BRAiN'),
        sa.Column('target_paths', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('pr', postgresql.JSONB(), nullable=False, server_default='{}'),  # {url, git_ref}
        sa.Column('git_diff_excerpt', sa.Text(), nullable=False, server_default=''),
        sa.Column('tests', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('migrations', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('risk_assessment', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('security_impact', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('observability', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('approvals', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('deployment_plan', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('release_notes', sa.Text(), nullable=False, server_default=''),
        sa.Column('metadata', postgresql.JSONB(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    
    # Foreign key constraint
    op.create_foreign_key(
        'fk_fred_patches_ticket',
        'fred_patches', 'fred_tickets',
        ['ticket_id'], ['ticket_id'],
        ondelete='CASCADE'
    )
    
    # Indexes for fred_patches
    op.create_index('idx_fred_patches_ticket_id', 'fred_patches', ['ticket_id'])
    op.create_index('idx_fred_patches_status', 'fred_patches', ['status'])
    op.create_index('idx_fred_patches_created_at', 'fred_patches', ['created_at'])
    
    # Create updated_at trigger function
    op.execute('''
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    ''')
    
    # Create triggers
    op.execute('''
        DROP TRIGGER IF EXISTS trg_fred_tickets_updated_at ON fred_tickets;
        CREATE TRIGGER trg_fred_tickets_updated_at
        BEFORE UPDATE ON fred_tickets
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    ''')
    
    op.execute('''
        DROP TRIGGER IF EXISTS trg_fred_patches_updated_at ON fred_patches;
        CREATE TRIGGER trg_fred_patches_updated_at
        BEFORE UPDATE ON fred_patches
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
    ''')


def downgrade():
    # Drop triggers
    op.execute('DROP TRIGGER IF EXISTS trg_fred_patches_updated_at ON fred_patches')
    op.execute('DROP TRIGGER IF EXISTS trg_fred_tickets_updated_at ON fred_tickets')
    
    # Drop tables
    op.drop_table('fred_patches')
    op.drop_table('fred_tickets')
    
    # Drop function
    op.execute('DROP FUNCTION IF EXISTS set_updated_at()')
