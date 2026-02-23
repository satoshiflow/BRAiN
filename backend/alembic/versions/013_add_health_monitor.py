"""Add health monitor system

Revision ID: 013_add_health_monitor
Revises: 012_add_task_queue
"""
from typing import Sequence, Union

from alembic import op

revision: str = '013_add_health_monitor'
down_revision: Union[str, None] = '012_add_task_queue'


def upgrade() -> None:
    """Create health check tables."""
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'healthstatus') THEN
                CREATE TYPE healthstatus AS ENUM ('healthy', 'degraded', 'unhealthy', 'unknown');
            END IF;
        END
        $$;
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS health_checks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_name VARCHAR(100) NOT NULL UNIQUE,
            service_type VARCHAR(50) NOT NULL DEFAULT 'internal',
            status healthstatus NOT NULL DEFAULT 'unknown',
            previous_status healthstatus,
            status_changed_at TIMESTAMP,
            last_check_at TIMESTAMP,
            next_check_at TIMESTAMP,
            response_time_ms FLOAT,
            check_interval_seconds INTEGER NOT NULL DEFAULT 60,
            error_message TEXT,
            check_output TEXT,
            metadata JSONB NOT NULL DEFAULT '{}',
            total_checks INTEGER NOT NULL DEFAULT 0,
            failed_checks INTEGER NOT NULL DEFAULT 0,
            consecutive_failures INTEGER NOT NULL DEFAULT 0,
            consecutive_successes INTEGER NOT NULL DEFAULT 0,
            uptime_percentage FLOAT,
            last_healthy_at TIMESTAMP,
            last_failure_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    
    op.execute("""
        CREATE TABLE IF NOT EXISTS health_check_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            service_name VARCHAR(100) NOT NULL,
            status healthstatus NOT NULL,
            response_time_ms FLOAT,
            error_message TEXT,
            checked_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    
    op.execute("CREATE INDEX IF NOT EXISTS idx_health_checks_service ON health_checks (service_name);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_health_checks_status ON health_checks (status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_health_history_service ON health_check_history (service_name);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_health_history_checked ON health_check_history (checked_at);


def downgrade() -> None:
    op.drop_table('health_check_history', if_exists=True)
    op.drop_table('health_checks', if_exists=True)
    op.execute('DROP TYPE IF EXISTS healthstatus;')
