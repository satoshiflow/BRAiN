"""
Credit System Models

Pydantic models and database ORM models for the credit system.
Implements the data structures defined in brain_credit_selection_spec.v1.yaml

Philosophy:
- Credits are "energy", not currency
- Append-only ledger ensures immutability
- Deterministic calculations ensure reproducibility
- Fail-closed security prevents silent failures
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import BigInteger, CheckConstraint, Column, DateTime, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# ============================================================================
# ENUMS
# ============================================================================


class CreditType(str, Enum):
    """Credit type enumeration."""

    COMPUTE_CREDITS = "CC"  # CPU and memory
    LLM_CREDITS = "LC"  # LLM API tokens
    STORAGE_CREDITS = "SC"  # Persistent storage
    NETWORK_CREDITS = "NC"  # Network I/O and external APIs


class TransactionType(str, Enum):
    """Transaction type enumeration."""

    MINT = "MINT"  # Create new credits (system-only)
    BURN = "BURN"  # Destroy credits (consumption)
    TRANSFER = "TRANSFER"  # Move credits between entities
    TAX = "TAX"  # Existence tax collection


class EntityType(str, Enum):
    """Entity type enumeration."""

    AGENT = "AGENT"
    MISSION = "MISSION"
    SYSTEM = "SYSTEM"


class AgentStatus(str, Enum):
    """Agent lifecycle status."""

    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class AuditResult(str, Enum):
    """Audit event result."""

    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    DENIED = "DENIED"


# ============================================================================
# DATABASE MODELS
# ============================================================================


class CreditLedger(Base):
    """
    Append-only credit transaction ledger.

    CRITICAL SECURITY PROPERTIES:
    - NO UPDATE operations allowed (append-only)
    - NO DELETE operations allowed (immutable)
    - Monotonically increasing sequence_number ensures ordering
    - Cryptographic signature prevents tampering
    """

    __tablename__ = "credit_ledger"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    sequence_number = Column(BigInteger, autoincrement=True, unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    entity_id = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    credit_type = Column(String(50), nullable=False, index=True)

    amount = Column(Numeric(20, 6), nullable=False)
    balance_after = Column(Numeric(20, 6), nullable=False)

    transaction_type = Column(String(50), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    metadata = Column(JSONB, nullable=False, server_default="{}")
    signature = Column(String(255), nullable=False)

    __table_args__ = (
        CheckConstraint("entity_type IN ('AGENT', 'MISSION', 'SYSTEM')", name="ck_entity_type"),
        CheckConstraint("credit_type IN ('CC', 'LC', 'SC', 'NC')", name="ck_credit_type"),
        CheckConstraint(
            "transaction_type IN ('MINT', 'BURN', 'TRANSFER', 'TAX')", name="ck_transaction_type"
        ),
        Index("idx_ledger_entity_time", "entity_id", "timestamp"),
        Index("idx_ledger_sequence", "sequence_number", unique=True),
        Index("idx_ledger_credit_type", "credit_type", "timestamp"),
    )


class AgentRegistry(Base):
    """
    Extended agent registry with lifecycle tracking and credit balances.

    Maintains cached credit balances for performance.
    Source of truth is still the credit_ledger.
    """

    __tablename__ = "agent_registry"

    agent_id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    agent_name = Column(String(255), nullable=False, unique=True)
    agent_type = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, server_default="ACTIVE", index=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    activated_at = Column(DateTime(timezone=True), nullable=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    terminated_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    # Cached credit balances (performance optimization)
    credit_balance_cc = Column(Numeric(20, 6), nullable=False, server_default="0.0")
    credit_balance_lc = Column(Numeric(20, 6), nullable=False, server_default="0.0")
    credit_balance_sc = Column(Numeric(20, 6), nullable=False, server_default="0.0")
    credit_balance_nc = Column(Numeric(20, 6), nullable=False, server_default="0.0")

    # Lifetime statistics
    total_credits_earned = Column(Numeric(20, 6), nullable=False, server_default="0.0")
    total_credits_spent = Column(Numeric(20, 6), nullable=False, server_default="0.0")

    metadata = Column(JSONB, nullable=False, server_default="{}")

    __table_args__ = (
        CheckConstraint("status IN ('ACTIVE', 'SUSPENDED', 'TERMINATED')", name="ck_agent_status"),
        Index("idx_agent_status", "status"),
        Index("idx_agent_type", "agent_type"),
        Index("idx_agent_created", "created_at"),
        Index("idx_agent_last_activity", "last_activity_at"),
    )


class AuditTrail(Base):
    """
    Comprehensive audit trail for all credit and lifecycle events.

    Ensures complete traceability and tamper detection.
    """

    __tablename__ = "audit_trail"

    id = Column(PGUUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    event_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(255), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    actor_id = Column(String(255), nullable=False, index=True)

    action = Column(Text, nullable=False)
    result = Column(String(50), nullable=False, index=True)
    metadata = Column(JSONB, nullable=False, server_default="{}")
    signature = Column(String(255), nullable=False)

    __table_args__ = (
        CheckConstraint("result IN ('SUCCESS', 'FAILURE', 'DENIED')", name="ck_audit_result"),
        Index("idx_audit_timestamp", "timestamp"),
        Index("idx_audit_entity", "entity_id", "timestamp"),
        Index("idx_audit_event_type", "event_type"),
    )


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================


class CreditBalance(BaseModel):
    """Current credit balances for an entity."""

    entity_id: str
    entity_type: EntityType
    compute_credits: Decimal = Field(default=Decimal("0.0"), ge=0)
    llm_credits: Decimal = Field(default=Decimal("0.0"), ge=0)
    storage_credits: Decimal = Field(default=Decimal("0.0"), ge=0)
    network_credits: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_earned: Decimal = Field(default=Decimal("0.0"), ge=0)
    total_spent: Decimal = Field(default=Decimal("0.0"), ge=0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        json_schema_extra = {
            "example": {
                "entity_id": "agent_001",
                "entity_type": "AGENT",
                "compute_credits": "950.500000",
                "llm_credits": "1000.000000",
                "storage_credits": "999.900000",
                "network_credits": "1000.000000",
                "total_earned": "4000.000000",
                "total_spent": "49.500000",
                "last_updated": "2025-12-21T10:00:00Z",
            }
        }


class CreditTransaction(BaseModel):
    """A single credit transaction."""

    id: UUID = Field(default_factory=uuid4)
    sequence_number: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    entity_id: str
    entity_type: EntityType
    credit_type: CreditType

    amount: Decimal
    balance_after: Decimal

    transaction_type: TransactionType
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    signature: str

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount is not zero."""
        if v == 0:
            raise ValueError("Transaction amount cannot be zero")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "sequence_number": 12345,
                "timestamp": "2025-12-21T10:00:00Z",
                "entity_id": "agent_001",
                "entity_type": "AGENT",
                "credit_type": "CC",
                "amount": "-5.000000",
                "balance_after": "950.500000",
                "transaction_type": "TAX",
                "reason": "Hourly existence tax",
                "metadata": {"hours_active": 1},
                "signature": "sha256:abcd1234...",
            }
        }


