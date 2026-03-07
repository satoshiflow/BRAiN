"""Add persistence tables for stabilization layer modules.

Revision ID: 017_add_stabilization_layer_persistence
Revises: 016_auth_governance_tables
Create Date: 2026-03-06 15:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "017_add_stabilization_layer_persistence"
down_revision: Union[str, None] = "016_auth_governance_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "immune_orchestrator_signals",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("entity", sa.String(length=256), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("blast_radius", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("recurrence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_immune_orchestrator_signals_type", "immune_orchestrator_signals", ["type"])
    op.create_index("ix_immune_orchestrator_signals_source", "immune_orchestrator_signals", ["source"])
    op.create_index("ix_immune_orchestrator_signals_severity", "immune_orchestrator_signals", ["severity"])
    op.create_index("ix_immune_orchestrator_signals_entity", "immune_orchestrator_signals", ["entity"])
    op.create_index("ix_immune_orchestrator_signals_correlation_id", "immune_orchestrator_signals", ["correlation_id"])

    op.create_table(
        "immune_orchestrator_decisions",
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("signal_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requires_governance_hook", sa.String(length=5), nullable=False, server_default="false"),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("decision_id"),
    )
    op.create_index("ix_immune_orchestrator_decisions_signal_id", "immune_orchestrator_decisions", ["signal_id"])
    op.create_index("ix_immune_orchestrator_decisions_action", "immune_orchestrator_decisions", ["action"])
    op.create_index("ix_immune_orchestrator_decisions_correlation_id", "immune_orchestrator_decisions", ["correlation_id"])

    op.create_table(
        "immune_orchestrator_audit",
        sa.Column("audit_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("resource_id", sa.String(length=256), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_immune_orchestrator_audit_event_type", "immune_orchestrator_audit", ["event_type"])
    op.create_index("ix_immune_orchestrator_audit_action", "immune_orchestrator_audit", ["action"])
    op.create_index("ix_immune_orchestrator_audit_resource_id", "immune_orchestrator_audit", ["resource_id"])
    op.create_index("ix_immune_orchestrator_audit_correlation_id", "immune_orchestrator_audit", ["correlation_id"])

    op.create_table(
        "recovery_policy_requests",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.String(length=256), nullable=False),
        sa.Column("failure_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recurrence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recovery_policy_requests_source", "recovery_policy_requests", ["source"])
    op.create_index("ix_recovery_policy_requests_entity_id", "recovery_policy_requests", ["entity_id"])
    op.create_index("ix_recovery_policy_requests_failure_type", "recovery_policy_requests", ["failure_type"])
    op.create_index("ix_recovery_policy_requests_severity", "recovery_policy_requests", ["severity"])
    op.create_index("ix_recovery_policy_requests_correlation_id", "recovery_policy_requests", ["correlation_id"])

    op.create_table(
        "recovery_policy_decisions",
        sa.Column("decision_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requires_governance_hook", sa.String(length=5), nullable=False, server_default="false"),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("decision_id"),
    )
    op.create_index("ix_recovery_policy_decisions_request_id", "recovery_policy_decisions", ["request_id"])
    op.create_index("ix_recovery_policy_decisions_action", "recovery_policy_decisions", ["action"])
    op.create_index("ix_recovery_policy_decisions_correlation_id", "recovery_policy_decisions", ["correlation_id"])

    op.create_table(
        "recovery_policy_audit",
        sa.Column("audit_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_recovery_policy_audit_event_type", "recovery_policy_audit", ["event_type"])
    op.create_index("ix_recovery_policy_audit_action", "recovery_policy_audit", ["action"])
    op.create_index("ix_recovery_policy_audit_request_id", "recovery_policy_audit", ["request_id"])
    op.create_index("ix_recovery_policy_audit_correlation_id", "recovery_policy_audit", ["correlation_id"])

    op.create_table(
        "genetic_integrity_snapshots",
        sa.Column("record_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("parent_snapshot", sa.Integer(), nullable=True),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("parent_hash", sa.String(length=128), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("record_id"),
    )
    op.create_index("ix_genetic_integrity_snapshots_agent_id", "genetic_integrity_snapshots", ["agent_id"])
    op.create_index("ix_genetic_integrity_snapshots_snapshot_version", "genetic_integrity_snapshots", ["snapshot_version"])
    op.create_index("ix_genetic_integrity_snapshots_correlation_id", "genetic_integrity_snapshots", ["correlation_id"])

    op.create_table(
        "genetic_integrity_mutations",
        sa.Column("audit_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("from_version", sa.Integer(), nullable=False),
        sa.Column("to_version", sa.Integer(), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("mutation", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("requires_governance_hook", sa.String(length=5), nullable=False, server_default="false"),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_genetic_integrity_mutations_agent_id", "genetic_integrity_mutations", ["agent_id"])
    op.create_index("ix_genetic_integrity_mutations_correlation_id", "genetic_integrity_mutations", ["correlation_id"])

    op.create_table(
        "genetic_integrity_audit",
        sa.Column("audit_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("resource_id", sa.String(length=256), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_genetic_integrity_audit_event_type", "genetic_integrity_audit", ["event_type"])
    op.create_index("ix_genetic_integrity_audit_action", "genetic_integrity_audit", ["action"])
    op.create_index("ix_genetic_integrity_audit_resource_id", "genetic_integrity_audit", ["resource_id"])


def downgrade() -> None:
    op.drop_index("ix_genetic_integrity_audit_resource_id", table_name="genetic_integrity_audit")
    op.drop_index("ix_genetic_integrity_audit_action", table_name="genetic_integrity_audit")
    op.drop_index("ix_genetic_integrity_audit_event_type", table_name="genetic_integrity_audit")
    op.drop_table("genetic_integrity_audit")

    op.drop_index("ix_genetic_integrity_mutations_correlation_id", table_name="genetic_integrity_mutations")
    op.drop_index("ix_genetic_integrity_mutations_agent_id", table_name="genetic_integrity_mutations")
    op.drop_table("genetic_integrity_mutations")

    op.drop_index("ix_genetic_integrity_snapshots_correlation_id", table_name="genetic_integrity_snapshots")
    op.drop_index("ix_genetic_integrity_snapshots_snapshot_version", table_name="genetic_integrity_snapshots")
    op.drop_index("ix_genetic_integrity_snapshots_agent_id", table_name="genetic_integrity_snapshots")
    op.drop_table("genetic_integrity_snapshots")

    op.drop_index("ix_recovery_policy_audit_correlation_id", table_name="recovery_policy_audit")
    op.drop_index("ix_recovery_policy_audit_request_id", table_name="recovery_policy_audit")
    op.drop_index("ix_recovery_policy_audit_action", table_name="recovery_policy_audit")
    op.drop_index("ix_recovery_policy_audit_event_type", table_name="recovery_policy_audit")
    op.drop_table("recovery_policy_audit")

    op.drop_index("ix_recovery_policy_decisions_correlation_id", table_name="recovery_policy_decisions")
    op.drop_index("ix_recovery_policy_decisions_action", table_name="recovery_policy_decisions")
    op.drop_index("ix_recovery_policy_decisions_request_id", table_name="recovery_policy_decisions")
    op.drop_table("recovery_policy_decisions")

    op.drop_index("ix_recovery_policy_requests_correlation_id", table_name="recovery_policy_requests")
    op.drop_index("ix_recovery_policy_requests_severity", table_name="recovery_policy_requests")
    op.drop_index("ix_recovery_policy_requests_failure_type", table_name="recovery_policy_requests")
    op.drop_index("ix_recovery_policy_requests_entity_id", table_name="recovery_policy_requests")
    op.drop_index("ix_recovery_policy_requests_source", table_name="recovery_policy_requests")
    op.drop_table("recovery_policy_requests")

    op.drop_index("ix_immune_orchestrator_audit_correlation_id", table_name="immune_orchestrator_audit")
    op.drop_index("ix_immune_orchestrator_audit_resource_id", table_name="immune_orchestrator_audit")
    op.drop_index("ix_immune_orchestrator_audit_action", table_name="immune_orchestrator_audit")
    op.drop_index("ix_immune_orchestrator_audit_event_type", table_name="immune_orchestrator_audit")
    op.drop_table("immune_orchestrator_audit")

    op.drop_index("ix_immune_orchestrator_decisions_correlation_id", table_name="immune_orchestrator_decisions")
    op.drop_index("ix_immune_orchestrator_decisions_action", table_name="immune_orchestrator_decisions")
    op.drop_index("ix_immune_orchestrator_decisions_signal_id", table_name="immune_orchestrator_decisions")
    op.drop_table("immune_orchestrator_decisions")

    op.drop_index("ix_immune_orchestrator_signals_correlation_id", table_name="immune_orchestrator_signals")
    op.drop_index("ix_immune_orchestrator_signals_entity", table_name="immune_orchestrator_signals")
    op.drop_index("ix_immune_orchestrator_signals_severity", table_name="immune_orchestrator_signals")
    op.drop_index("ix_immune_orchestrator_signals_source", table_name="immune_orchestrator_signals")
    op.drop_index("ix_immune_orchestrator_signals_type", table_name="immune_orchestrator_signals")
    op.drop_table("immune_orchestrator_signals")
