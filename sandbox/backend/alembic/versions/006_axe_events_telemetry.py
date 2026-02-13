"""AXE Event Telemetry - Add axe_events table for widget telemetry

Revision ID: 006_axe_events_telemetry
Revises: 005_genesis_agent_support
Create Date: 2026-01-10 00:00:00.000000

This migration adds the axe_events table for AXE widget event telemetry with:
- Event type enum (axe_message, axe_feedback, axe_click, etc.)
- Anonymization level enum (none, pseudonymized, strict)
- Session and app tracking
- JSONB event data storage
- Privacy-aware design (DSGVO-compliant)
- Indexes for efficient querying

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '006_axe_events_telemetry'
down_revision: Union[str, None] = '005_genesis_agent_support'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade to AXE Event Telemetry support.

    Creates:
    - axe_event_type ENUM (11 event types)
    - anonymization_level ENUM (3 levels)
    - axe_events table with JSONB event data
    - Performance indexes for queries
    - TTL partitioning support (optional, for future)
    """

    # Create ENUM types
    op.execute("""
        CREATE TYPE IF NOT EXISTS axe_event_type AS ENUM (
            'axe_message',
            'axe_feedback',
            'axe_click',
            'axe_context_snapshot',
            'axe_error',
            'axe_file_open',
            'axe_file_save',
            'axe_diff_applied',
            'axe_diff_rejected',
            'axe_session_start',
            'axe_session_end'
        )
    """)

    op.execute("""
        CREATE TYPE IF NOT EXISTS anonymization_level AS ENUM (
            'none',
            'pseudonymized',
            'strict'
        )
    """)

    # Create axe_events table
    op.execute("""
        CREATE TABLE IF NOT EXISTS axe_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type axe_event_type NOT NULL,
            session_id VARCHAR(255) NOT NULL,
            app_id VARCHAR(255) NOT NULL,
            user_id VARCHAR(255),
            anonymization_level anonymization_level NOT NULL DEFAULT 'pseudonymized',
            event_data JSONB NOT NULL,
            client_timestamp TIMESTAMP WITH TIME ZONE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

            -- Metadata for retention and compliance
            retention_days INTEGER DEFAULT 90,
            is_training_data BOOLEAN DEFAULT FALSE,

            -- Source tracking
            client_version VARCHAR(50),
            client_platform VARCHAR(50)
        )
    """)

    # Create indexes for efficient querying
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_axe_events_session_id
        ON axe_events(session_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_axe_events_app_id
        ON axe_events(app_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_axe_events_event_type
        ON axe_events(event_type)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_axe_events_created_at
        ON axe_events(created_at DESC)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_axe_events_user_id
        ON axe_events(user_id)
        WHERE user_id IS NOT NULL
    """)

    # Index for training data queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_axe_events_training_data
        ON axe_events(is_training_data, anonymization_level)
        WHERE is_training_data = TRUE
    """)

    # JSONB GIN index for event_data queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_axe_events_event_data_gin
        ON axe_events USING GIN (event_data)
    """)

    # Composite index for session analytics
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_axe_events_session_analytics
        ON axe_events(session_id, event_type, created_at DESC)
    """)

    # Add table comment
    op.execute("""
        COMMENT ON TABLE axe_events IS
        'AXE Widget event telemetry with privacy controls (DSGVO-compliant)'
    """)

    # Add column comments
    op.execute("""
        COMMENT ON COLUMN axe_events.event_type IS
        'Type of AXE event (message, feedback, click, error, etc.)'
    """)

    op.execute("""
        COMMENT ON COLUMN axe_events.session_id IS
        'Unique session identifier for grouping related events'
    """)

    op.execute("""
        COMMENT ON COLUMN axe_events.app_id IS
        'Application identifier (e.g., widget-test, fewoheros, satoshiflow)'
    """)

    op.execute("""
        COMMENT ON COLUMN axe_events.user_id IS
        'Optional user identifier (anonymized based on anonymization_level)'
    """)

    op.execute("""
        COMMENT ON COLUMN axe_events.anonymization_level IS
        'Privacy level: none (full data), pseudonymized (hashed IDs), strict (no PII)'
    """)

    op.execute("""
        COMMENT ON COLUMN axe_events.event_data IS
        'Flexible JSONB field for event-specific data (message content, error details, etc.)'
    """)

    op.execute("""
        COMMENT ON COLUMN axe_events.retention_days IS
        'Number of days to retain this event (default 90, configurable per event type)'
    """)

    op.execute("""
        COMMENT ON COLUMN axe_events.is_training_data IS
        'Flag indicating if this event can be used for LLM training (requires explicit user consent)'
    """)

    # Create a function for automatic cleanup (optional, can be scheduled via cron)
    op.execute("""
        CREATE OR REPLACE FUNCTION cleanup_old_axe_events()
        RETURNS INTEGER AS $$
        DECLARE
            deleted_count INTEGER;
        BEGIN
            DELETE FROM axe_events
            WHERE created_at < (CURRENT_TIMESTAMP - INTERVAL '1 day' * retention_days);

            GET DIAGNOSTICS deleted_count = ROW_COUNT;
            RETURN deleted_count;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        COMMENT ON FUNCTION cleanup_old_axe_events() IS
        'Delete events older than their retention period (run via cron or pg_cron)'
    """)


def downgrade() -> None:
    """
    Downgrade from AXE Event Telemetry support.

    Removes:
    - axe_events table
    - Indexes
    - ENUM types
    - Cleanup function
    """
    # Drop cleanup function
    op.execute("DROP FUNCTION IF EXISTS cleanup_old_axe_events()")

    # Drop indexes (will cascade with table, but explicit for clarity)
    op.execute("DROP INDEX IF EXISTS idx_axe_events_session_analytics")
    op.execute("DROP INDEX IF EXISTS idx_axe_events_event_data_gin")
    op.execute("DROP INDEX IF EXISTS idx_axe_events_training_data")
    op.execute("DROP INDEX IF EXISTS idx_axe_events_user_id")
    op.execute("DROP INDEX IF EXISTS idx_axe_events_created_at")
    op.execute("DROP INDEX IF EXISTS idx_axe_events_event_type")
    op.execute("DROP INDEX IF EXISTS idx_axe_events_app_id")
    op.execute("DROP INDEX IF EXISTS idx_axe_events_session_id")

    # Drop table
    op.execute("DROP TABLE IF EXISTS axe_events CASCADE")

    # Drop ENUM types (check for dependencies first)
    op.execute("DROP TYPE IF EXISTS anonymization_level CASCADE")
    op.execute("DROP TYPE IF EXISTS axe_event_type CASCADE")
