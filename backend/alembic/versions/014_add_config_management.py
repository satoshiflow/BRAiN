"""Add config management
Revision ID: 014_add_config_management
Revises: 013_add_health_monitor
"""
from typing import Sequence, Union
from alembic import op

revision: str = '014_add_config_management'
down_revision: Union[str, None] = '013_add_health_monitor'

def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS config_entries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key VARCHAR(255) NOT NULL,
            value JSONB,
            type VARCHAR(50) NOT NULL DEFAULT 'string',
            environment VARCHAR(50) NOT NULL DEFAULT 'default',
            is_secret BOOLEAN NOT NULL DEFAULT false,
            is_encrypted BOOLEAN NOT NULL DEFAULT false,
            description TEXT,
            version INTEGER NOT NULL DEFAULT 1,
            created_by VARCHAR(100),
            updated_by VARCHAR(100),
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            UNIQUE(key, environment)
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_config_key ON config_entries (key);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_config_env ON config_entries (environment);")

def downgrade():
    op.drop_table('config_entries', if_exists=True)
