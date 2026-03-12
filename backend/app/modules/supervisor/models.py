"""Persistence models for supervisor module."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DomainEscalationModel(Base):
    __tablename__ = "domain_escalations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    domain_key = Column(String(100), nullable=False, index=True)
    requested_by = Column(String(120), nullable=False, index=True)
    requested_by_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, default="queued", index=True)
    reason = Column(Text, nullable=False)
    reasons = Column(JSONB, nullable=False, default=list)
    recommended_next_actions = Column(JSONB, nullable=False, default=list)
    risk_tier = Column(String(32), nullable=False, default="high")
    correlation_id = Column(String(160), nullable=True, index=True)
    context = Column(JSONB, nullable=False, default=dict)
    reviewed_by = Column(String(120), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    decision_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_domain_escalations_tenant_created", "tenant_id", "created_at"),
    )
