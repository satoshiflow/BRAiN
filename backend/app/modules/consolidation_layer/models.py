from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PatternCandidateModel(Base):
    __tablename__ = "pattern_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    insight_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="proposed", index=True)
    confidence = Column(Float, nullable=False, default=0.5)
    recurrence_support = Column(Float, nullable=False, default=0.0)
    pattern_summary = Column(Text, nullable=False)
    failure_modes = Column(JSONB, nullable=False, default=list)
    evidence = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_pattern_candidates_tenant_run", "tenant_id", "skill_run_id"),
    )
