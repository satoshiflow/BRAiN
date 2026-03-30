"""Add premium metadata and pricing fields for skill definitions.

Revision ID: 049_add_skill_premium_metadata
Revises: 048_add_skill_value_fields
Create Date: 2026-03-31 01:15:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "049_add_skill_premium_metadata"
down_revision: Union[str, None] = "048_add_skill_value_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS premium_tier VARCHAR(32) NOT NULL DEFAULT 'free'"
    )
    op.execute(
        "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS internal_credit_price DOUBLE PRECISION NOT NULL DEFAULT 0"
    )
    op.execute(
        "ALTER TABLE IF EXISTS skill_definitions ADD COLUMN IF NOT EXISTS marketplace_listing_state VARCHAR(32) NOT NULL DEFAULT 'internal_only'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_skill_definitions_premium_tier ON skill_definitions (premium_tier)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_skill_definitions_premium_tier")
    op.execute("ALTER TABLE IF EXISTS skill_definitions DROP COLUMN IF EXISTS marketplace_listing_state")
    op.execute("ALTER TABLE IF EXISTS skill_definitions DROP COLUMN IF EXISTS internal_credit_price")
    op.execute("ALTER TABLE IF EXISTS skill_definitions DROP COLUMN IF EXISTS premium_tier")
