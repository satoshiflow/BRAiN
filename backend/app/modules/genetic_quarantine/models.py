"""Persistence models for Genetic Quarantine Manager."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class GeneticQuarantineRecordModel(Base):
    __tablename__ = "genetic_quarantine_records"

    quarantine_id = Column(String(128), primary_key=True)
    agent_id = Column(String(128), nullable=False, index=True)
    snapshot_version = Column(Integer, nullable=False, index=True)
    state = Column(String(32), nullable=False, index=True)
    previous_state = Column(String(32), nullable=True)
    reason = Column(Text, nullable=False)
    severity = Column(String(32), nullable=False, index=True)
    source = Column(String(128), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    correlation_id = Column(String(128), nullable=True, index=True)
    context = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class GeneticQuarantineAuditModel(Base):
    __tablename__ = "genetic_quarantine_audit"

    audit_id = Column(String(128), primary_key=True)
    quarantine_id = Column(String(128), nullable=False, index=True)
    event_type = Column(String(128), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    correlation_id = Column(String(128), nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False)
