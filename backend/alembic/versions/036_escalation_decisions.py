"""Add supervisor escalation decision columns.

Revision ID: 036_escalation_decisions
Revises: 035_domain_escalations
Create Date: 2026-03-11 22:55:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "036_escalation_decisions"
down_revision: Union[str, None] = "035_domain_escalations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE domain_escalations ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(120);")
    op.execute("ALTER TABLE domain_escalations ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;")
    op.execute("ALTER TABLE domain_escalations ADD COLUMN IF NOT EXISTS decision_reason TEXT;")
    op.execute("ALTER TABLE domain_escalations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();")


def downgrade() -> None:
    op.execute("ALTER TABLE domain_escalations DROP COLUMN IF EXISTS updated_at;")
    op.execute("ALTER TABLE domain_escalations DROP COLUMN IF EXISTS decision_reason;")
    op.execute("ALTER TABLE domain_escalations DROP COLUMN IF EXISTS reviewed_at;")
    op.execute("ALTER TABLE domain_escalations DROP COLUMN IF EXISTS reviewed_by;")
