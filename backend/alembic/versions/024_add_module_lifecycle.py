"""Add module lifecycle control plane.

Revision ID: 024_add_module_lifecycle
Revises: 023_runtime_harmonization_knowledge_memory
Create Date: 2026-03-08 21:20:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "024_add_module_lifecycle"
down_revision: Union[str, None] = "023_runtime_harmonization_knowledge_memory"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS module_lifecycle (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            module_id VARCHAR(120) NOT NULL UNIQUE,
            owner_scope VARCHAR(16) NOT NULL DEFAULT 'system',
            classification VARCHAR(20) NOT NULL,
            lifecycle_status VARCHAR(20) NOT NULL,
            canonical_path VARCHAR(255) NOT NULL,
            active_routes JSONB NOT NULL DEFAULT '[]',
            data_owner VARCHAR(120) NOT NULL,
            auth_surface TEXT NOT NULL,
            event_contract_status VARCHAR(32) NOT NULL,
            audit_policy VARCHAR(120) NOT NULL,
            migration_adapter VARCHAR(255),
            kill_switch VARCHAR(120),
            replacement_target VARCHAR(120),
            sunset_phase VARCHAR(64),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_module_lifecycle_status_classification ON module_lifecycle (lifecycle_status, classification);")
    op.execute(
        """
        INSERT INTO module_lifecycle (
            id, module_id, owner_scope, classification, lifecycle_status, canonical_path,
            active_routes, data_owner, auth_surface, event_contract_status, audit_policy,
            migration_adapter, kill_switch, replacement_target, sunset_phase, notes,
            created_at, updated_at
        )
        SELECT gen_random_uuid(), seeded.module_id, 'system', seeded.classification, seeded.lifecycle_status, seeded.canonical_path,
               seeded.active_routes::jsonb, seeded.data_owner, seeded.auth_surface, seeded.event_contract_status, seeded.audit_policy,
               seeded.migration_adapter, seeded.kill_switch, seeded.replacement_target, seeded.sunset_phase, seeded.notes,
               NOW(), NOW()
        FROM (
            VALUES
                ('course_factory', 'CONSOLIDATE', 'stable', 'backend/app/modules/course_factory', '["/api/course-factory/generate","/api/course-factory/enhance"]', 'skillrun', 'operator', 'partial', 'audit_required', 'app.modules.course_factory', NULL, NULL, 'epic11', 'Builder wrapper over SkillRun'),
                ('webgenesis', 'CONSOLIDATE', 'stable', 'backend/app/modules/webgenesis', '["/api/webgenesis/{site_id}/generate","/api/webgenesis/{site_id}/build","/api/webgenesis/{site_id}/deploy","/api/webgenesis/{site_id}/rollback"]', 'skillrun', 'operator+dmz', 'partial', 'audit_required', 'app.modules.webgenesis', NULL, NULL, 'epic11', 'Builder wrapper over SkillRun')
        ) AS seeded(module_id, classification, lifecycle_status, canonical_path, active_routes, data_owner, auth_surface, event_contract_status, audit_policy, migration_adapter, kill_switch, replacement_target, sunset_phase, notes)
        WHERE NOT EXISTS (SELECT 1 FROM module_lifecycle existing WHERE existing.module_id = seeded.module_id);
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM module_lifecycle WHERE module_id IN ('course_factory', 'webgenesis');")
    op.execute("DROP INDEX IF EXISTS ix_module_lifecycle_status_classification;")
    op.drop_table("module_lifecycle")
