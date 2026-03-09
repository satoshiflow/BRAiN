"""Finalize discovery contracts for thresholds and prioritization.

Revision ID: 031_finalize_discovery_contracts
Revises: 030_add_discovery_layer
Create Date: 2026-03-09 21:10:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "031_finalize_discovery_contracts"
down_revision: Union[str, None] = "030_add_discovery_layer"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE discovery_skill_proposals ADD COLUMN IF NOT EXISTS dedup_key VARCHAR(255) NOT NULL DEFAULT '';")
    op.execute("ALTER TABLE discovery_skill_proposals ADD COLUMN IF NOT EXISTS evidence_score DOUBLE PRECISION NOT NULL DEFAULT 0.0;")
    op.execute("ALTER TABLE discovery_skill_proposals ADD COLUMN IF NOT EXISTS priority_score DOUBLE PRECISION NOT NULL DEFAULT 0.0;")
    op.execute("UPDATE discovery_skill_proposals SET dedup_key = CONCAT(skill_run_id::text, ':', target_skill_key) WHERE dedup_key = '';")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_discovery_skill_proposals_tenant_dedup "
        "ON discovery_skill_proposals (tenant_id, dedup_key);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_discovery_skill_proposals_priority "
        "ON discovery_skill_proposals (priority_score DESC, updated_at DESC);"
    )

    op.execute(
        """
        UPDATE module_lifecycle
        SET active_routes = '["/api/discovery/skill-runs/{skill_run_id}/analyze", "/api/discovery/proposals", "/api/discovery/proposals/{proposal_id}/queue-review"]'::jsonb,
            notes = 'Proposal-only discovery with explicit evidence thresholds and prioritization'
        WHERE module_id = 'discovery_layer';
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_discovery_skill_proposals_priority;")
    op.execute("DROP INDEX IF EXISTS uq_discovery_skill_proposals_tenant_dedup;")
    op.execute("ALTER TABLE discovery_skill_proposals DROP COLUMN IF EXISTS priority_score;")
    op.execute("ALTER TABLE discovery_skill_proposals DROP COLUMN IF EXISTS evidence_score;")
    op.execute("ALTER TABLE discovery_skill_proposals DROP COLUMN IF EXISTS dedup_key;")
