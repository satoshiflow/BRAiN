"""Add evaluation results and optimizer recommendation tables.

Revision ID: 021_add_evaluation_and_optimizer_tables
Revises: 020_add_skill_runs
Create Date: 2026-03-08 17:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "021_add_evaluation_and_optimizer_tables"
down_revision: Union[str, None] = "020_add_skill_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS evaluation_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            skill_run_id UUID NOT NULL,
            skill_key VARCHAR(120) NOT NULL,
            skill_version INTEGER NOT NULL,
            evaluator_type VARCHAR(32) NOT NULL DEFAULT 'rule',
            status VARCHAR(32) NOT NULL DEFAULT 'completed',
            overall_score DOUBLE PRECISION,
            dimension_scores JSONB NOT NULL DEFAULT '{}',
            passed BOOLEAN NOT NULL DEFAULT TRUE,
            criteria_snapshot JSONB NOT NULL DEFAULT '{}',
            findings JSONB NOT NULL DEFAULT '{}',
            recommendations JSONB NOT NULL DEFAULT '{}',
            metrics_summary JSONB NOT NULL DEFAULT '{}',
            provider_selection_snapshot JSONB NOT NULL DEFAULT '{}',
            error_classification VARCHAR(32),
            policy_compliance VARCHAR(32) NOT NULL DEFAULT 'unknown',
            policy_violations JSONB NOT NULL DEFAULT '[]',
            correlation_id VARCHAR(160),
            evaluation_revision INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            created_by VARCHAR(120) NOT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluation_results_skill_run_id ON evaluation_results (skill_run_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluation_results_run_status ON evaluation_results (skill_run_id, status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluation_results_skill_version ON evaluation_results (tenant_id, skill_key, skill_version);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_evaluation_results_correlation_id ON evaluation_results (correlation_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_optimizer_recommendations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            skill_key VARCHAR(120) NOT NULL,
            skill_version INTEGER NOT NULL,
            recommendation_type VARCHAR(64) NOT NULL,
            confidence DOUBLE PRECISION NOT NULL DEFAULT 0.0,
            status VARCHAR(32) NOT NULL DEFAULT 'open',
            rationale TEXT NOT NULL,
            evidence JSONB NOT NULL DEFAULT '{}',
            source_snapshot JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_by VARCHAR(120) NOT NULL DEFAULT 'skill_optimizer'
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_skill_optimizer_recommendations_skill ON skill_optimizer_recommendations (tenant_id, skill_key, skill_version);")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_skill_optimizer_recommendations_skill;")
    op.drop_table("skill_optimizer_recommendations")
    op.execute("DROP INDEX IF EXISTS ix_evaluation_results_correlation_id;")
    op.execute("DROP INDEX IF EXISTS ix_evaluation_results_skill_version;")
    op.execute("DROP INDEX IF EXISTS ix_evaluation_results_run_status;")
    op.execute("DROP INDEX IF EXISTS ix_evaluation_results_skill_run_id;")
    op.drop_table("evaluation_results")
