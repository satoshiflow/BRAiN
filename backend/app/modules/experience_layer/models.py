from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ExperienceRecordModel(Base):
    __tablename__ = "experience_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    idempotency_key = Column(String(160), nullable=False, unique=True)
    state = Column(String(32), nullable=False, index=True)
    failure_code = Column(String(40), nullable=True)
    summary = Column(Text, nullable=False)
    evaluation_summary = Column(JSONB, nullable=False, default=dict)
    signals = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_experience_records_tenant_run", "tenant_id", "skill_run_id"),
    )
