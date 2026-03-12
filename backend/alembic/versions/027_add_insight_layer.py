"""Add insight layer persistence and lifecycle seed.

Revision ID: 027_add_insight_layer
Revises: 026_add_observer_core
Create Date: 2026-03-09 17:20:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "027_add_insight_layer"
down_revision: Union[str, None] = "026_add_observer_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS insight_candidates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            experience_id UUID NOT NULL,
            skill_run_id UUID NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'proposed',
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.5,
            scope VARCHAR(40) NOT NULL DEFAULT 'skill_run',
            hypothesis TEXT NOT NULL,
            evidence JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_insight_candidates_tenant_run ON insight_candidates (tenant_id, skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_insight_candidates_status ON insight_candidates (status);")

    op.execute(
        """
        INSERT INTO module_lifecycle (
            module_id, owner_scope, classification, lifecycle_status, canonical_path,
            active_routes, data_owner, auth_surface, event_contract_status, audit_policy,
            migration_adapter, kill_switch, replacement_target, sunset_phase, notes
        )
        SELECT
            'insight_layer',
            'system',
            'NEW',
            'experimental',
            'backend/app/modules/insight_layer',
            '["/api/insights/skill-runs/{skill_run_id}/derive"]'::jsonb,
            'experience_layer',
            'operator+admin',
            'partial',
            'audit_required',
            'app.modules.insight_layer',
            NULL,
            NULL,
            'phase_p2',
            'Insight candidates derived from ExperienceRecord'
        WHERE NOT EXISTS (
            SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = 'insight_layer'
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM module_lifecycle WHERE module_id = 'insight_layer';")
    op.execute("DROP INDEX IF EXISTS ix_insight_candidates_status;")
    op.execute("DROP INDEX IF EXISTS ix_insight_candidates_tenant_run;")
    op.drop_table("insight_candidates")
