"""Add audit logging
Revision ID: 015_add_audit_logging
Revises: 014_add_config_management
"""
from typing import Sequence, Union
from alembic import op

revision: str = '015_add_audit_logging'
down_revision: Union[str, None] = '014_add_config_management'

def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(50) NOT NULL,
            action VARCHAR(50) NOT NULL,
            actor VARCHAR(100) NOT NULL,
            actor_type VARCHAR(50) NOT NULL DEFAULT 'user',
            resource_type VARCHAR(100),
            resource_id VARCHAR(100),
            old_values JSONB,
            new_values JSONB,
            ip_address VARCHAR(45),
            user_agent TEXT,
            severity VARCHAR(20) NOT NULL DEFAULT 'info',
            message TEXT,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_events (event_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events (action);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events (actor);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events (resource_type, resource_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events (created_at);")

def downgrade():
    op.drop_table('audit_events', if_exists=True)
