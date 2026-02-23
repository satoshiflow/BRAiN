"""Add agent management system

Revision ID: 011_add_agent_management
Revises: 010_add_skill_builtin_flag
Create Date: 2025-02-23 08:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '011_add_agent_management'
down_revision: Union[str, None] = '010_add_skill_builtin_flag'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agents table for Agent Management System."""
    # Create enum type
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'agentstatus') THEN
                CREATE TYPE agentstatus AS ENUM (
                    'registered', 'active', 'degraded', 'offline', 'maintenance', 'terminated'
                );
            END IF;
        END
        $$;
    """)
    
    # Create agents table
    op.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            status agentstatus NOT NULL DEFAULT 'registered',
            agent_type VARCHAR(50) NOT NULL DEFAULT 'worker',
            version VARCHAR(50),
            capabilities JSONB NOT NULL DEFAULT '[]',
            config JSONB NOT NULL DEFAULT '{}',
            last_heartbeat TIMESTAMP,
            heartbeat_interval INTEGER NOT NULL DEFAULT 60,
            missed_heartbeats INTEGER NOT NULL DEFAULT 0,
            tasks_completed INTEGER NOT NULL DEFAULT 0,
            tasks_failed INTEGER NOT NULL DEFAULT 0,
            avg_task_duration_ms FLOAT,
            host VARCHAR(255),
            pid INTEGER,
            registered_at TIMESTAMP NOT NULL DEFAULT NOW(),
            activated_at TIMESTAMP,
            last_active_at TIMESTAMP,
            terminated_at TIMESTAMP
        );
    """)
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_agent_id ON agents (agent_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_status ON agents (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_agent_type ON agents (agent_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_status_type ON agents (status, agent_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_agents_last_heartbeat ON agents (last_heartbeat);")
    
    # Create trigger for updated_at
    op.execute("""
        DROP TRIGGER IF EXISTS update_agents_updated_at ON agents;
        CREATE TRIGGER update_agents_updated_at
            BEFORE UPDATE ON agents
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop agents table."""
    op.drop_table('agents', if_exists=True)
    op.execute('DROP TYPE IF EXISTS agentstatus;')
