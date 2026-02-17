"""
PayCore SQLAlchemy Models

Database schema for payment processing:
- PaymentIntent: Checkout sessions
- Transaction: Append-only ledger
- Refund: Refund records
- RevenueDaily: Aggregation table (optional)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Index,
    JSON,
    Date,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()


# ============================================================================
# Payment Intent
# ============================================================================

class PaymentIntent(Base):
    """
    Payment checkout session.

    Represents a single payment intent that can go through states:
    created → pending → succeeded/failed/cancelled
    """
    __tablename__ = "paycore_intents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=True)

    # Provider details
    provider = Column(
        SQLEnum("stripe", "paypal", "crypto", name="payment_provider"),
        nullable=False,
        default="stripe"
    )
    provider_intent_id = Column(String(255), nullable=True, unique=True)

    # Amount details
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")

    # Status tracking
    status = Column(
        SQLEnum(
            "created",
            "pending",
            "succeeded",
            "failed",
            "cancelled",
            name="intent_status"
        ),
        nullable=False,
        default="created"
    )

    # Metadata (course_id, product_type, etc.)
    payment_metadata = Column(JSONB, nullable=True, default={})

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_paycore_intents_tenant", "tenant_id"),
        Index("idx_paycore_intents_status", "status"),
        Index("idx_paycore_intents_provider_id", "provider", "provider_intent_id"),
    )


# ============================================================================
# Transaction Ledger
# ============================================================================

class Transaction(Base):
    """
    Append-only transaction ledger.

    Records all payment events for audit trail and reconciliation.
    Each transaction is immutable once created.
    """
    __tablename__ = "paycore_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("paycore_intents.id"), nullable=False)

    # Event details
    event_type = Column(
        SQLEnum(
            "payment_succeeded",
            "payment_failed",
            "payment_cancelled",
            "refund_succeeded",
            "refund_failed",
            name="transaction_event_type"
        ),
        nullable=False
    )

    # Idempotency key (provider webhook event ID)
    provider_event_id = Column(String(255), nullable=False, unique=True)

    # Amount details
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False, default="EUR")

    # Raw provider data (for debugging/reconciliation)
    provider_data = Column(JSONB, nullable=True)

    # Timestamp (append-only, no updates)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_paycore_transactions_intent", "intent_id"),
        Index("idx_paycore_transactions_event_type", "event_type"),
        Index("idx_paycore_transactions_provider_event", "provider_event_id"),
    )


# ============================================================================
# Refunds
# ============================================================================

class Refund(Base):
    """
    Refund records.

    Tracks refund requests with approval workflow for high-value refunds.
    """
    __tablename__ = "paycore_refunds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    intent_id = Column(UUID(as_uuid=True), ForeignKey("paycore_intents.id"), nullable=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("paycore_transactions.id"), nullable=True)

    # Refund details
    amount_cents = Column(Integer, nullable=False)
    reason = Column(String(500), nullable=True)

    # Status tracking
    status = Column(
        SQLEnum(
            "requested",
            "processing",
            "succeeded",
            "failed",
            name="refund_status"
        ),
        nullable=False,
        default="requested"
    )

    # Approval workflow
    requested_by = Column(String(100), nullable=False)
    approved_by = Column(String(100), nullable=True)

    # Provider refund ID
    provider_refund_id = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("idx_paycore_refunds_intent", "intent_id"),
        Index("idx_paycore_refunds_status", "status"),
    )


# ============================================================================
# Revenue Aggregation (Optional)
# ============================================================================

class RevenueDaily(Base):
    """
    Daily revenue aggregation.

    Pre-computed daily metrics for analytics and reporting.
    """
    __tablename__ = "paycore_revenue_daily"

    date = Column(Date, primary_key=True)
    tenant_id = Column(String(100), primary_key=True)

    # Revenue metrics
    total_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String(3), nullable=False, default="EUR")

    # Transaction counts
    transaction_count = Column(Integer, nullable=False, default=0)
    refund_count = Column(Integer, nullable=False, default=0)
    refund_total_cents = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("idx_paycore_revenue_date", "date"),
        Index("idx_paycore_revenue_tenant", "tenant_id"),
    )
