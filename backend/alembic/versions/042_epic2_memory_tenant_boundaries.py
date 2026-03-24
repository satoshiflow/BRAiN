"""Epic 2 memory tenant boundaries.

Revision ID: 042_epic2_memory_tenant_boundaries
Revises: 041_epic2_memory_contract_links
Create Date: 2026-03-22 18:20:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "042_epic2_memory_tenant_boundaries"
down_revision: Union[str, None] = "041_epic2_memory_contract_links"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("memory_entries", sa.Column("tenant_id", sa.String(length=64), nullable=True))
    op.create_index("idx_memory_entries_tenant", "memory_entries", ["tenant_id"], unique=False)

    op.add_column("session_contexts", sa.Column("tenant_id", sa.String(length=64), nullable=True))
    op.create_index("idx_session_contexts_tenant", "session_contexts", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_session_contexts_tenant", table_name="session_contexts")
    op.drop_column("session_contexts", "tenant_id")

    op.drop_index("idx_memory_entries_tenant", table_name="memory_entries")
    op.drop_column("memory_entries", "tenant_id")
