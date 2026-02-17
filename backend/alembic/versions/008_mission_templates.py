"""Add mission_templates table

Revision ID: 008_mission_templates
Revises: 001_initial_schema
Create Date: 2025-02-12 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '008_mission_templates'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create mission_templates table for reusable mission templates.
    """
    op.create_table(
        'mission_templates',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(100), nullable=False, server_default='general'),
        sa.Column('steps', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('variables', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    
    # Create index on category for filtering
    op.create_index(
        'idx_mission_templates_category',
        'mission_templates',
        ['category']
    )
    
    # Create index on name for search
    op.create_index(
        'idx_mission_templates_name',
        'mission_templates',
        ['name']
    )


def downgrade() -> None:
    """
    Drop mission_templates table.
    """
    op.drop_index('idx_mission_templates_name', table_name='mission_templates')
    op.drop_index('idx_mission_templates_category', table_name='mission_templates')
    op.drop_table('mission_templates')
