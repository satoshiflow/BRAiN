"""
PayCore Pydantic Schemas

API request/response models for PayCore endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================

class PaymentProvider(str, Enum):
    """Supported payment providers"""
    STRIPE = "stripe"
    PAYPAL = "paypal"
    CRYPTO = "crypto"


class IntentStatus(str, Enum):
    """Payment intent status"""
    CREATED = "created"
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RefundStatus(str, Enum):
    """Refund status"""
    REQUESTED = "requested"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TransactionEventType(str, Enum):
    """Transaction event types"""
    PAYMENT_SUCCEEDED = "payment_succeeded"
    PAYMENT_FAILED = "payment_failed"
    PAYMENT_CANCELLED = "payment_cancelled"
    REFUND_SUCCEEDED = "refund_succeeded"
    REFUND_FAILED = "refund_failed"


# ============================================================================
# Module Info
# ============================================================================

class PayCoreInfo(BaseModel):
    """PayCore module information"""
    name: str = "PayCore"
    version: str = "1.0.0"
    description: str = "Payment processing infrastructure for BRAiN"
    supported_providers: list[str] = ["stripe", "paypal"]
    features: list[str] = [
        "Multi-provider support",
        "Append-only ledger",
        "Event-driven architecture",
        "Policy-based refunds",
        "Webhook idempotency"
    ]


class PayCoreHealth(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: datetime
    providers: Dict[str, bool] = {}


# ============================================================================
# Payment Intent
# ============================================================================

class IntentCreateRequest(BaseModel):
    """Request to create payment intent"""
    amount_cents: int = Field(..., gt=0, description="Amount in cents (e.g., 5000 = 50.00 EUR)")
    currency: str = Field(default="EUR", description="ISO currency code")
    provider: PaymentProvider = Field(default=PaymentProvider.STRIPE)
    user_id: Optional[str] = Field(None, description="User ID (optional)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom metadata (course_id, product_type, etc.)")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency is uppercase 3-letter code"""
        if len(v) != 3:
            raise ValueError("Currency must be 3-letter ISO code")
        return v.upper()


class IntentCreateResponse(BaseModel):
    """Response from creating payment intent"""
    intent_id: UUID
    provider: PaymentProvider
    provider_intent_id: Optional[str] = None
    status: IntentStatus
    amount_cents: int
    currency: str
    checkout_url: Optional[str] = None  # For hosted checkout flows
    client_secret: Optional[str] = None  # For custom checkout flows
    created_at: datetime


class IntentStatusResponse(BaseModel):
    """Response for intent status query"""
    intent_id: UUID
    status: IntentStatus
    amount_cents: int
    currency: str
    provider: PaymentProvider
    provider_intent_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Refunds
# ============================================================================

class RefundCreateRequest(BaseModel):
    """Request to create refund"""
    intent_id: UUID
    amount_cents: int = Field(..., gt=0, description="Refund amount in cents")
    reason: Optional[str] = Field(None, max_length=500, description="Reason for refund")


class RefundCreateResponse(BaseModel):
    """Response from creating refund"""
    refund_id: UUID
    intent_id: UUID
    status: RefundStatus
    amount_cents: int
    reason: Optional[str] = None
    requested_by: str
    approved_by: Optional[str] = None
    created_at: datetime


class RefundStatusResponse(BaseModel):
    """Response for refund status query"""
    refund_id: UUID
    intent_id: UUID
    status: RefundStatus
    amount_cents: int
    reason: Optional[str] = None
    provider_refund_id: Optional[str] = None
    requested_by: str
    approved_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Transactions
# ============================================================================

class TransactionRecord(BaseModel):
    """Transaction ledger record"""
    transaction_id: UUID
    intent_id: UUID
    event_type: TransactionEventType
    amount_cents: int
    currency: str
    provider_event_id: str
    created_at: datetime


# ============================================================================
# Revenue
# ============================================================================

class RevenueDailyResponse(BaseModel):
    """Daily revenue aggregation"""
    date: str  # ISO date format
    tenant_id: str
    total_cents: int
    currency: str
    transaction_count: int
    refund_count: int
    refund_total_cents: int


# ============================================================================
# Webhooks
# ============================================================================

class WebhookHandleResponse(BaseModel):
    """Response from webhook handler"""
    success: bool
    event_id: str
    event_type: str
    processed: bool  # False if already processed (idempotent)
    intent_id: Optional[UUID] = None
    transaction_id: Optional[UUID] = None


# ============================================================================
# Provider Layer (internal)
# ============================================================================

class ProviderIntent(BaseModel):
    """Provider-agnostic intent representation"""
    provider_intent_id: str
    status: IntentStatus
    amount_cents: int
    currency: str
    checkout_url: Optional[str] = None
    client_secret: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None


class ProviderRefund(BaseModel):
    """Provider-agnostic refund representation"""
    provider_refund_id: str
    status: RefundStatus
    amount_cents: int
    raw_data: Optional[Dict[str, Any]] = None
