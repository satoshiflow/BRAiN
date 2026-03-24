"""Add experience layer persistence and lifecycle seed.

Revision ID: 025_add_experience_layer
Revises: 024_add_module_lifecycle
Create Date: 2026-03-09 16:10:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "025_add_experience_layer"
down_revision: Union[str, None] = "024_add_module_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS experience_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            skill_run_id UUID NOT NULL,
            idempotency_key VARCHAR(160) NOT NULL UNIQUE,
            state VARCHAR(32) NOT NULL,
            failure_code VARCHAR(40),
            summary TEXT NOT NULL,
            evaluation_summary JSONB NOT NULL DEFAULT '{}',
            signals JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_experience_records_tenant_run ON experience_records (tenant_id, skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_experience_records_skill_run_id ON experience_records (skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_experience_records_state ON experience_records (state);")

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
            'experience_layer',
            'system',
            'KEEP_IN_CORE',
            'stable',
            'backend/app/modules/experience_layer',
            '["/api/experience/skill-runs/{skill_run_id}/ingest"]'::jsonb,
            'skillrun',
            'operator',
            'partial',
            'audit_required',
            'app.modules.experience_layer',
            NULL,
            NULL,
            'phase_p1',
            'Experience layer MVP anchored to SkillRun',
            NOW(),
            NOW()
        WHERE NOT EXISTS (
            SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = 'experience_layer'
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM module_lifecycle WHERE module_id = 'experience_layer';")
    op.execute("DROP INDEX IF EXISTS ix_experience_records_state;")
    op.execute("DROP INDEX IF EXISTS ix_experience_records_skill_run_id;")
    op.execute("DROP INDEX IF EXISTS ix_experience_records_tenant_run;")
    op.drop_table("experience_records")
