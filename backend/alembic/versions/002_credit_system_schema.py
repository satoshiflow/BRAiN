"""Credit System Schema - Phase 2

Revision ID: 002_credit_system_schema
Revises: 001_initial_schema
Create Date: 2025-12-21 00:00:00.000000

This migration implements the complete credit system infrastructure:
- Credit Ledger (append-only)
- Agent Registry (with lifecycle tracking)
- Audit Trail
- Supporting indexes and constraints

Specification: docs/specs/brain_credit_selection_spec.v1.yaml
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_credit_system_schema'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade to credit system schema.

    Creates:
    1. credit_ledger - Append-only transaction log
    2. agent_registry - Extended agent metadata with lifecycle
    3. audit_trail - Comprehensive audit logging
    """

    # ========================================================================
    # 1. CREDIT LEDGER
    # ========================================================================

    op.create_table(
        'credit_ledger',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('sequence_number', sa.BigInteger, nullable=False, autoincrement=True, unique=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('credit_type', sa.String(50), nullable=False),
        sa.Column('amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('balance_after', sa.Numeric(20, 6), nullable=False),
        sa.Column('transaction_type', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text, nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('signature', sa.String(255), nullable=False),

        # Constraints
        sa.CheckConstraint("entity_type IN ('AGENT', 'MISSION', 'SYSTEM')", name='ck_entity_type'),
        sa.CheckConstraint("credit_type IN ('CC', 'LC', 'SC', 'NC')", name='ck_credit_type'),
        sa.CheckConstraint("transaction_type IN ('MINT', 'BURN', 'TRANSFER', 'TAX')", name='ck_transaction_type'),
    )

    # Indexes for credit_ledger
    op.create_index('idx_ledger_entity_time', 'credit_ledger', ['entity_id', sa.text('timestamp DESC')])
    op.create_index('idx_ledger_sequence', 'credit_ledger', ['sequence_number'], unique=True)
    op.create_index('idx_ledger_credit_type', 'credit_ledger', ['credit_type', sa.text('timestamp DESC')])
    op.create_index('idx_ledger_entity_type', 'credit_ledger', ['entity_type'])
    op.create_index('idx_ledger_transaction_type', 'credit_ledger', ['transaction_type'])

    # ========================================================================
    # 2. AGENT REGISTRY
    # ========================================================================

    op.create_table(
        'agent_registry',
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_name', sa.String(255), nullable=False, unique=True),
        sa.Column('agent_type', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('suspended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('terminated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),

        # Credit balances (cached for performance)
        sa.Column('credit_balance_cc', sa.Numeric(20, 6), nullable=False, server_default='0.0'),
        sa.Column('credit_balance_lc', sa.Numeric(20, 6), nullable=False, server_default='0.0'),
        sa.Column('credit_balance_sc', sa.Numeric(20, 6), nullable=False, server_default='0.0'),
        sa.Column('credit_balance_nc', sa.Numeric(20, 6), nullable=False, server_default='0.0'),

        # Lifetime statistics
        sa.Column('total_credits_earned', sa.Numeric(20, 6), nullable=False, server_default='0.0'),
        sa.Column('total_credits_spent', sa.Numeric(20, 6), nullable=False, server_default='0.0'),

        # Metadata
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),

        # Constraints
        sa.CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'TERMINATED')", name='ck_agent_status'),
    )

    # Indexes for agent_registry
    op.create_index('idx_agent_status', 'agent_registry', ['status'])
    op.create_index('idx_agent_type', 'agent_registry', ['agent_type'])
    op.create_index('idx_agent_created', 'agent_registry', [sa.text('created_at DESC')])
    op.create_index('idx_agent_last_activity', 'agent_registry', [sa.text('last_activity_at DESC')])

    # ========================================================================
    # 3. AUDIT TRAIL
    # ========================================================================

    op.create_table(
        'audit_trail',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(255), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.String(255), nullable=False),
        sa.Column('action', sa.Text, nullable=False),
        sa.Column('result', sa.String(50), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('signature', sa.String(255), nullable=False),

        # Constraints
        sa.CheckConstraint("result IN ('SUCCESS', 'FAILURE', 'DENIED')", name='ck_audit_result'),
    )

    # Indexes for audit_trail
    op.create_index('idx_audit_timestamp', 'audit_trail', [sa.text('timestamp DESC')])
    op.create_index('idx_audit_entity', 'audit_trail', ['entity_id', sa.text('timestamp DESC')])
    op.create_index('idx_audit_event_type', 'audit_trail', ['event_type'])
    op.create_index('idx_audit_actor', 'audit_trail', ['actor_id'])
    op.create_index('idx_audit_result', 'audit_trail', ['result'])


def downgrade() -> None:
    """
    Downgrade from credit system schema.

    Drops all credit system tables and indexes.
    """

    # Drop tables in reverse order
    op.drop_table('audit_trail')
    op.drop_table('agent_registry')
    op.drop_table('credit_ledger')
