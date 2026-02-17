"""Genesis Agent support - Extend agents table

Revision ID: 005_genesis_agent_support
Revises: 004_neurorail_schema
Create Date: 2026-01-02 00:00:00.000000

This migration extends the agents table to support Genesis Agent System:
- Add status column (CREATED, QUARANTINED, ACTIVE, DECOMMISSIONED, ARCHIVED)
- Add dna_schema_version column (MANDATORY for DNA v2.0)
- Add template_hash column (SHA256 hash of source template)
- Add request_id column (for idempotency)
- Add indexes for performance

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_genesis_agent_support'
down_revision: Union[str, None] = '004_neurorail_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade to Genesis Agent support.

    Extends agents table with:
    - status: Agent lifecycle status
    - dna_schema_version: DNA schema version (v2.0)
    - template_hash: SHA256 hash of source template
    - request_id: Unique request ID for idempotency
    """
    # Check if agents table exists, if not create it
    op.execute("""
        CREATE TABLE IF NOT EXISTS agents (
            id VARCHAR(64) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50) NOT NULL,
            config JSONB,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)

    # Add new columns for Genesis support
    op.execute("""
        ALTER TABLE agents
        ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'CREATED',
        ADD COLUMN IF NOT EXISTS dna_schema_version VARCHAR(10),
        ADD COLUMN IF NOT EXISTS template_hash VARCHAR(71),
        ADD COLUMN IF NOT EXISTS request_id VARCHAR(64) UNIQUE
    """)

    # Create indexes for performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agents_status
        ON agents(status)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agents_type
        ON agents(type)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agents_request_id
        ON agents(request_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_agents_created_at
        ON agents(created_at DESC)
    """)

    # Add comment on table
    op.execute("""
        COMMENT ON TABLE agents IS
        'Agent registry with Genesis support (DNA v2.0)'
    """)

    # Add comments on new columns
    op.execute("""
        COMMENT ON COLUMN agents.status IS
        'Agent lifecycle status: CREATED, QUARANTINED, ACTIVE, DECOMMISSIONED, ARCHIVED'
    """)

    op.execute("""
        COMMENT ON COLUMN agents.dna_schema_version IS
        'DNA schema version (e.g., 2.0) - MANDATORY for Genesis agents'
    """)

    op.execute("""
        COMMENT ON COLUMN agents.template_hash IS
        'SHA256 hash of source template (format: sha256:abc123...) for reproducibility'
    """)

    op.execute("""
        COMMENT ON COLUMN agents.request_id IS
        'Unique request identifier for idempotency (prevents duplicate creation)'
    """)


def downgrade() -> None:
    """
    Downgrade from Genesis Agent support.

    Removes Genesis-specific columns and indexes.
    """
    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_agents_created_at")
    op.execute("DROP INDEX IF EXISTS idx_agents_request_id")
    op.execute("DROP INDEX IF EXISTS idx_agents_type")
    op.execute("DROP INDEX IF EXISTS idx_agents_status")

    # Drop columns
    op.execute("""
        ALTER TABLE agents
        DROP COLUMN IF EXISTS status,
        DROP COLUMN IF EXISTS dna_schema_version,
        DROP COLUMN IF EXISTS template_hash,
        DROP COLUMN IF EXISTS request_id
    """)
