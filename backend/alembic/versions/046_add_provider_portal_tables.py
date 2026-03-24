"""Add provider portal control-plane tables.

Revision ID: 046_add_provider_portal_tables
Revises: 045_add_routing_memory_and_adaptation
Create Date: 2026-03-24 22:40:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "046_add_provider_portal_tables"
down_revision: Union[str, None] = "045_add_routing_memory_and_adaptation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "provider_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=64), nullable=True),
        sa.Column("owner_scope", sa.String(length=16), nullable=False, server_default="system"),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False, server_default="cloud"),
        sa.Column("base_url", sa.String(length=255), nullable=False),
        sa.Column("auth_mode", sa.String(length=32), nullable=False, server_default="api_key"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_local", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_chat", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_embeddings", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_responses", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("health_status", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_health_error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("updated_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "owner_scope", "slug", name="uq_provider_accounts_scope_slug"),
    )
    op.create_index(op.f("ix_provider_accounts_tenant_id"), "provider_accounts", ["tenant_id"], unique=False)
    op.create_index("ix_provider_accounts_scope_enabled", "provider_accounts", ["owner_scope", "is_enabled"], unique=False)

    op.create_table(
        "provider_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("key_hint_last4", sa.String(length=8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("updated_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_credentials_provider_id"), "provider_credentials", ["provider_id"], unique=False)
    op.create_index(
        "ix_provider_credentials_provider_active",
        "provider_credentials",
        ["provider_id", "is_active"],
        unique=False,
    )

    op.create_table(
        "provider_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(length=160), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("cost_class", sa.String(length=32), nullable=True),
        sa.Column("latency_class", sa.String(length=32), nullable=True),
        sa.Column("quality_class", sa.String(length=32), nullable=True),
        sa.Column("supports_tools", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_json", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_streaming", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "model_name", name="uq_provider_models_provider_model_name"),
    )
    op.create_index(op.f("ix_provider_models_provider_id"), "provider_models", ["provider_id"], unique=False)
    op.create_index(
        "ix_provider_models_provider_enabled_priority",
        "provider_models",
        ["provider_id", "is_enabled", "priority"],
        unique=False,
    )

    op.create_table(
        "provider_health_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="unknown"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["provider_accounts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_provider_health_checks_provider_id"), "provider_health_checks", ["provider_id"], unique=False)
    op.create_index(
        "ix_provider_health_checks_provider_checked_at",
        "provider_health_checks",
        ["provider_id", "checked_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_provider_health_checks_provider_checked_at", table_name="provider_health_checks")
    op.drop_index(op.f("ix_provider_health_checks_provider_id"), table_name="provider_health_checks")
    op.drop_table("provider_health_checks")

    op.drop_index("ix_provider_models_provider_enabled_priority", table_name="provider_models")
    op.drop_index(op.f("ix_provider_models_provider_id"), table_name="provider_models")
    op.drop_table("provider_models")

    op.drop_index("ix_provider_credentials_provider_active", table_name="provider_credentials")
    op.drop_index(op.f("ix_provider_credentials_provider_id"), table_name="provider_credentials")
    op.drop_table("provider_credentials")

    op.drop_index("ix_provider_accounts_scope_enabled", table_name="provider_accounts")
    op.drop_index(op.f("ix_provider_accounts_tenant_id"), table_name="provider_accounts")
    op.drop_table("provider_accounts")
