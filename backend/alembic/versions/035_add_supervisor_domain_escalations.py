"""Add supervisor domain escalations table.

Revision ID: 035_domain_escalations
Revises: 034_add_domain_agent_registry
Create Date: 2026-03-11 22:20:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "035_domain_escalations"
down_revision: Union[str, None] = "034_add_domain_agent_registry"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS domain_escalations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            domain_key VARCHAR(100) NOT NULL,
            requested_by VARCHAR(120) NOT NULL,
            requested_by_type VARCHAR(32) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'queued',
            reason TEXT NOT NULL,
            reasons JSONB NOT NULL DEFAULT '[]'::jsonb,
            recommended_next_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
            risk_tier VARCHAR(32) NOT NULL DEFAULT 'high',
            correlation_id VARCHAR(160),
            context JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_domain_escalations_tenant_id ON domain_escalations (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_domain_escalations_domain_key ON domain_escalations (domain_key);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_domain_escalations_requested_by ON domain_escalations (requested_by);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_domain_escalations_status ON domain_escalations (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_domain_escalations_correlation_id ON domain_escalations (correlation_id);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_domain_escalations_tenant_created ON domain_escalations (tenant_id, created_at);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_domain_escalations_tenant_created;")
    op.execute("DROP INDEX IF EXISTS ix_domain_escalations_correlation_id;")
    op.execute("DROP INDEX IF EXISTS ix_domain_escalations_status;")
    op.execute("DROP INDEX IF EXISTS ix_domain_escalations_requested_by;")
    op.execute("DROP INDEX IF EXISTS ix_domain_escalations_domain_key;")
    op.execute("DROP INDEX IF EXISTS ix_domain_escalations_tenant_id;")
    op.drop_table("domain_escalations")
