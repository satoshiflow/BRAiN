from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EconomyAssessmentModel(Base):
    __tablename__ = "economy_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    discovery_proposal_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="draft", index=True)
    confidence_score = Column(Float, nullable=False, default=0.0)
    frequency_score = Column(Float, nullable=False, default=0.0)
    impact_score = Column(Float, nullable=False, default=0.0)
    cost_score = Column(Float, nullable=False, default=0.0)
    weighted_score = Column(Float, nullable=False, default=0.0, index=True)
    score_breakdown = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "discovery_proposal_id",
            name="uq_economy_assessments_tenant_discovery_proposal",
        ),
        Index("ix_economy_assessments_tenant_status", "tenant_id", "status"),
    )
