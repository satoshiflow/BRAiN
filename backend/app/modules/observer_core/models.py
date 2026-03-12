from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ObserverSignalModel(Base):
    __tablename__ = "observer_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    source_module = Column(String(120), nullable=False, index=True)
    source_event_type = Column(String(160), nullable=False)
    source_event_id = Column(String(160), nullable=True)
    correlation_id = Column(String(160), nullable=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(String(160), nullable=False, index=True)
    signal_class = Column(String(32), nullable=False, index=True)
    severity = Column(String(16), nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    ingested_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    payload = Column(JSONB, nullable=False, default=dict)
    payload_hash = Column(String(64), nullable=False)
    ordering_key = Column(String(160), nullable=True)
    idempotency_key = Column(String(255), nullable=False, unique=True)

    __table_args__ = (
        Index("ix_observer_signals_tenant_occurred", "tenant_id", "occurred_at"),
        Index("ix_observer_signals_tenant_source", "tenant_id", "source_module", "occurred_at"),
    )


class ObserverStateModel(Base):
    __tablename__ = "observer_state_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    scope_type = Column(String(32), nullable=False, default="tenant_global")
    scope_entity_type = Column(String(64), nullable=False, default="")
    scope_entity_id = Column(String(160), nullable=False, default="")
    snapshot_version = Column(Integer, nullable=False, default=1)
    last_signal_id = Column(UUID(as_uuid=True), nullable=True)
    last_occurred_at = Column(DateTime(timezone=True), nullable=True)
    health_summary = Column(JSONB, nullable=False, default=dict)
    risk_summary = Column(JSONB, nullable=False, default=dict)
    execution_summary = Column(JSONB, nullable=False, default=dict)
    queue_summary = Column(JSONB, nullable=False, default=dict)
    audit_refs = Column(JSONB, nullable=False, default=list)
    snapshot_payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "scope_type",
            "scope_entity_type",
            "scope_entity_id",
            name="uq_observer_state_scope",
        ),
        Index("ix_observer_state_tenant_scope", "tenant_id", "scope_type"),
        Index("ix_observer_state_tenant_entity", "tenant_id", "scope_entity_type", "scope_entity_id"),
    )
