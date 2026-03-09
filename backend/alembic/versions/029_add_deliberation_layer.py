"""Add deliberation layer persistence.

Revision ID: 029_add_deliberation_layer
Revises: 028_add_consolidation_and_evolution_control
Create Date: 2026-03-09 18:45:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "029_add_deliberation_layer"
down_revision: Union[str, None] = "028_add_consolidation_and_evolution_control"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS deliberation_summaries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            mission_id VARCHAR(120) NOT NULL,
            alternatives JSONB NOT NULL DEFAULT '[]',
            rationale_summary TEXT NOT NULL,
            uncertainty DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            open_tensions JSONB NOT NULL DEFAULT '[]',
            evidence JSONB NOT NULL DEFAULT '{}',
            created_by VARCHAR(120) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_deliberation_summaries_tenant_mission ON deliberation_summaries (tenant_id, mission_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS mission_tensions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64) NOT NULL,
            mission_id VARCHAR(120) NOT NULL,
            hypothesis TEXT NOT NULL,
            perspective TEXT NOT NULL,
            tension TEXT NOT NULL,
            status VARCHAR(24) NOT NULL DEFAULT 'open',
            evidence JSONB NOT NULL DEFAULT '{}',
            created_by VARCHAR(120) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_mission_tensions_tenant_mission ON mission_tensions (tenant_id, mission_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_mission_tensions_status ON mission_tensions (status);")

    op.execute(
        """
        INSERT INTO module_lifecycle (
            module_id, owner_scope, classification, lifecycle_status, canonical_path,
            active_routes, data_owner, auth_surface, event_contract_status, audit_policy,
            migration_adapter, kill_switch, replacement_target, sunset_phase, notes
        )
        SELECT
            'deliberation_layer',
            'system',
            'NEW',
            'experimental',
            'backend/app/modules/deliberation_layer',
            '["/api/deliberation/missions/{mission_id}/summaries", "/api/deliberation/missions/{mission_id}/tensions"]'::jsonb,
            'missions',
            'operator+admin',
            'partial',
            'audit_required',
            'app.modules.deliberation_layer',
            NULL,
            NULL,
            'phase_p4',
            'Bounded mission deliberation artifacts without chain-of-thought dumps'
        WHERE NOT EXISTS (
            SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = 'deliberation_layer'
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM module_lifecycle WHERE module_id = 'deliberation_layer';")
    op.execute("DROP INDEX IF EXISTS ix_mission_tensions_status;")
    op.execute("DROP INDEX IF EXISTS ix_mission_tensions_tenant_mission;")
    op.drop_table("mission_tensions")
    op.execute("DROP INDEX IF EXISTS ix_deliberation_summaries_tenant_mission;")
    op.drop_table("deliberation_summaries")
