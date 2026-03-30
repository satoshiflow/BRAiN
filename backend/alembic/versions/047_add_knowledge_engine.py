"""Add knowledge engine tables.

Revision ID: 047_add_knowledge_engine
Revises: 046_add_provider_portal_tables
Create Date: 2026-03-30 15:30:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "047_add_knowledge_engine"
down_revision: Union[str, None] = "046_add_provider_portal_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id VARCHAR(64),
            title VARCHAR(255) NOT NULL,
            content TEXT NOT NULL,
            type VARCHAR(40) NOT NULL,
            tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            visibility VARCHAR(24) NOT NULL DEFAULT 'tenant',
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            item_id UUID NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            embedding_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            embedding_vector TEXT,
            chunk_index INTEGER NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_links (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id UUID NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
            target_id UUID NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
            relation_type VARCHAR(60) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            item_id UUID NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
            version INTEGER NOT NULL,
            diff JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS knowledge_scores (
            item_id UUID PRIMARY KEY REFERENCES knowledge_items(id) ON DELETE CASCADE,
            usage_count INTEGER NOT NULL DEFAULT 0,
            relevance_score DOUBLE PRECISION NOT NULL DEFAULT 0,
            last_used TIMESTAMPTZ,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_items_tenant_type ON knowledge_items (tenant_id, type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_items_updated_at ON knowledge_items (updated_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_item_index ON knowledge_chunks (item_id, chunk_index)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_links_source_target ON knowledge_links (source_id, target_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_versions_item_version ON knowledge_versions (item_id, version DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_knowledge_scores_relevance ON knowledge_scores (relevance_score DESC)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_knowledge_scores_relevance")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_versions_item_version")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_links_source_target")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_chunks_item_index")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_items_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_knowledge_items_tenant_type")

    op.execute("DROP TABLE IF EXISTS knowledge_scores")
    op.execute("DROP TABLE IF EXISTS knowledge_versions")
    op.execute("DROP TABLE IF EXISTS knowledge_links")
    op.execute("DROP TABLE IF EXISTS knowledge_chunks")
    op.execute("DROP TABLE IF EXISTS knowledge_items")
