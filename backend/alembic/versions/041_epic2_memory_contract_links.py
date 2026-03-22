"""Epic 2 memory contract links.

Revision ID: 041_epic2_memory_contract_links
Revises: 040_epic1_control_plane_normalization
Create Date: 2026-03-22 17:25:00.000000
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "041_epic2_memory_contract_links"
down_revision: Union[str, None] = "040_epic1_control_plane_normalization"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("experience_records", sa.Column("evaluation_result_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_experience_records_eval", "experience_records", ["tenant_id", "evaluation_result_id"], unique=False)

    op.add_column("knowledge_items", sa.Column("skill_run_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("knowledge_items", sa.Column("experience_record_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("knowledge_items", sa.Column("evaluation_result_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_knowledge_items_run_chain", "knowledge_items", ["tenant_id", "skill_run_id", "experience_record_id", "evaluation_result_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_knowledge_items_run_chain", table_name="knowledge_items")
    op.drop_column("knowledge_items", "evaluation_result_id")
    op.drop_column("knowledge_items", "experience_record_id")
    op.drop_column("knowledge_items", "skill_run_id")

    op.drop_index("ix_experience_records_eval", table_name="experience_records")
    op.drop_column("experience_records", "evaluation_result_id")
