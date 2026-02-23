"""Add task queue system

Revision ID: 012_add_task_queue
Revises: 011_add_agent_management
Create Date: 2025-02-23 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '012_add_task_queue'
down_revision: Union[str, None] = '011_add_agent_management'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tasks table for Task Queue System."""
    # Create enum types
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'taskstatus') THEN
                CREATE TYPE taskstatus AS ENUM (
                    'pending', 'scheduled', 'claimed', 'running', 
                    'completed', 'failed', 'cancelled', 'timeout', 'retrying'
                );
            END IF;
        END
        $$;
    """)
    
    # Create tasks table
    op.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task_id VARCHAR(100) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            task_type VARCHAR(50) NOT NULL DEFAULT 'generic',
            category VARCHAR(50),
            tags JSONB NOT NULL DEFAULT '[]',
            status taskstatus NOT NULL DEFAULT 'pending',
            priority INTEGER NOT NULL DEFAULT 50,
            payload JSONB NOT NULL DEFAULT '{}',
            config JSONB NOT NULL DEFAULT '{}',
            scheduled_at TIMESTAMP,
            deadline_at TIMESTAMP,
            claimed_by VARCHAR(100),
            claimed_at TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            max_retries INTEGER NOT NULL DEFAULT 3,
            retry_count INTEGER NOT NULL DEFAULT 0,
            retry_delay_seconds INTEGER NOT NULL DEFAULT 60,
            result JSONB,
            error_message TEXT,
            error_details JSONB,
            execution_time_ms FLOAT,
            wait_time_ms FLOAT,
            created_by VARCHAR(100),
            created_by_type VARCHAR(50),
            depends_on JSONB NOT NULL DEFAULT '[]',
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_task_id ON tasks (task_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks (priority);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_priority_created ON tasks (status, priority, created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_claimed_by ON tasks (claimed_by);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_task_type ON tasks (task_type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_scheduled_at ON tasks (scheduled_at);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks (created_at);
    
    # Create trigger for updated_at
    op.execute("""
        DROP TRIGGER IF EXISTS update_tasks_updated_at ON tasks;
        CREATE TRIGGER update_tasks_updated_at
            BEFORE UPDATE ON tasks
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Drop tasks table."""
    op.drop_table('tasks', if_exists=True)
    op.execute('DROP TYPE IF EXISTS taskstatus;')
