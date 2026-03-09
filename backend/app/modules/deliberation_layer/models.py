from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DeliberationSummaryModel(Base):
    __tablename__ = "deliberation_summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    mission_id = Column(String(120), nullable=False, index=True)
    alternatives = Column(JSONB, nullable=False, default=list)
    rationale_summary = Column(Text, nullable=False)
    uncertainty = Column(Float, nullable=False, default=0.0)
    open_tensions = Column(JSONB, nullable=False, default=list)
    evidence = Column(JSONB, nullable=False, default=dict)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_deliberation_summaries_tenant_mission", "tenant_id", "mission_id"),
    )


class MissionTensionModel(Base):
    __tablename__ = "mission_tensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    mission_id = Column(String(120), nullable=False, index=True)
    hypothesis = Column(Text, nullable=False)
    perspective = Column(Text, nullable=False)
    tension = Column(Text, nullable=False)
    status = Column(String(24), nullable=False, default="open", index=True)
    evidence = Column(JSONB, nullable=False, default=dict)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_mission_tensions_tenant_mission", "tenant_id", "mission_id"),
    )
