"""Persistence models for Unified Recovery Policy Engine."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class RecoveryRequestModel(Base):
    __tablename__ = "recovery_policy_requests"

    id = Column(String(128), primary_key=True)
    source = Column(String(128), nullable=False, index=True)
    entity_id = Column(String(256), nullable=False, index=True)
    failure_type = Column(String(128), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)
    retry_count = Column(Integer, nullable=False, default=0)
    recurrence = Column(Integer, nullable=False, default=0)
    context = Column(JSONB, nullable=False, default=dict)
    correlation_id = Column(String(128), nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class RecoveryDecisionModel(Base):
    __tablename__ = "recovery_policy_decisions"

    decision_id = Column(String(128), primary_key=True)
    request_id = Column(String(128), nullable=False, index=True)
    action = Column(String(32), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    cooldown_seconds = Column(Integer, nullable=False, default=0)
    requires_governance_hook = Column(String(5), nullable=False, default="false")
    correlation_id = Column(String(128), nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False)


class RecoveryAuditModel(Base):
    __tablename__ = "recovery_policy_audit"

    audit_id = Column(String(128), primary_key=True)
    event_type = Column(String(128), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    action = Column(String(64), nullable=False, index=True)
    request_id = Column(String(128), nullable=False, index=True)
    correlation_id = Column(String(128), nullable=True, index=True)
    details = Column(JSONB, nullable=False, default=dict)
    timestamp = Column(DateTime, nullable=False)
