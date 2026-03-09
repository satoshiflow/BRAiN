from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SkillGapModel(Base):
    __tablename__ = "skill_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pattern_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    gap_type = Column(String(40), nullable=False, default="skill")
    summary = Column(Text, nullable=False)
    severity = Column(String(24), nullable=False, default="medium")
    confidence = Column(Float, nullable=False, default=0.5)
    evidence = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (Index("ix_skill_gaps_tenant_run", "tenant_id", "skill_run_id"),)


class CapabilityGapModel(Base):
    __tablename__ = "capability_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pattern_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    capability_key = Column(String(160), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    severity = Column(String(24), nullable=False, default="medium")
    confidence = Column(Float, nullable=False, default=0.5)
    evidence = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_capability_gaps_tenant_run", "tenant_id", "skill_run_id"),
    )


class SkillProposalModel(Base):
    __tablename__ = "discovery_skill_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=False, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    pattern_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    skill_gap_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    capability_gap_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    target_skill_key = Column(String(160), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="draft", index=True)
    proposal_summary = Column(Text, nullable=False)
    proposal_evidence = Column(JSONB, nullable=False, default=dict)
    dedup_key = Column(String(255), nullable=False, default="", index=True)
    evidence_score = Column(Float, nullable=False, default=0.0)
    priority_score = Column(Float, nullable=False, default=0.0, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "skill_run_id", name="uq_discovery_skill_proposals_tenant_run"
        ),
        UniqueConstraint(
            "tenant_id", "dedup_key", name="uq_discovery_skill_proposals_tenant_dedup"
        ),
        Index("ix_discovery_proposals_tenant_run", "tenant_id", "skill_run_id"),
    )
