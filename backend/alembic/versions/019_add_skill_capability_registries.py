"""Add skill and capability registry tables.

Revision ID: 019_add_skill_capability_registries
Revises: 018_add_quarantine_and_repair_tables
Create Date: 2026-03-08 14:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "019_add_skill_capability_registries"
down_revision: Union[str, None] = "018_add_quarantine_and_repair_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS capability_definitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            owner_scope VARCHAR(16) NOT NULL DEFAULT 'tenant',
            capability_key VARCHAR(120) NOT NULL,
            version INTEGER NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            domain VARCHAR(80) NOT NULL,
            description TEXT NOT NULL,
            input_schema JSONB NOT NULL DEFAULT '{}',
            output_schema JSONB NOT NULL DEFAULT '{}',
            default_timeout_ms INTEGER NOT NULL DEFAULT 30000,
            retry_policy JSONB NOT NULL DEFAULT '{}',
            qos_targets JSONB NOT NULL DEFAULT '{}',
            fallback_capability_key VARCHAR(120),
            policy_constraints JSONB NOT NULL DEFAULT '{}',
            checksum_sha256 VARCHAR(64) NOT NULL,
            created_by VARCHAR(120) NOT NULL,
            updated_by VARCHAR(120) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_capability_owner_scope CHECK (owner_scope IN ('tenant', 'system')),
            CONSTRAINT chk_capability_tenant_system CHECK (
                (owner_scope = 'tenant' AND tenant_id IS NOT NULL) OR
                (owner_scope = 'system' AND tenant_id IS NULL)
            )
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_definitions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            owner_scope VARCHAR(16) NOT NULL DEFAULT 'tenant',
            skill_key VARCHAR(120) NOT NULL,
            version INTEGER NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            purpose TEXT NOT NULL,
            input_schema JSONB NOT NULL DEFAULT '{}',
            output_schema JSONB NOT NULL DEFAULT '{}',
            required_capabilities JSONB NOT NULL DEFAULT '[]',
            optional_capabilities JSONB NOT NULL DEFAULT '[]',
            constraints JSONB NOT NULL DEFAULT '{}',
            quality_profile VARCHAR(32) NOT NULL DEFAULT 'standard',
            fallback_policy VARCHAR(32) NOT NULL DEFAULT 'allowed',
            evaluation_criteria JSONB NOT NULL DEFAULT '{}',
            risk_tier VARCHAR(32) NOT NULL DEFAULT 'medium',
            policy_pack_ref VARCHAR(120) NOT NULL DEFAULT 'default',
            trust_tier_min VARCHAR(32) NOT NULL DEFAULT 'internal',
            checksum_sha256 VARCHAR(64) NOT NULL,
            created_by VARCHAR(120) NOT NULL,
            updated_by VARCHAR(120) NOT NULL,
            approved_by VARCHAR(120),
            approved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_skill_owner_scope CHECK (owner_scope IN ('tenant', 'system')),
            CONSTRAINT chk_skill_tenant_system CHECK (
                (owner_scope = 'tenant' AND tenant_id IS NOT NULL) OR
                (owner_scope = 'system' AND tenant_id IS NULL)
            )
        );
        """
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_capability_definitions_tenant_key_version ON capability_definitions (tenant_id, capability_key, version) WHERE owner_scope = 'tenant';"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_capability_definitions_system_key_version ON capability_definitions (capability_key, version) WHERE owner_scope = 'system';"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_capability_definitions_tenant_active ON capability_definitions (tenant_id, capability_key) WHERE owner_scope = 'tenant' AND status = 'active';"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_capability_definitions_system_active ON capability_definitions (capability_key) WHERE owner_scope = 'system' AND status = 'active';"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_capability_definitions_status ON capability_definitions (status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_capability_definitions_domain_status ON capability_definitions (domain, status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_capability_definitions_key_scope_version ON capability_definitions (capability_key, owner_scope, version);"
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_skill_definitions_tenant_key_version ON skill_definitions (tenant_id, skill_key, version) WHERE owner_scope = 'tenant';"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_skill_definitions_system_key_version ON skill_definitions (skill_key, version) WHERE owner_scope = 'system';"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_skill_definitions_tenant_active ON skill_definitions (tenant_id, skill_key) WHERE owner_scope = 'tenant' AND status = 'active';"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_skill_definitions_system_active ON skill_definitions (skill_key) WHERE owner_scope = 'system' AND status = 'active';"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_skill_definitions_status ON skill_definitions (status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_skill_definitions_risk_status ON skill_definitions (risk_tier, status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_skill_definitions_key_scope_version ON skill_definitions (skill_key, owner_scope, version);"
    )

    op.execute("DROP TRIGGER IF EXISTS update_capability_definitions_updated_at ON capability_definitions;")
    op.execute(
        """
        CREATE TRIGGER update_capability_definitions_updated_at
            BEFORE UPDATE ON capability_definitions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )
    op.execute("DROP TRIGGER IF EXISTS update_skill_definitions_updated_at ON skill_definitions;")
    op.execute(
        """
        CREATE TRIGGER update_skill_definitions_updated_at
            BEFORE UPDATE ON skill_definitions
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS update_skill_definitions_updated_at ON skill_definitions;")
    op.execute("DROP TRIGGER IF EXISTS update_capability_definitions_updated_at ON capability_definitions;")
    op.execute("DROP INDEX IF EXISTS ix_skill_definitions_key_scope_version;")
    op.execute("DROP INDEX IF EXISTS ix_skill_definitions_risk_status;")
    op.execute("DROP INDEX IF EXISTS ix_skill_definitions_status;")
    op.execute("DROP INDEX IF EXISTS ux_skill_definitions_system_active;")
    op.execute("DROP INDEX IF EXISTS ux_skill_definitions_tenant_active;")
    op.execute("DROP INDEX IF EXISTS ux_skill_definitions_system_key_version;")
    op.execute("DROP INDEX IF EXISTS ux_skill_definitions_tenant_key_version;")
    op.execute("DROP INDEX IF EXISTS ix_capability_definitions_key_scope_version;")
    op.execute("DROP INDEX IF EXISTS ix_capability_definitions_domain_status;")
    op.execute("DROP INDEX IF EXISTS ix_capability_definitions_status;")
    op.execute("DROP INDEX IF EXISTS ux_capability_definitions_system_active;")
    op.execute("DROP INDEX IF EXISTS ux_capability_definitions_tenant_active;")
    op.execute("DROP INDEX IF EXISTS ux_capability_definitions_system_key_version;")
    op.execute("DROP INDEX IF EXISTS ux_capability_definitions_tenant_key_version;")
    op.drop_table("skill_definitions")
    op.drop_table("capability_definitions")