class AgentRegistryEntry(BaseModel):
    """Agent registry entry with lifecycle and credit information."""

    agent_id: UUID
    agent_name: str
    agent_type: str
    status: AgentStatus

    created_at: datetime
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    terminated_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    credit_balance_cc: Decimal = Decimal("0.0")
    credit_balance_lc: Decimal = Decimal("0.0")
    credit_balance_sc: Decimal = Decimal("0.0")
    credit_balance_nc: Decimal = Decimal("0.0")

    total_credits_earned: Decimal = Decimal("0.0")
    total_credits_spent: Decimal = Decimal("0.0")

    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "agent_id": "550e8400-e29b-41d4-a716-446655440000",
                "agent_name": "coder_agent_001",
                "agent_type": "CODER",
                "status": "ACTIVE",
                "created_at": "2025-12-21T09:00:00Z",
                "activated_at": "2025-12-21T09:00:00Z",
                "suspended_at": None,
                "terminated_at": None,
                "last_activity_at": "2025-12-21T10:00:00Z",
                "credit_balance_cc": "950.500000",
                "credit_balance_lc": "1000.000000",
                "credit_balance_sc": "999.900000",
                "credit_balance_nc": "1000.000000",
                "total_credits_earned": "4000.000000",
                "total_credits_spent": "49.500000",
                "metadata": {},
            }
        }


class AuditEvent(BaseModel):
    """Audit trail event."""

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    event_type: str
    entity_id: str
    entity_type: EntityType
    actor_id: str

    action: str
    result: AuditResult
    metadata: dict[str, Any] = Field(default_factory=dict)
    signature: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "timestamp": "2025-12-21T10:00:00Z",
                "event_type": "CREDIT_MINT",
                "entity_id": "agent_001",
                "entity_type": "AGENT",
                "actor_id": "SYSTEM",
                "action": "Minted 1000.0 CC for agent creation",
                "result": "SUCCESS",
                "metadata": {"reason": "AGENT_CREATION_MINT"},
                "signature": "sha256:abcd1234...",
            }
        }


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class CreditAllocationRequest(BaseModel):
    """Request to allocate credits to an entity."""

    entity_id: str
    entity_type: EntityType
    allocation_reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreditSpendRequest(BaseModel):
    """Request to spend credits."""

    entity_id: str
    credit_type: CreditType
    amount: Decimal = Field(gt=0)
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("amount")
    @classmethod
    def validate_positive(cls, v: Decimal) -> Decimal:
        """Ensure amount is positive."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v


class CreditTransferRequest(BaseModel):
    """Request to transfer credits between entities."""

    from_entity_id: str
    to_entity_id: str
    credit_type: CreditType
    amount: Decimal = Field(gt=0)
    reason: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LedgerQueryParams(BaseModel):
    """Query parameters for ledger retrieval."""

    entity_id: Optional[str] = None
    credit_type: Optional[CreditType] = None
    transaction_type: Optional[TransactionType] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditQueryParams(BaseModel):
    """Query parameters for audit trail retrieval."""

    entity_id: Optional[str] = None
    event_type: Optional[str] = None
    actor_id: Optional[str] = None
    result: Optional[AuditResult] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
