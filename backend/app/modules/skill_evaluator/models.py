from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EvaluationResultModel(Base):
    __tablename__ = "evaluation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    skill_run_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    skill_key = Column(String(120), nullable=False, index=True)
    skill_version = Column(Integer, nullable=False)
    evaluator_type = Column(String(32), nullable=False, default="rule")
    status = Column(String(32), nullable=False, default="completed", index=True)
    overall_score = Column(Float, nullable=True)
    dimension_scores = Column(JSONB, nullable=False, default=dict)
    passed = Column(Boolean, nullable=False, default=True)
    criteria_snapshot = Column(JSONB, nullable=False, default=dict)
    findings = Column(JSONB, nullable=False, default=dict)
    recommendations = Column(JSONB, nullable=False, default=dict)
    metrics_summary = Column(JSONB, nullable=False, default=dict)
    provider_selection_snapshot = Column(JSONB, nullable=False, default=dict)
    error_classification = Column(String(32), nullable=True)
    policy_compliance = Column(String(32), nullable=False, default="unknown")
    policy_violations = Column(JSONB, nullable=False, default=list)
    correlation_id = Column(String(160), nullable=True, index=True)
    evaluation_revision = Column(Integer, nullable=False, default=1)
    revision_of_id = Column(UUID(as_uuid=True), nullable=True)
    evidence_artifact_refs = Column(JSONB, nullable=False, default=list)
    review_artifact_refs = Column(JSONB, nullable=False, default=list)
    comparison_artifact_refs = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(120), nullable=False)

    __table_args__ = (
        Index("ix_evaluation_results_run_status", "skill_run_id", "status"),
        Index("ix_evaluation_results_skill_version", "tenant_id", "skill_key", "skill_version"),
    )
