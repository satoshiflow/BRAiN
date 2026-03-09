from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class InsightCandidateModel(Base):
    __tablename__ = "insight_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    experience_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="proposed", index=True)
    confidence = Column(Float, nullable=False, default=0.5)
    scope = Column(String(40), nullable=False, default="skill_run")
    hypothesis = Column(Text, nullable=False)
    evidence = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_insight_candidates_tenant_run", "tenant_id", "skill_run_id"),
    )
