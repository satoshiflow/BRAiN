"""Add purpose evaluations and routing decisions.

Revision ID: 044_add_purpose_and_routing_decisions
Revises: 043_epic2_adaptive_freeze_controls
Create Date: 2026-03-24 16:15:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "044_add_purpose_and_routing_decisions"
down_revision: Union[str, None] = "043_epic2_adaptive_freeze_controls"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purpose_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("decision_context_id", sa.String(length=160), nullable=False),
        sa.Column("purpose_profile_id", sa.String(length=120), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("purpose_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("sovereignty_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("requires_human_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("required_modifications", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("governance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("mission_id", sa.String(length=120), nullable=True),
        sa.Column("correlation_id", sa.String(length=160), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_purpose_evaluations_tenant_id"), "purpose_evaluations", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_purpose_evaluations_decision_context_id"), "purpose_evaluations", ["decision_context_id"], unique=False)
    op.create_index(op.f("ix_purpose_evaluations_purpose_profile_id"), "purpose_evaluations", ["purpose_profile_id"], unique=False)
    op.create_index(op.f("ix_purpose_evaluations_outcome"), "purpose_evaluations", ["outcome"], unique=False)
    op.create_index(op.f("ix_purpose_evaluations_mission_id"), "purpose_evaluations", ["mission_id"], unique=False)
    op.create_index(op.f("ix_purpose_evaluations_correlation_id"), "purpose_evaluations", ["correlation_id"], unique=False)

    op.create_table(
        "routing_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("decision_context_id", sa.String(length=160), nullable=False),
        sa.Column("task_profile_id", sa.String(length=160), nullable=False),
        sa.Column("purpose_evaluation_id", sa.String(length=160), nullable=True),
        sa.Column("worker_candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("filtered_candidates", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("scoring_breakdown", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("selected_worker", sa.String(length=120), nullable=True),
        sa.Column("selected_skill_or_plan", sa.String(length=200), nullable=True),
        sa.Column("strategy", sa.String(length=64), nullable=False, server_default="single_worker"),
        sa.Column("reasoning", sa.Text(), nullable=False, server_default=""),
        sa.Column("governance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("mission_id", sa.String(length=120), nullable=True),
        sa.Column("correlation_id", sa.String(length=160), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_routing_decisions_tenant_id"), "routing_decisions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_routing_decisions_decision_context_id"), "routing_decisions", ["decision_context_id"], unique=False)
    op.create_index(op.f("ix_routing_decisions_task_profile_id"), "routing_decisions", ["task_profile_id"], unique=False)
    op.create_index(op.f("ix_routing_decisions_purpose_evaluation_id"), "routing_decisions", ["purpose_evaluation_id"], unique=False)
    op.create_index(op.f("ix_routing_decisions_selected_worker"), "routing_decisions", ["selected_worker"], unique=False)
    op.create_index(op.f("ix_routing_decisions_mission_id"), "routing_decisions", ["mission_id"], unique=False)
    op.create_index(op.f("ix_routing_decisions_correlation_id"), "routing_decisions", ["correlation_id"], unique=False)
    op.create_index(
        "ix_routing_decisions_tenant_context",
        "routing_decisions",
        ["tenant_id", "decision_context_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_routing_decisions_tenant_context", table_name="routing_decisions")
    op.drop_index(op.f("ix_routing_decisions_correlation_id"), table_name="routing_decisions")
    op.drop_index(op.f("ix_routing_decisions_mission_id"), table_name="routing_decisions")
    op.drop_index(op.f("ix_routing_decisions_selected_worker"), table_name="routing_decisions")
    op.drop_index(op.f("ix_routing_decisions_purpose_evaluation_id"), table_name="routing_decisions")
    op.drop_index(op.f("ix_routing_decisions_task_profile_id"), table_name="routing_decisions")
    op.drop_index(op.f("ix_routing_decisions_decision_context_id"), table_name="routing_decisions")
    op.drop_index(op.f("ix_routing_decisions_tenant_id"), table_name="routing_decisions")
    op.drop_table("routing_decisions")

    op.drop_index(op.f("ix_purpose_evaluations_correlation_id"), table_name="purpose_evaluations")
    op.drop_index(op.f("ix_purpose_evaluations_mission_id"), table_name="purpose_evaluations")
    op.drop_index(op.f("ix_purpose_evaluations_outcome"), table_name="purpose_evaluations")
    op.drop_index(op.f("ix_purpose_evaluations_purpose_profile_id"), table_name="purpose_evaluations")
    op.drop_index(op.f("ix_purpose_evaluations_decision_context_id"), table_name="purpose_evaluations")
    op.drop_index(op.f("ix_purpose_evaluations_tenant_id"), table_name="purpose_evaluations")
    op.drop_table("purpose_evaluations")
