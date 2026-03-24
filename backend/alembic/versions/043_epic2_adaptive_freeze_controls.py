"""Epic 2 adaptive freeze controls.

Revision ID: 043_epic2_adaptive_freeze_controls
Revises: 042_epic2_memory_tenant_boundaries
Create Date: 2026-03-22 20:05:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "043_epic2_adaptive_freeze_controls"
down_revision: Union[str, None] = "042_epic2_memory_tenant_boundaries"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evolution_control_flags",
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("adaptive_frozen", sa.String(length=8), nullable=False, server_default="false"),
        sa.Column("freeze_reason", sa.Text(), nullable=True),
        sa.Column("frozen_by", sa.String(length=120), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("tenant_id"),
    )


def downgrade() -> None:
    op.drop_table("evolution_control_flags")
