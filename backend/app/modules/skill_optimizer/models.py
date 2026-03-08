from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SkillOptimizerRecommendationModel(Base):
    __tablename__ = "skill_optimizer_recommendations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    skill_key = Column(String(120), nullable=False, index=True)
    skill_version = Column(Integer, nullable=False)
    recommendation_type = Column(String(64), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    status = Column(String(32), nullable=False, default="open")
    rationale = Column(Text, nullable=False)
    evidence = Column(JSONB, nullable=False, default=dict)
    source_snapshot = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_by = Column(String(120), nullable=False, default="skill_optimizer")

    __table_args__ = (
        Index("ix_skill_optimizer_recommendations_skill", "tenant_id", "skill_key", "skill_version"),
    )
