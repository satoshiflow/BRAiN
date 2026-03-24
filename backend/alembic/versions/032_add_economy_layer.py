"""Add economy layer prioritization support.

Revision ID: 032_add_economy_layer
Revises: 031_finalize_discovery_contracts
Create Date: 2026-03-09 21:20:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "032_add_economy_layer"
down_revision: Union[str, None] = "031_finalize_discovery_contracts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS economy_assessments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            discovery_proposal_id UUID NOT NULL,
            skill_run_id UUID NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            confidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            frequency_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            impact_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            cost_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            weighted_score DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            score_breakdown JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_economy_assessments_tenant_discovery_proposal UNIQUE (tenant_id, discovery_proposal_id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_economy_assessments_tenant_status ON economy_assessments (tenant_id, status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_economy_assessments_weighted_score ON economy_assessments (weighted_score DESC, updated_at DESC);")

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
            'economy_layer',
            'system',
            'NEW',
            'experimental',
            'backend/app/modules/economy_layer',
            '["/api/economy/proposals/{proposal_id}/analyze", "/api/economy/assessments/{assessment_id}", "/api/economy/assessments/{assessment_id}/queue-review"]'::jsonb,
            'discovery_layer',
            'operator+admin',
            'partial',
            'audit_required',
            'app.modules.economy_layer',
            NULL,
            'evolution_control',
            'phase_p7',
            'Economy signals influence proposal and review queue prioritization only',
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = 'economy_layer'
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM module_lifecycle WHERE module_id = 'economy_layer';")
    op.execute("DROP INDEX IF EXISTS ix_economy_assessments_weighted_score;")
    op.execute("DROP INDEX IF EXISTS ix_economy_assessments_tenant_status;")
    op.drop_table("economy_assessments")
