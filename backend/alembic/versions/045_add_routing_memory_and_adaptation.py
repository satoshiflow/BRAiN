"""Add routing memory projections and adaptation proposals.

Revision ID: 045_add_routing_memory_and_adaptation
Revises: 044_add_purpose_and_routing_decisions
Create Date: 2026-03-24 18:05:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "045_add_routing_memory_and_adaptation"
down_revision: Union[str, None] = "044_add_purpose_and_routing_decisions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "routing_memory_projections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("task_profile_id", sa.String(length=160), nullable=False),
        sa.Column("task_profile_fingerprint", sa.String(length=160), nullable=False),
        sa.Column("worker_outcome_history", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("summary_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("routing_lessons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("derived_from_runs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "task_profile_fingerprint", name="uq_routing_memory_tenant_fingerprint"),
    )
    op.create_index(op.f("ix_routing_memory_projections_tenant_id"), "routing_memory_projections", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_routing_memory_projections_task_profile_id"), "routing_memory_projections", ["task_profile_id"], unique=False)
    op.create_index(op.f("ix_routing_memory_projections_task_profile_fingerprint"), "routing_memory_projections", ["task_profile_fingerprint"], unique=False)
    op.create_index(
        "ix_routing_memory_tenant_task_profile",
        "routing_memory_projections",
        ["tenant_id", "task_profile_id"],
        unique=False,
    )

    op.create_table(
        "routing_adaptation_proposals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("task_profile_id", sa.String(length=160), nullable=False),
        sa.Column("routing_memory_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("proposed_changes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("sandbox_validated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("validation_evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("block_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_routing_adaptation_proposals_tenant_id"), "routing_adaptation_proposals", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_routing_adaptation_proposals_task_profile_id"), "routing_adaptation_proposals", ["task_profile_id"], unique=False)
    op.create_index(op.f("ix_routing_adaptation_proposals_routing_memory_id"), "routing_adaptation_proposals", ["routing_memory_id"], unique=False)
    op.create_index(op.f("ix_routing_adaptation_proposals_status"), "routing_adaptation_proposals", ["status"], unique=False)
    op.create_index(
        "ix_routing_adaptation_tenant_task_status",
        "routing_adaptation_proposals",
        ["tenant_id", "task_profile_id", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_routing_adaptation_tenant_task_status", table_name="routing_adaptation_proposals")
    op.drop_index(op.f("ix_routing_adaptation_proposals_status"), table_name="routing_adaptation_proposals")
    op.drop_index(op.f("ix_routing_adaptation_proposals_routing_memory_id"), table_name="routing_adaptation_proposals")
    op.drop_index(op.f("ix_routing_adaptation_proposals_task_profile_id"), table_name="routing_adaptation_proposals")
    op.drop_index(op.f("ix_routing_adaptation_proposals_tenant_id"), table_name="routing_adaptation_proposals")
    op.drop_table("routing_adaptation_proposals")

    op.drop_index("ix_routing_memory_tenant_task_profile", table_name="routing_memory_projections")
    op.drop_index(op.f("ix_routing_memory_projections_task_profile_fingerprint"), table_name="routing_memory_projections")
    op.drop_index(op.f("ix_routing_memory_projections_task_profile_id"), table_name="routing_memory_projections")
    op.drop_index(op.f("ix_routing_memory_projections_tenant_id"), table_name="routing_memory_projections")
    op.drop_table("routing_memory_projections")
