"""Add domain agent registry table.

Revision ID: 034_add_domain_agent_registry
Revises: 033_add_axe_persistent_mapping
Create Date: 2026-03-11 21:30:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "034_add_domain_agent_registry"
down_revision: Union[str, None] = "033_add_axe_persistent_mapping"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS domain_agent_configs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            owner_scope VARCHAR(16) NOT NULL DEFAULT 'tenant',
            domain_key VARCHAR(100) NOT NULL,
            display_name VARCHAR(200) NOT NULL,
            description TEXT,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            allowed_skill_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
            allowed_capability_keys JSONB NOT NULL DEFAULT '[]'::jsonb,
            allowed_specialist_roles JSONB NOT NULL DEFAULT '[]'::jsonb,
            review_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
            risk_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
            escalation_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
            budget_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_domain_agent_owner_scope CHECK (owner_scope IN ('tenant', 'system')),
            CONSTRAINT ck_domain_agent_tenant_scope CHECK (
                (owner_scope = 'tenant' AND tenant_id IS NOT NULL)
                OR (owner_scope = 'system' AND tenant_id IS NULL)
            )
        );
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_domain_agent_configs_tenant_id ON domain_agent_configs (tenant_id);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_domain_agent_configs_domain_key ON domain_agent_configs (domain_key);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_domain_agent_configs_status ON domain_agent_configs (status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_domain_agent_configs_tenant_domain ON domain_agent_configs (tenant_id, domain_key);"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_domain_agent_configs_scope_key
        ON domain_agent_configs (owner_scope, COALESCE(tenant_id, ''), domain_key);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_domain_agent_configs_scope_key;")
    op.execute("DROP INDEX IF EXISTS ix_domain_agent_configs_tenant_domain;")
    op.execute("DROP INDEX IF EXISTS ix_domain_agent_configs_status;")
    op.execute("DROP INDEX IF EXISTS ix_domain_agent_configs_domain_key;")
    op.execute("DROP INDEX IF EXISTS ix_domain_agent_configs_tenant_id;")
    op.drop_table("domain_agent_configs")
