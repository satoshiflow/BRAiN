"""Add value-scoring fields to skill definitions.

Revision ID: 048_add_skill_value_fields
Revises: 047_add_knowledge_engine
Create Date: 2026-03-30 22:20:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "048_add_skill_value_fields"
down_revision: Union[str, None] = "047_add_knowledge_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS value_score DOUBLE PRECISION NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS effort_saved_hours DOUBLE PRECISION NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS complexity_level VARCHAR(32) NOT NULL DEFAULT 'medium'"
    )
    op.execute(
        "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS quality_impact DOUBLE PRECISION NOT NULL DEFAULT 0"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_skill_definitions_value_score ON skill_definitions (value_score DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_skill_definitions_value_score")
    op.execute("ALTER TABLE IF EXISTS skill_definitions DROP COLUMN IF EXISTS quality_impact")
    op.execute("ALTER TABLE IF EXISTS skill_definitions DROP COLUMN IF EXISTS complexity_level")
    op.execute("ALTER TABLE IF EXISTS skill_definitions DROP COLUMN IF EXISTS effort_saved_hours")
    op.execute("ALTER TABLE IF EXISTS skill_definitions DROP COLUMN IF EXISTS value_score")
