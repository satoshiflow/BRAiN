"""Add discovery layer proposal-only persistence.

Revision ID: 030_add_discovery_layer
Revises: 029_add_deliberation_layer
Create Date: 2026-03-09 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "030_add_discovery_layer"
down_revision: Union[str, None] = "029_add_deliberation_layer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_gaps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            skill_run_id UUID NOT NULL,
            pattern_id UUID NOT NULL,
            gap_type VARCHAR(40) NOT NULL DEFAULT 'skill',
            summary TEXT NOT NULL,
            severity VARCHAR(24) NOT NULL DEFAULT 'medium',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            evidence JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_skill_gaps_tenant_run ON skill_gaps (tenant_id, skill_run_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS capability_gaps (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            skill_run_id UUID NOT NULL,
            pattern_id UUID NOT NULL,
            capability_key VARCHAR(160) NOT NULL,
            summary TEXT NOT NULL,
            severity VARCHAR(24) NOT NULL DEFAULT 'medium',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            evidence JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_capability_gaps_tenant_run ON capability_gaps (tenant_id, skill_run_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS discovery_skill_proposals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            skill_run_id UUID NOT NULL,
            pattern_id UUID NOT NULL,
            skill_gap_id UUID NOT NULL,
            capability_gap_id UUID NOT NULL,
            target_skill_key VARCHAR(160) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            proposal_summary TEXT NOT NULL,
            proposal_evidence JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_discovery_skill_proposals_tenant_run UNIQUE (tenant_id, skill_run_id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_discovery_skill_proposals_tenant_run ON discovery_skill_proposals (tenant_id, skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_discovery_skill_proposals_status ON discovery_skill_proposals (status);")

    op.execute(
        """
        INSERT INTO module_lifecycle (
            id, module_id, owner_scope, classification, lifecycle_status, canonical_path,
            active_routes, data_owner, auth_surface, event_contract_status, audit_policy,
            migration_adapter, kill_switch, replacement_target, sunset_phase, notes,
            created_at, updated_at
        )
        SELECT
            gen_random_uuid(),
            'discovery_layer',
            'system',
            'NEW',
            'experimental',
            'backend/app/modules/discovery_layer',
            '["/api/discovery/skill-runs/{skill_run_id}/analyze", "/api/discovery/proposals/{proposal_id}/queue-review"]'::jsonb,
            'consolidation_layer',
            'operator+admin',
            'partial',
            'audit_required',
            'app.modules.discovery_layer',
            NULL,
            'evolution_control',
            'phase_p6',
            'Proposal-only discovery based on knowledge, consolidation, and observer context',
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = 'discovery_layer'
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM module_lifecycle WHERE module_id = 'discovery_layer';")
    op.execute("DROP INDEX IF EXISTS ix_discovery_skill_proposals_status;")
    op.execute("DROP INDEX IF EXISTS ix_discovery_skill_proposals_tenant_run;")
    op.drop_table("discovery_skill_proposals")
    op.execute("DROP INDEX IF EXISTS ix_capability_gaps_tenant_run;")
    op.drop_table("capability_gaps")
    op.execute("DROP INDEX IF EXISTS ix_skill_gaps_tenant_run;")
    op.drop_table("skill_gaps")
