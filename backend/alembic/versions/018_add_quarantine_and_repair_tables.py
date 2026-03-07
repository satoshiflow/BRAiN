"""Add genetic quarantine and OpenCode repair loop tables.

Revision ID: 018_add_quarantine_and_repair_tables
Revises: 017_add_stabilization_layer_persistence
Create Date: 2026-03-07 00:35:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "018_add_quarantine_and_repair_tables"
down_revision: Union[str, None] = "017_add_stabilization_layer_persistence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "genetic_quarantine_records",
        sa.Column("quarantine_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("snapshot_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("previous_state", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("quarantine_id"),
    )
    op.create_index("ix_genetic_quarantine_records_agent_id", "genetic_quarantine_records", ["agent_id"])
    op.create_index("ix_genetic_quarantine_records_snapshot_version", "genetic_quarantine_records", ["snapshot_version"])
    op.create_index("ix_genetic_quarantine_records_state", "genetic_quarantine_records", ["state"])
    op.create_index("ix_genetic_quarantine_records_severity", "genetic_quarantine_records", ["severity"])
    op.create_index("ix_genetic_quarantine_records_source", "genetic_quarantine_records", ["source"])
    op.create_index("ix_genetic_quarantine_records_correlation_id", "genetic_quarantine_records", ["correlation_id"])

    op.create_table(
        "genetic_quarantine_audit",
        sa.Column("audit_id", sa.String(length=128), nullable=False),
        sa.Column("quarantine_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_genetic_quarantine_audit_quarantine_id", "genetic_quarantine_audit", ["quarantine_id"])
    op.create_index("ix_genetic_quarantine_audit_event_type", "genetic_quarantine_audit", ["event_type"])
    op.create_index("ix_genetic_quarantine_audit_action", "genetic_quarantine_audit", ["action"])
    op.create_index("ix_genetic_quarantine_audit_correlation_id", "genetic_quarantine_audit", ["correlation_id"])

    op.create_table(
        "opencode_repair_tickets",
        sa.Column("ticket_id", sa.String(length=128), nullable=False),
        sa.Column("source_module", sa.String(length=128), nullable=False),
        sa.Column("source_event_type", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("governance_required", sa.Boolean(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("ticket_id"),
    )
    op.create_index("ix_opencode_repair_tickets_source_module", "opencode_repair_tickets", ["source_module"])
    op.create_index("ix_opencode_repair_tickets_source_event_type", "opencode_repair_tickets", ["source_event_type"])
    op.create_index("ix_opencode_repair_tickets_severity", "opencode_repair_tickets", ["severity"])
    op.create_index("ix_opencode_repair_tickets_status", "opencode_repair_tickets", ["status"])
    op.create_index("ix_opencode_repair_tickets_correlation_id", "opencode_repair_tickets", ["correlation_id"])

    op.create_table(
        "opencode_repair_audit",
        sa.Column("audit_id", sa.String(length=128), nullable=False),
        sa.Column("ticket_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("audit_id"),
    )
    op.create_index("ix_opencode_repair_audit_ticket_id", "opencode_repair_audit", ["ticket_id"])
    op.create_index("ix_opencode_repair_audit_action", "opencode_repair_audit", ["action"])
    op.create_index("ix_opencode_repair_audit_correlation_id", "opencode_repair_audit", ["correlation_id"])


def downgrade() -> None:
    op.drop_index("ix_opencode_repair_audit_correlation_id", table_name="opencode_repair_audit")
    op.drop_index("ix_opencode_repair_audit_action", table_name="opencode_repair_audit")
    op.drop_index("ix_opencode_repair_audit_ticket_id", table_name="opencode_repair_audit")
    op.drop_table("opencode_repair_audit")

    op.drop_index("ix_opencode_repair_tickets_correlation_id", table_name="opencode_repair_tickets")
    op.drop_index("ix_opencode_repair_tickets_status", table_name="opencode_repair_tickets")
    op.drop_index("ix_opencode_repair_tickets_severity", table_name="opencode_repair_tickets")
    op.drop_index("ix_opencode_repair_tickets_source_event_type", table_name="opencode_repair_tickets")
    op.drop_index("ix_opencode_repair_tickets_source_module", table_name="opencode_repair_tickets")
    op.drop_table("opencode_repair_tickets")

    op.drop_index("ix_genetic_quarantine_audit_correlation_id", table_name="genetic_quarantine_audit")
    op.drop_index("ix_genetic_quarantine_audit_action", table_name="genetic_quarantine_audit")
    op.drop_index("ix_genetic_quarantine_audit_event_type", table_name="genetic_quarantine_audit")
    op.drop_index("ix_genetic_quarantine_audit_quarantine_id", table_name="genetic_quarantine_audit")
    op.drop_table("genetic_quarantine_audit")

    op.drop_index("ix_genetic_quarantine_records_correlation_id", table_name="genetic_quarantine_records")
    op.drop_index("ix_genetic_quarantine_records_source", table_name="genetic_quarantine_records")
    op.drop_index("ix_genetic_quarantine_records_severity", table_name="genetic_quarantine_records")
    op.drop_index("ix_genetic_quarantine_records_state", table_name="genetic_quarantine_records")
    op.drop_index("ix_genetic_quarantine_records_snapshot_version", table_name="genetic_quarantine_records")
    op.drop_index("ix_genetic_quarantine_records_agent_id", table_name="genetic_quarantine_records")
    op.drop_table("genetic_quarantine_records")
