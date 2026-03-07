"""Persistence models for OpenCode repair loop."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class OpenCodeRepairTicketModel(Base):
    __tablename__ = "opencode_repair_tickets"

    ticket_id = Column(String(128), primary_key=True)
    source_module = Column(String(128), nullable=False, index=True)
    source_event_type = Column(String(128), nullable=False, index=True)
    title = Column(String(256), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    correlation_id = Column(String(128), nullable=True, index=True)
    actor = Column(String(128), nullable=False)
    governance_required = Column(Boolean, nullable=False, default=False)
    evidence = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class OpenCodeRepairAuditModel(Base):
    __tablename__ = "opencode_repair_audit"

    audit_id = Column(String(128), primary_key=True)
    ticket_id = Column(String(128), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    actor = Column(String(128), nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
    correlation_id = Column(String(128), nullable=True, index=True)
    timestamp = Column(DateTime, nullable=False)
