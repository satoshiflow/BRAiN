"""Add AXE identity table

Revision ID: 6c1cd97efaa1
Revises: 012_add_cluster_system
Create Date: 2026-02-19 17:11:59.120542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c1cd97efaa1'
down_revision: Union[str, None] = '012_add_cluster_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create AXE identities table
    op.create_table(
        'axe_identities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('personality', sa.JSON(), nullable=True),
        sa.Column('capabilities', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create indexes
    op.create_index('idx_axe_identities_active', 'axe_identities', ['is_active'],
                    postgresql_where=sa.text('is_active = TRUE'))
    op.create_index('idx_axe_identities_name', 'axe_identities', ['name'])
    op.create_index('idx_axe_identities_created_at', 'axe_identities', ['created_at'])

    # Insert default AXE identity
    op.execute("""
        INSERT INTO axe_identities (
            id,
            name,
            description,
            system_prompt,
            personality,
            capabilities,
            is_active,
            version,
            created_by
        )
        VALUES (
            gen_random_uuid(),
            'AXE Default',
            'Default AXE identity with standard capabilities',
            'Du bist AXE (Auxiliary Execution Engine), der intelligente Assistent des BRAiN-Systems.

Deine Rolle:
- Hilfreicher Assistent für System-Administration und Monitoring
- Schnittstelle zwischen Mensch und BRAiN-Framework
- Troubleshooting-Partner bei Problemen

Deine Fähigkeiten:
- System-Status überwachen
- Logs analysieren
- Fehler diagnostizieren
- Empfehlungen geben

Antworte präzise, hilfsbereit und technisch versiert.',
            '{}',
            ARRAY['monitoring', 'troubleshooting', 'system-admin'],
            TRUE,
            1,
            'system'
        )
    """)


def downgrade() -> None:
    op.drop_index('idx_axe_identities_created_at', table_name='axe_identities')
    op.drop_index('idx_axe_identities_name', table_name='axe_identities')
    op.drop_index('idx_axe_identities_active', table_name='axe_identities')
    op.drop_table('axe_identities')
