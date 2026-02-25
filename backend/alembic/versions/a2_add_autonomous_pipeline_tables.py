"""Add autonomous pipeline tables - Workspace, Project, RunContract

Revision ID: a2_add_autonomous_pipeline_tables
Revises: a1_add_token_tables
Create Date: 2026-02-25 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a2_add_autonomous_pipeline_tables'
down_revision: Union[str, None] = 'a1_add_token_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workspaces table
    op.create_table('workspaces',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('owner_id', sa.String(length=255), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('max_projects', sa.Integer(), nullable=False),
        sa.Column('max_runs_per_day', sa.Integer(), nullable=False),
        sa.Column('max_storage_gb', sa.Float(), nullable=False),
        sa.Column('settings', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaces_workspace_id'), 'workspaces', ['workspace_id'], unique=True)
    op.create_index(op.f('ix_workspaces_slug'), 'workspaces', ['slug'], unique=False)
    op.create_index(op.f('ix_workspaces_status'), 'workspaces', ['status'], unique=False)
    op.create_index(op.f('ix_workspaces_owner_id'), 'workspaces', ['owner_id'], unique=False)
    op.create_index(op.f('ix_workspaces_created_at'), 'workspaces', ['created_at'], unique=False)

    # Create projects table
    op.create_table('projects',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=False),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('slug', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('default_budget', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('default_policy', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('total_runs', sa.Integer(), nullable=False),
        sa.Column('successful_runs', sa.Integer(), nullable=False),
        sa.Column('failed_runs', sa.Integer(), nullable=False),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.workspace_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_project_id'), 'projects', ['project_id'], unique=True)
    op.create_index(op.f('ix_projects_workspace_id'), 'projects', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_projects_slug'), 'projects', ['slug'], unique=False)
    op.create_index(op.f('ix_projects_status'), 'projects', ['status'], unique=False)
    op.create_index(op.f('ix_projects_created_at'), 'projects', ['created_at'], unique=False)

    # Create run_contracts table
    op.create_table('run_contracts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('contract_id', sa.String(length=255), nullable=False),
        sa.Column('workspace_id', sa.String(length=255), nullable=False),
        sa.Column('project_id', sa.String(length=255), nullable=True),
        sa.Column('graph_id', sa.String(length=255), nullable=False),
        sa.Column('business_intent_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('dry_run', sa.Boolean(), nullable=False),
        sa.Column('graph_spec', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('execution_result', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('evidence_pack', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('contract_hash', sa.String(length=255), nullable=True),
        sa.Column('evidence_hash', sa.String(length=255), nullable=True),
        sa.Column('storage_path', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.workspace_id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.project_id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_run_contracts_contract_id'), 'run_contracts', ['contract_id'], unique=True)
    op.create_index(op.f('ix_run_contracts_workspace_id'), 'run_contracts', ['workspace_id'], unique=False)
    op.create_index(op.f('ix_run_contracts_project_id'), 'run_contracts', ['project_id'], unique=False)
    op.create_index(op.f('ix_run_contracts_graph_id'), 'run_contracts', ['graph_id'], unique=False)
    op.create_index(op.f('ix_run_contracts_status'), 'run_contracts', ['status'], unique=False)
    op.create_index(op.f('ix_run_contracts_created_at'), 'run_contracts', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop run_contracts table
    op.drop_index(op.f('ix_run_contracts_created_at'), table_name='run_contracts')
    op.drop_index(op.f('ix_run_contracts_status'), table_name='run_contracts')
    op.drop_index(op.f('ix_run_contracts_graph_id'), table_name='run_contracts')
    op.drop_index(op.f('ix_run_contracts_project_id'), table_name='run_contracts')
    op.drop_index(op.f('ix_run_contracts_workspace_id'), table_name='run_contracts')
    op.drop_index(op.f('ix_run_contracts_contract_id'), table_name='run_contracts')
    op.drop_table('run_contracts')

    # Drop projects table
    op.drop_index(op.f('ix_projects_created_at'), table_name='projects')
    op.drop_index(op.f('ix_projects_status'), table_name='projects')
    op.drop_index(op.f('ix_projects_slug'), table_name='projects')
    op.drop_index(op.f('ix_projects_workspace_id'), table_name='projects')
    op.drop_index(op.f('ix_projects_project_id'), table_name='projects')
    op.drop_table('projects')

    # Drop workspaces table
    op.drop_index(op.f('ix_workspaces_created_at'), table_name='workspaces')
    op.drop_index(op.f('ix_workspaces_owner_id'), table_name='workspaces')
    op.drop_index(op.f('ix_workspaces_status'), table_name='workspaces')
    op.drop_index(op.f('ix_workspaces_slug'), table_name='workspaces')
    op.drop_index(op.f('ix_workspaces_workspace_id'), table_name='workspaces')
    op.drop_table('workspaces')
