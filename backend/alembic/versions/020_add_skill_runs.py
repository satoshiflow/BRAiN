"""Add skill run execution table.

Revision ID: 020_add_skill_runs
Revises: 019_add_skill_capability_registries
Create Date: 2026-03-08 16:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "020_add_skill_runs"
down_revision: Union[str, None] = "019_add_skill_capability_registries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            skill_key VARCHAR(120) NOT NULL,
            skill_version INTEGER NOT NULL,
            state VARCHAR(32) NOT NULL DEFAULT 'queued',
            input_payload JSONB NOT NULL DEFAULT '{}',
            plan_snapshot JSONB NOT NULL DEFAULT '{}',
            provider_selection_snapshot JSONB NOT NULL DEFAULT '{}',
            requested_by VARCHAR(120) NOT NULL,
            requested_by_type VARCHAR(32) NOT NULL,
            trigger_type VARCHAR(32) NOT NULL DEFAULT 'api',
            policy_decision JSONB NOT NULL DEFAULT '{}',
            risk_tier VARCHAR(32) NOT NULL DEFAULT 'medium',
            correlation_id VARCHAR(160) NOT NULL,
            causation_id VARCHAR(160),
            idempotency_key VARCHAR(160) NOT NULL,
            mission_id VARCHAR(120),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            deadline_at TIMESTAMPTZ,
            retry_count INTEGER NOT NULL DEFAULT 0,
            cost_estimate DOUBLE PRECISION,
            cost_actual DOUBLE PRECISION,
            output_payload JSONB NOT NULL DEFAULT '{}',
            evaluation_summary JSONB NOT NULL DEFAULT '{}',
            failure_code VARCHAR(40),
            failure_reason_sanitized TEXT
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_skill_runs_skill_key ON skill_runs (skill_key);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_skill_runs_state ON skill_runs (state);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_skill_runs_correlation_id ON skill_runs (correlation_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_skill_runs_tenant_skill_state ON skill_runs (tenant_id, skill_key, state);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_skill_runs_idempotency ON skill_runs (tenant_id, requested_by, idempotency_key);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_skill_runs_idempotency;")
    op.execute("DROP INDEX IF EXISTS ix_skill_runs_tenant_skill_state;")
    op.execute("DROP INDEX IF EXISTS ix_skill_runs_correlation_id;")
    op.execute("DROP INDEX IF EXISTS ix_skill_runs_state;")
    op.execute("DROP INDEX IF EXISTS ix_skill_runs_skill_key;")
    op.drop_table("skill_runs")
