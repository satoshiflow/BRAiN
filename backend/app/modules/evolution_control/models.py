from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvolutionProposalModel(Base):
    __tablename__ = "evolution_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    pattern_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="draft", index=True)
    target_skill_key = Column(String(160), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    governance_required = Column(String(16), nullable=False, default="true")
    validation_state = Column(String(32), nullable=False, default="required")
    proposal_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "pattern_id", name="uq_evolution_proposals_tenant_pattern"
        ),
        Index("ix_evolution_proposals_tenant_run", "tenant_id", "skill_run_id"),
    )


class EvolutionControlFlagModel(Base):
    __tablename__ = "evolution_control_flags"

    tenant_id = Column(String(64), primary_key=True)
    adaptive_frozen = Column(String(8), nullable=False, default="false")
    freeze_reason = Column(Text, nullable=True)
    frozen_by = Column(String(120), nullable=True)
    frozen_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
