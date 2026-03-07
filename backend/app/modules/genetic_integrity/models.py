"""Persistence models for Genetic Integrity module."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class GeneticSnapshotRecordModel(Base):
    __tablename__ = "genetic_integrity_snapshots"

    record_id = Column(String(128), primary_key=True)
    agent_id = Column(String(128), nullable=False, index=True)
    snapshot_version = Column(Integer, nullable=False, index=True)
    parent_snapshot = Column(Integer, nullable=True)
    payload_hash = Column(String(128), nullable=False)
    parent_hash = Column(String(128), nullable=True)
    correlation_id = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class GeneticMutationAuditModel(Base):
    __tablename__ = "genetic_integrity_mutations"

    audit_id = Column(String(128), primary_key=True)
    agent_id = Column(String(128), nullable=False, index=True)
    from_version = Column(Integer, nullable=False)
    to_version = Column(Integer, nullable=False)
    actor = Column(String(128), nullable=False)
    reason = Column(Text, nullable=False)
    mutation = Column(JSONB, nullable=False, default=dict)
    requires_governance_hook = Column(String(5), nullable=False, default="false")
    correlation_id = Column(String(128), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class GeneticAuditModel(Base):
    __tablename__ = "genetic_integrity_audit"

    audit_id = Column(String(128), primary_key=True)
    event_type = Column(String(128), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    resource_type = Column(String(128), nullable=False)
    resource_id = Column(String(256), nullable=False, index=True)
    details = Column(JSONB, nullable=False, default=dict)
    timestamp = Column(DateTime, nullable=False)
