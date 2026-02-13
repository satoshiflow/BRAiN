"""Add PayCore tables

Revision ID: 002_add_paycore_tables
Revises: 001_initial_schema
Create Date: 2025-12-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '002_add_paycore_tables'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create PayCore tables for payment processing.
    """
    # Create enums
    op.execute("CREATE TYPE payment_provider AS ENUM ('stripe', 'paypal', 'crypto')")
    op.execute("CREATE TYPE intent_status AS ENUM ('created', 'pending', 'succeeded', 'failed', 'cancelled')")
    op.execute("CREATE TYPE transaction_event_type AS ENUM ('payment_succeeded', 'payment_failed', 'payment_cancelled', 'refund_succeeded', 'refund_failed')")
    op.execute("CREATE TYPE refund_status AS ENUM ('requested', 'processing', 'succeeded', 'failed')")

    # Table: paycore_intents
    op.create_table(
        'paycore_intents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('user_id', sa.String(100), nullable=True),
        sa.Column('provider', sa.Enum('stripe', 'paypal', 'crypto', name='payment_provider'), nullable=False, server_default='stripe'),
        sa.Column('provider_intent_id', sa.String(255), nullable=True, unique=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('status', sa.Enum('created', 'pending', 'succeeded', 'failed', 'cancelled', name='intent_status'), nullable=False, server_default='created'),
        sa.Column('metadata', JSONB, nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Indexes for paycore_intents
    op.create_index('idx_paycore_intents_tenant', 'paycore_intents', ['tenant_id'])
    op.create_index('idx_paycore_intents_status', 'paycore_intents', ['status'])
    op.create_index('idx_paycore_intents_provider_id', 'paycore_intents', ['provider', 'provider_intent_id'])

    # Table: paycore_transactions
    op.create_table(
        'paycore_transactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('intent_id', UUID(as_uuid=True), sa.ForeignKey('paycore_intents.id'), nullable=False),
        sa.Column('event_type', sa.Enum('payment_succeeded', 'payment_failed', 'payment_cancelled', 'refund_succeeded', 'refund_failed', name='transaction_event_type'), nullable=False),
        sa.Column('provider_event_id', sa.String(255), nullable=False, unique=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('provider_data', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Indexes for paycore_transactions
    op.create_index('idx_paycore_transactions_intent', 'paycore_transactions', ['intent_id'])
    op.create_index('idx_paycore_transactions_event_type', 'paycore_transactions', ['event_type'])
    op.create_index('idx_paycore_transactions_provider_event', 'paycore_transactions', ['provider_event_id'])

    # Table: paycore_refunds
    op.create_table(
        'paycore_refunds',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('intent_id', UUID(as_uuid=True), sa.ForeignKey('paycore_intents.id'), nullable=False),
        sa.Column('transaction_id', UUID(as_uuid=True), sa.ForeignKey('paycore_transactions.id'), nullable=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(500), nullable=True),
        sa.Column('status', sa.Enum('requested', 'processing', 'succeeded', 'failed', name='refund_status'), nullable=False, server_default='requested'),
        sa.Column('requested_by', sa.String(100), nullable=False),
        sa.Column('approved_by', sa.String(100), nullable=True),
        sa.Column('provider_refund_id', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Indexes for paycore_refunds
    op.create_index('idx_paycore_refunds_intent', 'paycore_refunds', ['intent_id'])
    op.create_index('idx_paycore_refunds_status', 'paycore_refunds', ['status'])

    # Table: paycore_revenue_daily (optional, for analytics)
    op.create_table(
        'paycore_revenue_daily',
        sa.Column('date', sa.Date(), primary_key=True),
        sa.Column('tenant_id', sa.String(100), primary_key=True),
        sa.Column('total_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='EUR'),
        sa.Column('transaction_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('refund_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('refund_total_cents', sa.Integer(), nullable=False, server_default='0'),
    )

    # Indexes for paycore_revenue_daily
    op.create_index('idx_paycore_revenue_date', 'paycore_revenue_daily', ['date'])
    op.create_index('idx_paycore_revenue_tenant', 'paycore_revenue_daily', ['tenant_id'])


def downgrade() -> None:
    """
    Drop PayCore tables.
    """
    # Drop tables
    op.drop_table('paycore_revenue_daily')
    op.drop_table('paycore_refunds')
    op.drop_table('paycore_transactions')
    op.drop_table('paycore_intents')

    # Drop enums
    op.execute("DROP TYPE IF EXISTS refund_status")
    op.execute("DROP TYPE IF EXISTS transaction_event_type")
    op.execute("DROP TYPE IF EXISTS intent_status")
    op.execute("DROP TYPE IF EXISTS payment_provider")
