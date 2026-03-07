"""Persistence models for Immune Orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class ImmuneSignalModel(Base):
    __tablename__ = "immune_orchestrator_signals"

    id = Column(String(128), primary_key=True)
    type = Column(String(128), nullable=False, index=True)
    source = Column(String(128), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)
    entity = Column(String(256), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    context = Column(JSONB, nullable=False, default=dict)
    correlation_id = Column(String(128), nullable=True, index=True)
    blast_radius = Column(Integer, nullable=False, default=1)
    confidence = Column(Float, nullable=False, default=0.5)
    recurrence = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class ImmuneDecisionModel(Base):
    __tablename__ = "immune_orchestrator_decisions"

    decision_id = Column(String(128), primary_key=True)
    signal_id = Column(String(128), nullable=False, index=True)
    action = Column(String(32), nullable=False, index=True)
    priority_score = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)
    requires_governance_hook = Column(String(5), nullable=False, default="false")
    correlation_id = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False)


class ImmuneAuditModel(Base):
    __tablename__ = "immune_orchestrator_audit"

    audit_id = Column(String(128), primary_key=True)
    event_type = Column(String(128), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    action = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False)
    resource_type = Column(String(128), nullable=False)
    resource_id = Column(String(256), nullable=False, index=True)
    correlation_id = Column(String(128), nullable=True, index=True)
    details = Column(JSONB, nullable=False, default=dict)
    timestamp = Column(DateTime, nullable=False)
