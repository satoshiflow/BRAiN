"""Add user-scoped AXE chat session tables.

Revision ID: 038_add_axe_chat_sessions
Revises: 037_escalation_status_constraint
Create Date: 2026-03-12 16:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "038_add_axe_chat_sessions"
down_revision: Union[str, None] = "037_escalation_status_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "axe_chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("principal_id", sa.String(length=255), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False, server_default="New Chat"),
        sa.Column("preview", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("last_message_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("status IN ('active', 'deleted')", name="ck_axe_chat_sessions_status"),
    )
    op.create_index(op.f("ix_axe_chat_sessions_principal_id"), "axe_chat_sessions", ["principal_id"], unique=False)
    op.create_index(op.f("ix_axe_chat_sessions_tenant_id"), "axe_chat_sessions", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_axe_chat_sessions_status"), "axe_chat_sessions", ["status"], unique=False)
    op.create_index(op.f("ix_axe_chat_sessions_created_at"), "axe_chat_sessions", ["created_at"], unique=False)
    op.create_index(op.f("ix_axe_chat_sessions_updated_at"), "axe_chat_sessions", ["updated_at"], unique=False)
    op.create_index(op.f("ix_axe_chat_sessions_last_message_at"), "axe_chat_sessions", ["last_message_at"], unique=False)

    op.create_table(
        "axe_chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachments", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["axe_chat_sessions.id"], ondelete="CASCADE"),
        sa.CheckConstraint("role IN ('user', 'assistant')", name="ck_axe_chat_messages_role"),
    )
    op.create_index(op.f("ix_axe_chat_messages_session_id"), "axe_chat_messages", ["session_id"], unique=False)
    op.create_index(op.f("ix_axe_chat_messages_created_at"), "axe_chat_messages", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_axe_chat_messages_created_at"), table_name="axe_chat_messages")
    op.drop_index(op.f("ix_axe_chat_messages_session_id"), table_name="axe_chat_messages")
    op.drop_table("axe_chat_messages")

    op.drop_index(op.f("ix_axe_chat_sessions_last_message_at"), table_name="axe_chat_sessions")
    op.drop_index(op.f("ix_axe_chat_sessions_updated_at"), table_name="axe_chat_sessions")
    op.drop_index(op.f("ix_axe_chat_sessions_created_at"), table_name="axe_chat_sessions")
    op.drop_index(op.f("ix_axe_chat_sessions_status"), table_name="axe_chat_sessions")
    op.drop_index(op.f("ix_axe_chat_sessions_tenant_id"), table_name="axe_chat_sessions")
    op.drop_index(op.f("ix_axe_chat_sessions_principal_id"), table_name="axe_chat_sessions")
    op.drop_table("axe_chat_sessions")
