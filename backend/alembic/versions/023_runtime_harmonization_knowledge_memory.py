"""Add runtime bridge fields, knowledge layer, and builder skill seeds.

Revision ID: 023_runtime_harmonization_knowledge_memory
Revises: 022_add_agent_delegations
Create Date: 2026-03-08 21:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "023_runtime_harmonization_knowledge_memory"
down_revision: Union[str, None] = "022_add_agent_delegations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS tasks ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(64);")
    op.execute("ALTER TABLE IF EXISTS tasks ADD COLUMN IF NOT EXISTS mission_id VARCHAR(120);")
    op.execute("ALTER TABLE IF EXISTS tasks ADD COLUMN IF NOT EXISTS skill_run_id UUID;")
    op.execute("ALTER TABLE IF EXISTS tasks ADD COLUMN IF NOT EXISTS correlation_id VARCHAR(160);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_tenant_id ON tasks (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_mission_id ON tasks (mission_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_skill_run_id ON tasks (skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_correlation_id ON tasks (correlation_id);")

    op.execute("ALTER TABLE IF EXISTS memory_entries ADD COLUMN IF NOT EXISTS skill_run_id VARCHAR(64);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_memory_entries_skill_run ON memory_entries (skill_run_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            type VARCHAR(40) NOT NULL,
            title VARCHAR(255) NOT NULL,
            source VARCHAR(120) NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            owner VARCHAR(120) NOT NULL,
            module VARCHAR(120) NOT NULL,
            tags JSONB NOT NULL DEFAULT '[]',
            content TEXT NOT NULL,
            provenance_refs JSONB NOT NULL DEFAULT '[]',
            valid_until TIMESTAMPTZ,
            superseded_by_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_items_tenant_type ON knowledge_items (tenant_id, type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_items_tenant_module ON knowledge_items (tenant_id, module);")

    op.execute(
        """
        INSERT INTO skill_definitions (
            tenant_id, owner_scope, skill_key, version, status, purpose,
            input_schema, output_schema, required_capabilities, optional_capabilities,
            constraints, quality_profile, fallback_policy, evaluation_criteria,
            risk_tier, policy_pack_ref, trust_tier_min, checksum_sha256,
            created_by, updated_by, approved_by, approved_at
        )
        SELECT NULL, 'system', seeded.skill_key, 1, 'active', seeded.purpose,
               '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, '[]'::jsonb,
               '{}'::jsonb, 'standard', 'allowed', '{}'::jsonb,
               'medium', 'default', 'internal', md5(seeded.skill_key || seeded.purpose),
               'system_seed', 'system_seed', 'system_seed', NOW()
        FROM (
            VALUES
                ('builder.course_factory.generate', 'Governed course factory orchestration marker'),
                ('builder.webgenesis.generate', 'Governed webgenesis source generation marker'),
                ('builder.webgenesis.build', 'Governed webgenesis build marker'),
                ('builder.webgenesis.deploy', 'Governed webgenesis deploy marker'),
                ('builder.webgenesis.rollback', 'Governed webgenesis rollback marker')
        ) AS seeded(skill_key, purpose)
        WHERE NOT EXISTS (
            SELECT 1 FROM skill_definitions existing
            WHERE existing.owner_scope = 'system'
              AND existing.skill_key = seeded.skill_key
              AND existing.version = 1
        );
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM skill_definitions WHERE owner_scope = 'system' AND skill_key IN ('builder.course_factory.generate','builder.webgenesis.generate','builder.webgenesis.build','builder.webgenesis.deploy','builder.webgenesis.rollback');")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_items_tenant_module;")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_items_tenant_type;")
    op.drop_table("knowledge_items")
    op.execute("DROP INDEX IF EXISTS idx_memory_entries_skill_run;")
    op.execute("ALTER TABLE IF EXISTS memory_entries DROP COLUMN IF EXISTS skill_run_id;")
    op.execute("DROP INDEX IF EXISTS idx_tasks_correlation_id;")
    op.execute("DROP INDEX IF EXISTS idx_tasks_skill_run_id;")
    op.execute("DROP INDEX IF EXISTS idx_tasks_mission_id;")
    op.execute("DROP INDEX IF EXISTS idx_tasks_tenant_id;")
    op.execute("ALTER TABLE IF EXISTS tasks DROP COLUMN IF EXISTS correlation_id;")
    op.execute("ALTER TABLE IF EXISTS tasks DROP COLUMN IF EXISTS skill_run_id;")
    op.execute("ALTER TABLE IF EXISTS tasks DROP COLUMN IF EXISTS mission_id;")
    op.execute("ALTER TABLE IF EXISTS tasks DROP COLUMN IF EXISTS tenant_id;")
