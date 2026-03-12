"""Add AXE worker run polling table.

Revision ID: 039_add_axe_worker_runs
Revises: 038_add_axe_chat_sessions
Create Date: 2026-03-12 19:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "039_add_axe_worker_runs"
down_revision: Union[str, None] = "038_add_axe_chat_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "axe_worker_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_run_id", sa.String(length=64), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
        sa.Column("backend_run_id", sa.String(length=128), nullable=True),
        sa.Column("backend_run_type", sa.String(length=32), nullable=False, server_default="opencode_job"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("label", sa.String(length=160), nullable=False, server_default="OpenCode worker queued"),
        sa.Column("detail", sa.Text(), nullable=False, server_default="Job accepted by BRAiN orchestrator"),
        sa.Column("artifacts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["session_id"], ["axe_chat_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_run_id"),
    )

    op.create_index(op.f("ix_axe_worker_runs_session_id"), "axe_worker_runs", ["session_id"], unique=False)
    op.create_index(op.f("ix_axe_worker_runs_principal_id"), "axe_worker_runs", ["principal_id"], unique=False)
    op.create_index(op.f("ix_axe_worker_runs_tenant_id"), "axe_worker_runs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_axe_worker_runs_status"), "axe_worker_runs", ["status"], unique=False)
    op.create_index(op.f("ix_axe_worker_runs_updated_at"), "axe_worker_runs", ["updated_at"], unique=False)
    op.create_index(op.f("ix_axe_worker_runs_backend_run_id"), "axe_worker_runs", ["backend_run_id"], unique=False)
    op.create_index(op.f("ix_axe_worker_runs_message_id"), "axe_worker_runs", ["message_id"], unique=False)
    op.create_index(
        "ix_axe_worker_runs_session_updated",
        "axe_worker_runs",
        ["session_id", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_axe_worker_runs_session_updated", table_name="axe_worker_runs")
    op.drop_index(op.f("ix_axe_worker_runs_message_id"), table_name="axe_worker_runs")
    op.drop_index(op.f("ix_axe_worker_runs_backend_run_id"), table_name="axe_worker_runs")
    op.drop_index(op.f("ix_axe_worker_runs_updated_at"), table_name="axe_worker_runs")
    op.drop_index(op.f("ix_axe_worker_runs_status"), table_name="axe_worker_runs")
    op.drop_index(op.f("ix_axe_worker_runs_tenant_id"), table_name="axe_worker_runs")
    op.drop_index(op.f("ix_axe_worker_runs_principal_id"), table_name="axe_worker_runs")
    op.drop_index(op.f("ix_axe_worker_runs_session_id"), table_name="axe_worker_runs")
    op.drop_table("axe_worker_runs")
