"""add_cluster_system

Revision ID: 012_add_cluster_system
Revises: 011_learning_persistence
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '012_add_cluster_system'
down_revision = '011_learning_persistence'
branch_labels = None
depends_on = None


def upgrade():
    # Create clusters table
    op.create_table(
        'clusters',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),  # department|project|temporary|persistent
        sa.Column('status', sa.String(50), nullable=False, server_default='planning'),
        sa.Column('blueprint_id', sa.String(), nullable=False),
        sa.Column('blueprint_version', sa.String(), server_default='1.0.0'),
        sa.Column('parent_cluster_id', sa.String(), sa.ForeignKey('clusters.id'), nullable=True),
        sa.Column('min_workers', sa.Integer(), server_default='1'),
        sa.Column('max_workers', sa.Integer(), server_default='10'),
        sa.Column('current_workers', sa.Integer(), server_default='0'),
        sa.Column('target_workers', sa.Integer(), server_default='1'),
        sa.Column('health_score', sa.Float(), server_default='1.0'),
        sa.Column('load_percentage', sa.Float(), server_default='0.0'),
        sa.Column('tasks_completed', sa.Integer(), server_default='0'),
        sa.Column('tasks_failed', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('hibernated_at', sa.DateTime(), nullable=True),
        sa.Column('destroyed_at', sa.DateTime(), nullable=True),
        sa.Column('last_active', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),
        sa.Column('config', postgresql.JSONB(), server_default='{}'),
    )
    
    # Create indexes on clusters
    op.create_index('ix_clusters_name', 'clusters', ['name'])
    op.create_index('ix_clusters_type', 'clusters', ['type'])
    op.create_index('ix_clusters_status', 'clusters', ['status'])
    op.create_index('ix_clusters_blueprint_id', 'clusters', ['blueprint_id'])
    op.create_index('ix_clusters_parent_cluster_id', 'clusters', ['parent_cluster_id'])
    op.create_index('ix_clusters_created_at', 'clusters', ['created_at'])
    
    # Create cluster_agents table
    op.create_table(
        'cluster_agents',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('cluster_id', sa.String(), sa.ForeignKey('clusters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),  # supervisor|lead|specialist|worker
        sa.Column('supervisor_id', sa.String(), sa.ForeignKey('cluster_agents.id'), nullable=True),
        sa.Column('capabilities', postgresql.JSONB(), server_default='[]'),
        sa.Column('skills', postgresql.JSONB(), server_default='[]'),
        sa.Column('status', sa.String(50), server_default='active'),
        sa.Column('health_score', sa.Float(), server_default='1.0'),
        sa.Column('tasks_completed', sa.Integer(), server_default='0'),
        sa.Column('tasks_failed', sa.Integer(), server_default='0'),
        sa.Column('avg_task_duration', sa.Float(), server_default='0.0'),
        sa.Column('last_error', sa.String(), nullable=True),
        sa.Column('spawned_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_active', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('stopped_at', sa.DateTime(), nullable=True),
    )
    
    op.create_index('ix_cluster_agents_cluster_id', 'cluster_agents', ['cluster_id'])
    op.create_index('ix_cluster_agents_agent_id', 'cluster_agents', ['agent_id'])
    op.create_index('ix_cluster_agents_role', 'cluster_agents', ['role'])
    op.create_index('ix_cluster_agents_supervisor_id', 'cluster_agents', ['supervisor_id'])
    op.create_index('ix_cluster_agents_status', 'cluster_agents', ['status'])
    
    # Create cluster_blueprints table
    op.create_table(
        'cluster_blueprints',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False, server_default='1.0.0'),
        sa.Column('blueprint_yaml', sa.Text(), nullable=False),
        sa.Column('manifest_path', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('author', sa.String(), server_default='brain-system'),
        sa.Column('tags', postgresql.JSONB(), server_default='[]'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('instances_created', sa.Integer(), server_default='0'),
        sa.Column('instances_active', sa.Integer(), server_default='0'),
        sa.Column('success_rate', sa.Float(), server_default='0.0'),
    )
    
    # Create cluster_metrics table
    op.create_table(
        'cluster_metrics',
        sa.Column('id', sa.String(), primary_key=True),
        sa.Column('cluster_id', sa.String(), sa.ForeignKey('clusters.id', ondelete='CASCADE'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('cpu_usage', sa.Float(), server_default='0.0'),
        sa.Column('memory_usage', sa.Float(), server_default='0.0'),
        sa.Column('tasks_per_minute', sa.Float(), server_default='0.0'),
        sa.Column('avg_response_time', sa.Float(), server_default='0.0'),
        sa.Column('error_rate', sa.Float(), server_default='0.0'),
        sa.Column('active_agents', sa.Integer(), server_default='0'),
        sa.Column('idle_agents', sa.Integer(), server_default='0'),
        sa.Column('busy_agents', sa.Integer(), server_default='0'),
        sa.Column('failed_agents', sa.Integer(), server_default='0'),
        sa.Column('queue_length', sa.Integer(), server_default='0'),
    )
    
    op.create_index('ix_cluster_blueprints_name', 'cluster_blueprints', ['name'])
    op.create_index('ix_cluster_blueprints_is_active', 'cluster_blueprints', ['is_active'])

    op.create_index('ix_cluster_metrics_cluster_id', 'cluster_metrics', ['cluster_id'])
    op.create_index('ix_cluster_metrics_timestamp', 'cluster_metrics', ['timestamp'])


def downgrade():
    op.drop_table('cluster_metrics')
    op.drop_table('cluster_blueprints')
    op.drop_table('cluster_agents')
    op.drop_table('clusters')
