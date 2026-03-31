"""Add cognitive assessment tables.

Revision ID: 050_add_cognitive_assessment_tables
Revises: 049_add_skill_premium_metadata
Create Date: 2026-03-31 03:05:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "050_add_cognitive_assessment_tables"
down_revision: Union[str, None] = "049_add_skill_premium_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_assessments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            mission_id VARCHAR(120),
            normalized_intent TEXT NOT NULL,
            perception JSONB NOT NULL DEFAULT '{}'::jsonb,
            association_trace JSONB NOT NULL DEFAULT '{}'::jsonb,
            evaluation_signal JSONB NOT NULL DEFAULT '{}'::jsonb,
            recommended_skill_candidates JSONB NOT NULL DEFAULT '[]'::jsonb,
            latest_skill_run_id UUID,
            latest_feedback_at TIMESTAMPTZ,
            latest_feedback_score DOUBLE PRECISION,
            latest_feedback_success BOOLEAN,
            created_by VARCHAR(120),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cognitive_learning_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            assessment_id UUID NOT NULL REFERENCES cognitive_assessments(id) ON DELETE CASCADE,
            skill_run_id UUID NOT NULL,
            evaluation_result_id UUID,
            experience_record_id UUID,
            outcome_state VARCHAR(32) NOT NULL,
            overall_score DOUBLE PRECISION,
            success BOOLEAN NOT NULL DEFAULT false,
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_cognitive_assessments_tenant_created ON cognitive_assessments (tenant_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cognitive_learning_feedback_assessment ON cognitive_learning_feedback (assessment_id, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_cognitive_learning_feedback_assessment")
    op.execute("DROP INDEX IF EXISTS ix_cognitive_assessments_tenant_created")
    op.execute("DROP TABLE IF EXISTS cognitive_learning_feedback")
    op.execute("DROP TABLE IF EXISTS cognitive_assessments")
