"""Add consolidation and evolution control persistence.

Revision ID: 028_add_consolidation_and_evolution_control
Revises: 027_add_insight_layer
Create Date: 2026-03-09 18:05:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "028_add_consolidation_and_evolution_control"
down_revision: Union[str, None] = "027_add_insight_layer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pattern_candidates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            insight_id UUID NOT NULL,
            skill_run_id UUID NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'proposed',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            recurrence_support DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            pattern_summary TEXT NOT NULL,
            failure_modes JSONB NOT NULL DEFAULT '[]',
            evidence JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_pattern_candidates_tenant_run ON pattern_candidates (tenant_id, skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_pattern_candidates_status ON pattern_candidates (status);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS evolution_proposals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            pattern_id UUID NOT NULL,
            skill_run_id UUID NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            target_skill_key VARCHAR(160) NOT NULL,
            summary TEXT NOT NULL,
            governance_required VARCHAR(16) NOT NULL DEFAULT 'true',
            validation_state VARCHAR(32) NOT NULL DEFAULT 'required',
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_evolution_proposals_tenant_pattern UNIQUE (tenant_id, pattern_id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_evolution_proposals_tenant_run ON evolution_proposals (tenant_id, skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evolution_proposals_status ON evolution_proposals (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evolution_proposals_skill_key ON evolution_proposals (tenant_id, target_skill_key);")

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
            'consolidation_layer',
            'system',
            'NEW',
            'experimental',
            'backend/app/modules/consolidation_layer',
            '["/api/consolidation/skill-runs/{skill_run_id}/derive"]'::jsonb,
            'insight_layer',
            'operator+admin',
            'partial',
            'audit_required',
            'app.modules.consolidation_layer',
            NULL,
            NULL,
            'phase_p3',
            'Pattern candidates consolidated from insight candidates',
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = 'consolidation_layer'
        );
        """
    )

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
            'evolution_control',
            'system',
            'NEW',
            'experimental',
            'backend/app/modules/evolution_control',
            '["/api/evolution/proposals/patterns/{pattern_id}", "/api/evolution/proposals/{proposal_id}/transition"]'::jsonb,
            'governance',
            'admin+system_admin',
            'partial',
            'audit_required',
            'app.modules.evolution_control',
            NULL,
            'skills_registry',
            'phase_p3',
            'Governed proposal lifecycle without direct skill mutation',
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = 'evolution_control'
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM module_lifecycle WHERE module_id IN ('consolidation_layer', 'evolution_control');")
    op.execute("DROP INDEX IF EXISTS ix_evolution_proposals_skill_key;")
    op.execute("DROP INDEX IF EXISTS ix_evolution_proposals_status;")
    op.execute("DROP INDEX IF EXISTS ix_evolution_proposals_tenant_run;")
    op.drop_table("evolution_proposals")
    op.execute("DROP INDEX IF EXISTS ix_pattern_candidates_status;")
    op.execute("DROP INDEX IF EXISTS ix_pattern_candidates_tenant_run;")
    op.drop_table("pattern_candidates")
