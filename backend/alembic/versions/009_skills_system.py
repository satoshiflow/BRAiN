"""Add skills system

Revision ID: 009_skills_system
Revises: 008_mission_templates
Create Date: 2025-02-12 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '009_skills_system'
down_revision: Union[str, None] = '008_mission_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create skills table for the PicoClaw-style Skill System.
    """
    # Create enum type if not exists using raw SQL
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'skillcategory') THEN
                CREATE TYPE skillcategory AS ENUM ('api', 'file', 'communication', 'analysis', 'custom');
            END IF;
        END
        $$;
    """)
    
    # Create skills table using raw SQL for the enum column
    op.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            category skillcategory NOT NULL DEFAULT 'custom',
            manifest JSONB NOT NULL DEFAULT '{}',
            handler_path VARCHAR(255) NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_skills_name ON skills (name);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skills_category ON skills (category);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skills_enabled ON skills (enabled);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skills_category_enabled ON skills (category, enabled);")
    
    # Create update trigger for updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    op.execute("""
        DROP TRIGGER IF EXISTS update_skills_updated_at ON skills;
        CREATE TRIGGER update_skills_updated_at
            BEFORE UPDATE ON skills
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """
    Drop skills table and related objects.
    """
    op.drop_table('skills', if_exists=True)
    op.execute('DROP TYPE IF EXISTS skillcategory;')
