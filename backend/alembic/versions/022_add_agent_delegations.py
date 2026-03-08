"""Add agent delegation records.

Revision ID: 022_add_agent_delegations
Revises: 021_add_evaluation_and_optimizer_tables
Create Date: 2026-03-08 19:30:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "022_add_agent_delegations"
down_revision: Union[str, None] = "021_add_evaluation_and_optimizer_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_delegations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            source_agent_id VARCHAR(100) NOT NULL,
            target_agent_id VARCHAR(100) NOT NULL,
            skill_run_id UUID NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'requested',
            delegation_reason TEXT,
            correlation_id VARCHAR(160) NOT NULL,
            requested_by VARCHAR(120) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            accepted_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_delegations_source_agent_id ON agent_delegations (source_agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_delegations_target_agent_id ON agent_delegations (target_agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_delegations_skill_run_id ON agent_delegations (skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_agent_delegations_correlation_id ON agent_delegations (correlation_id);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_agent_delegations_pair_created ON agent_delegations (tenant_id, source_agent_id, target_agent_id, created_at);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_agent_delegations_pair_created;")
    op.execute("DROP INDEX IF EXISTS ix_agent_delegations_correlation_id;")
    op.execute("DROP INDEX IF EXISTS ix_agent_delegations_skill_run_id;")
    op.execute("DROP INDEX IF EXISTS ix_agent_delegations_target_agent_id;")
    op.execute("DROP INDEX IF EXISTS ix_agent_delegations_source_agent_id;")
    op.drop_table("agent_delegations")
