"""Add CHECK constraint for domain_escalations.status valid values.

Revision ID: 037_escalation_status_constraint
Revises: 036_escalation_decisions
Create Date: 2026-03-11 23:30:00.000000

Rationale:
    Migration 035 created the domain_escalations table without a CHECK constraint
    on the status column. The state-machine logic (queued -> in_review -> approved /
    denied / cancelled) lives only in the service layer, meaning a direct SQL write
    or an external system could insert arbitrary status strings.

    This migration adds an explicit CHECK constraint at the database layer to enforce
    the canonical state-machine values. The constraint is added non-destructively via
    ALTER TABLE ... ADD CONSTRAINT ... NOT VALID, then validated separately to avoid
    full table locking on large deployments.
"""

from typing import Sequence, Union

from alembic import op


revision: str = "037_escalation_status_constraint"
down_revision: Union[str, None] = "036_escalation_decisions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONSTRAINT_NAME = "ck_domain_escalations_status"
_VALID_STATUSES = "('queued', 'in_review', 'approved', 'denied', 'cancelled')"


def upgrade() -> None:
    # Add constraint as NOT VALID first — this avoids a full table scan / lock
    # on existing rows at migration time. VALIDATE CONSTRAINT runs a sequential
    # scan but does not take an exclusive lock, making it safe on live tables.
    op.execute(
        f"""
        ALTER TABLE domain_escalations
        ADD CONSTRAINT {_CONSTRAINT_NAME}
        CHECK (status IN {_VALID_STATUSES})
        NOT VALID;
        """
    )
    op.execute(
        f"ALTER TABLE domain_escalations VALIDATE CONSTRAINT {_CONSTRAINT_NAME};"
    )


def downgrade() -> None:
    op.execute(
        f"ALTER TABLE domain_escalations DROP CONSTRAINT IF EXISTS {_CONSTRAINT_NAME};"
    )
