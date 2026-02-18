"""add_cluster_system

Revision ID: add_cluster_system
Revises: 
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = 'add_cluster_system'
down_revision = None  # Set to last migration if exists
branch_labels = None
depends_on = None


def upgrade():
    # Create clusters table
    op.create_table(
        'clusters',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),  # department|project|product|functional
        sa.Column('blueprint_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='planning'),
        sa.Column('min_workers', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('max_workers', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('target_workers', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('current_workers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('configuration', postgresql.JSONB(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('last_active_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('hibernated_at', sa.DateTime(), nullable=True),
    )
    
    # Create index on status
    op.create_index('ix_clusters_status', 'clusters', ['status'])
    op.create_index('ix_clusters_type', 'clusters', ['type'])
    
    # Create cluster_agents table
    op.create_table(
        'cluster_agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cluster_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clusters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),  # supervisor|lead|specialist|worker
        sa.Column('tier', sa.Integer(), nullable=False, server_default='1'),  # 1-4
        sa.Column('status', sa.String(50), nullable=False, server_default='spawning'),
        sa.Column('skills', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('task_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('destroyed_at', sa.DateTime(), nullable=True),
    )
    
    op.create_index('ix_cluster_agents_cluster_id', 'cluster_agents', ['cluster_id'])
    op.create_index('ix_cluster_agents_agent_id', 'cluster_agents', ['agent_id'])
    op.create_index('ix_cluster_agents_status', 'cluster_agents', ['status'])
    
    # Create cluster_blueprints table
    op.create_table(
        'cluster_blueprints',
        sa.Column('id', sa.String(100), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('blueprint_data', postgresql.JSONB(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Create cluster_metrics table
    op.create_table(
        'cluster_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('cluster_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('clusters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('metric_type', sa.String(50), nullable=False),  # performance|scaling|error
        sa.Column('value', postgresql.JSONB(), nullable=False),
    )
    
    op.create_index('ix_cluster_metrics_cluster_id', 'cluster_metrics', ['cluster_id'])
    op.create_index('ix_cluster_metrics_timestamp', 'cluster_metrics', ['timestamp'])
    op.create_index('ix_cluster_metrics_type', 'cluster_metrics', ['metric_type'])


def downgrade():
    op.drop_table('cluster_metrics')
    op.drop_table('cluster_blueprints')
    op.drop_table('cluster_agents')
    op.drop_table('clusters')
