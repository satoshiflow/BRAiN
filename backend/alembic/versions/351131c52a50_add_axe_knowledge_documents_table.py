"""Add AXE knowledge documents table

Revision ID: 351131c52a50
Revises: 6c1cd97efaa1
Create Date: 2026-02-19 18:25:17.638617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '351131c52a50'
down_revision: Union[str, None] = '6c1cd97efaa1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create AXE knowledge documents table
    op.create_table(
        'axe_knowledge_documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_type', sa.String(length=50), nullable=True),
        sa.Column('doc_metadata', sa.JSON(), nullable=True),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('is_enabled', sa.Boolean(), nullable=True),
        sa.Column('access_count', sa.Integer(), nullable=True),
        sa.Column('importance_score', sa.Float(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('parent_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        sa.ForeignKeyConstraint(['parent_id'], ['axe_knowledge_documents.id'], ondelete='SET NULL')
    )

    # Create indexes
    op.create_index('idx_knowledge_category', 'axe_knowledge_documents', ['category'])
    op.create_index('idx_knowledge_enabled', 'axe_knowledge_documents', ['is_enabled'])
    op.create_index('idx_knowledge_importance', 'axe_knowledge_documents', ['importance_score'])
    op.create_index('idx_knowledge_created_at', 'axe_knowledge_documents', ['created_at'])
    op.create_index('idx_knowledge_name', 'axe_knowledge_documents', ['name'])

    # Insert sample knowledge document
    op.execute("""
        INSERT INTO axe_knowledge_documents (
            id,
            name,
            description,
            category,
            content,
            content_type,
            doc_metadata,
            tags,
            is_enabled,
            access_count,
            importance_score,
            version,
            created_by
        )
        VALUES (
            gen_random_uuid(),
            'BRAiN System Overview',
            'Overview of the BRAiN system architecture and components',
            'system',
            E'## BRAiN System Overview\n\n### Core Components\n\n1. **Backend API** - FastAPI-based REST API\n2. **AXE UI** - Next.js frontend for chat interface\n3. **AXEllm** - OpenAI-compatible LLM proxy\n4. **Ollama** - Local LLM inference\n\n### Key Features\n\n- Real-time chat with AXE identity\n- Knowledge document management\n- System health monitoring\n- Multi-tenant architecture',
            'markdown',
            '{\"source\": \"system\", \"verified\": true}',
            ARRAY['system', 'overview', 'architecture'],
            TRUE,
            0,
            9.5,
            1,
            'system'
        )
    """)


def downgrade() -> None:
    op.drop_index('idx_knowledge_name', table_name='axe_knowledge_documents')
    op.drop_index('idx_knowledge_created_at', table_name='axe_knowledge_documents')
    op.drop_index('idx_knowledge_importance', table_name='axe_knowledge_documents')
    op.drop_index('idx_knowledge_enabled', table_name='axe_knowledge_documents')
    op.drop_index('idx_knowledge_category', table_name='axe_knowledge_documents')
    op.drop_table('axe_knowledge_documents')
