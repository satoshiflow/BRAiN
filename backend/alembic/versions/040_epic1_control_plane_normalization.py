"""Epic 1 control-plane normalization.

Revision ID: 040_epic1_control_plane_normalization
Revises: 039_add_axe_worker_runs
Create Date: 2026-03-22 11:00:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "040_epic1_control_plane_normalization"
down_revision: Union[str, None] = "039_add_axe_worker_runs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("skill_runs", sa.Column("policy_decision_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("skill_runs", sa.Column("policy_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")))
    op.add_column("skill_runs", sa.Column("state_sequence", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("skill_runs", sa.Column("state_changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("skill_runs", sa.Column("input_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("skill_runs", sa.Column("output_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("skill_runs", sa.Column("evidence_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))

    op.add_column("evaluation_results", sa.Column("revision_of_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("evaluation_results", sa.Column("evidence_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("evaluation_results", sa.Column("review_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("evaluation_results", sa.Column("comparison_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))

    op.add_column("skill_definitions", sa.Column("builder_role", sa.String(length=64), nullable=False, server_default="manual"))
    op.add_column("skill_definitions", sa.Column("definition_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("skill_definitions", sa.Column("example_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("skill_definitions", sa.Column("builder_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))

    op.add_column("capability_definitions", sa.Column("contract_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))
    op.add_column("capability_definitions", sa.Column("adapter_test_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")))

    op.create_table(
        "control_plane_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=160), nullable=False),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("correlation_id", sa.String(length=160), nullable=True),
        sa.Column("mission_id", sa.String(length=120), nullable=True),
        sa.Column("actor_id", sa.String(length=120), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("audit_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_control_plane_events_tenant_id"), "control_plane_events", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_control_plane_events_entity_type"), "control_plane_events", ["entity_type"], unique=False)
    op.create_index(op.f("ix_control_plane_events_entity_id"), "control_plane_events", ["entity_id"], unique=False)
    op.create_index(op.f("ix_control_plane_events_event_type"), "control_plane_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_control_plane_events_correlation_id"), "control_plane_events", ["correlation_id"], unique=False)

    op.create_table(
        "skill_run_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("skill_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("transition_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("from_state", sa.String(length=32), nullable=True),
        sa.Column("to_state", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("correlation_id", sa.String(length=160), nullable=True),
        sa.Column("actor_id", sa.String(length=120), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_skill_run_transitions_skill_run_id"), "skill_run_transitions", ["skill_run_id"], unique=False)
    op.create_index(op.f("ix_skill_run_transitions_tenant_id"), "skill_run_transitions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_skill_run_transitions_to_state"), "skill_run_transitions", ["to_state"], unique=False)
    op.create_index(op.f("ix_skill_run_transitions_correlation_id"), "skill_run_transitions", ["correlation_id"], unique=False)

    op.create_table(
        "provider_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("owner_scope", sa.String(length=16), nullable=False, server_default="system"),
        sa.Column("capability_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("capability_key", sa.String(length=120), nullable=False),
        sa.Column("capability_version", sa.Integer(), nullable=False),
        sa.Column("provider_key", sa.String(length=120), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False, server_default="service"),
        sa.Column("adapter_key", sa.String(length=120), nullable=False),
        sa.Column("endpoint_ref", sa.String(length=255), nullable=False),
        sa.Column("model_or_tool_ref", sa.String(length=255), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("cost_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("sla_profile", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("policy_constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("definition_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("evidence_artifact_refs", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("updated_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_bindings_tenant_id"), "provider_bindings", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_provider_bindings_capability_key"), "provider_bindings", ["capability_key"], unique=False)
    op.create_index(op.f("ix_provider_bindings_status"), "provider_bindings", ["status"], unique=False)
    op.create_index("ix_provider_bindings_capability_status_priority", "provider_bindings", ["capability_key", "capability_version", "status", "priority"], unique=False)
    op.create_index("ux_provider_bindings_scope_provider", "provider_bindings", ["tenant_id", "capability_key", "capability_version", "provider_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ux_provider_bindings_scope_provider", table_name="provider_bindings")
    op.drop_index("ix_provider_bindings_capability_status_priority", table_name="provider_bindings")
    op.drop_index(op.f("ix_provider_bindings_status"), table_name="provider_bindings")
    op.drop_index(op.f("ix_provider_bindings_capability_key"), table_name="provider_bindings")
    op.drop_index(op.f("ix_provider_bindings_tenant_id"), table_name="provider_bindings")
    op.drop_table("provider_bindings")

    op.drop_index(op.f("ix_skill_run_transitions_correlation_id"), table_name="skill_run_transitions")
    op.drop_index(op.f("ix_skill_run_transitions_to_state"), table_name="skill_run_transitions")
    op.drop_index(op.f("ix_skill_run_transitions_tenant_id"), table_name="skill_run_transitions")
    op.drop_index(op.f("ix_skill_run_transitions_skill_run_id"), table_name="skill_run_transitions")
    op.drop_table("skill_run_transitions")

    op.drop_index(op.f("ix_control_plane_events_correlation_id"), table_name="control_plane_events")
    op.drop_index(op.f("ix_control_plane_events_event_type"), table_name="control_plane_events")
    op.drop_index(op.f("ix_control_plane_events_entity_id"), table_name="control_plane_events")
    op.drop_index(op.f("ix_control_plane_events_entity_type"), table_name="control_plane_events")
    op.drop_index(op.f("ix_control_plane_events_tenant_id"), table_name="control_plane_events")
    op.drop_table("control_plane_events")

    op.drop_column("capability_definitions", "adapter_test_artifact_refs")
    op.drop_column("capability_definitions", "contract_artifact_refs")
    op.drop_column("skill_definitions", "builder_artifact_refs")
    op.drop_column("skill_definitions", "example_artifact_refs")
    op.drop_column("skill_definitions", "definition_artifact_refs")
    op.drop_column("skill_definitions", "builder_role")
    op.drop_column("evaluation_results", "comparison_artifact_refs")
    op.drop_column("evaluation_results", "review_artifact_refs")
    op.drop_column("evaluation_results", "evidence_artifact_refs")
    op.drop_column("evaluation_results", "revision_of_id")
    op.drop_column("skill_runs", "evidence_artifact_refs")
    op.drop_column("skill_runs", "output_artifact_refs")
    op.drop_column("skill_runs", "input_artifact_refs")
    op.drop_column("skill_runs", "state_changed_at")
    op.drop_column("skill_runs", "state_sequence")
    op.drop_column("skill_runs", "policy_snapshot")
    op.drop_column("skill_runs", "policy_decision_id")
