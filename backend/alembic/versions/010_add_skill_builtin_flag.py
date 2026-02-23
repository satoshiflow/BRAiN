"""Add is_builtin flag to skills

Revision ID: 010_add_skill_builtin_flag
Revises: 009_skills_system
Create Date: 2025-02-23 08:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '010_add_skill_builtin_flag'
down_revision: Union[str, None] = '009_skills_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_builtin column to skills table."""
    op.execute("""
        ALTER TABLE skills 
        ADD COLUMN IF NOT EXISTS is_builtin BOOLEAN NOT NULL DEFAULT false;
    """)
    
    # Add index for quick builtin lookups
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_skills_is_builtin 
        ON skills (is_builtin);
    """)


def downgrade() -> None:
    """Remove is_builtin column from skills table."""
    op.execute("DROP INDEX IF EXISTS idx_skills_is_builtin;")
    op.execute("ALTER TABLE skills DROP COLUMN IF EXISTS is_builtin;")
