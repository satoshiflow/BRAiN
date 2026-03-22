from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SkillRunModel(Base):
    __tablename__ = "skill_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    skill_key = Column(String(120), nullable=False, index=True)
    skill_version = Column(Integer, nullable=False)
    state = Column(String(32), nullable=False, default="queued", index=True)
    input_payload = Column(JSONB, nullable=False, default=dict)
    plan_snapshot = Column(JSONB, nullable=False, default=dict)
    provider_selection_snapshot = Column(JSONB, nullable=False, default=dict)
    requested_by = Column(String(120), nullable=False)
    requested_by_type = Column(String(32), nullable=False)
    trigger_type = Column(String(32), nullable=False, default="api")
    policy_decision_id = Column(UUID(as_uuid=True), nullable=True)
    policy_decision = Column(JSONB, nullable=False, default=dict)
    policy_snapshot = Column(JSONB, nullable=False, default=dict)
    risk_tier = Column(String(32), nullable=False, default="medium")
    correlation_id = Column(String(160), nullable=False, index=True)
    causation_id = Column(String(160), nullable=True)
    idempotency_key = Column(String(160), nullable=False)
    mission_id = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    deadline_at = Column(DateTime(timezone=True), nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    state_sequence = Column(Integer, nullable=False, default=0)
    state_changed_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    cost_estimate = Column(Float, nullable=True)
    cost_actual = Column(Float, nullable=True)
    output_payload = Column(JSONB, nullable=False, default=dict)
    input_artifact_refs = Column(JSONB, nullable=False, default=list)
    output_artifact_refs = Column(JSONB, nullable=False, default=list)
    evidence_artifact_refs = Column(JSONB, nullable=False, default=list)
    evaluation_summary = Column(JSONB, nullable=False, default=dict)
    failure_code = Column(String(40), nullable=True)
    failure_reason_sanitized = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_skill_runs_tenant_skill_state", "tenant_id", "skill_key", "state"),
        Index("ix_skill_runs_idempotency", "tenant_id", "requested_by", "idempotency_key"),
    )
