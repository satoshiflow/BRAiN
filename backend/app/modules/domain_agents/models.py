"""Database models for Domain Agent registry."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DomainAgentConfigModel(Base):
    __tablename__ = "domain_agent_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    owner_scope = Column(String(16), nullable=False, default="tenant")
    domain_key = Column(String(100), nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(32), nullable=False, default="draft", index=True)

    allowed_skill_keys = Column(JSONB, nullable=False, default=list)
    allowed_capability_keys = Column(JSONB, nullable=False, default=list)
    allowed_specialist_roles = Column(JSONB, nullable=False, default=list)
    review_profile = Column(JSONB, nullable=False, default=dict)
    risk_profile = Column(JSONB, nullable=False, default=dict)
    escalation_profile = Column(JSONB, nullable=False, default=dict)
    budget_profile = Column(JSONB, nullable=False, default=dict)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)

    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_domain_agent_configs_tenant_domain", "tenant_id", "domain_key"),
    )


class PurposeEvaluationModel(Base):
    __tablename__ = "purpose_evaluations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    decision_context_id = Column(String(160), nullable=False, index=True)
    purpose_profile_id = Column(String(120), nullable=False, index=True)
    outcome = Column(String(32), nullable=False, index=True)
    purpose_score = Column(Float, nullable=False, default=0.0)
    sovereignty_score = Column(Float, nullable=False, default=0.0)
    requires_human_review = Column(Boolean, nullable=False, default=False)
    required_modifications = Column(JSONB, nullable=False, default=list)
    reasons = Column(JSONB, nullable=False, default=list)
    governance_snapshot = Column(JSONB, nullable=False, default=dict)
    mission_id = Column(String(120), nullable=True, index=True)
    correlation_id = Column(String(160), nullable=True, index=True)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)


class RoutingDecisionModel(Base):
    __tablename__ = "routing_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    decision_context_id = Column(String(160), nullable=False, index=True)
    task_profile_id = Column(String(160), nullable=False, index=True)
    purpose_evaluation_id = Column(String(160), nullable=True, index=True)
    worker_candidates = Column(JSONB, nullable=False, default=list)
    filtered_candidates = Column(JSONB, nullable=False, default=list)
    scoring_breakdown = Column(JSONB, nullable=False, default=dict)
    selected_worker = Column(String(120), nullable=True, index=True)
    selected_skill_or_plan = Column(String(200), nullable=True)
    strategy = Column(String(64), nullable=False, default="single_worker")
    reasoning = Column(Text, nullable=False, default="")
    governance_snapshot = Column(JSONB, nullable=False, default=dict)
    mission_id = Column(String(120), nullable=True, index=True)
    correlation_id = Column(String(160), nullable=True, index=True)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_routing_decisions_tenant_context", "tenant_id", "decision_context_id"),
    )


class RoutingMemoryProjectionModel(Base):
    __tablename__ = "routing_memory_projections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    task_profile_id = Column(String(160), nullable=False, index=True)
    task_profile_fingerprint = Column(String(160), nullable=False, index=True)
    worker_outcome_history = Column(JSONB, nullable=False, default=list)
    summary_metrics = Column(JSONB, nullable=False, default=dict)
    routing_lessons = Column(JSONB, nullable=False, default=list)
    sample_size = Column(Integer, nullable=False, default=0)
    derived_from_runs = Column(JSONB, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "task_profile_fingerprint",
            name="uq_routing_memory_tenant_fingerprint",
        ),
        Index(
            "ix_routing_memory_tenant_task_profile",
            "tenant_id",
            "task_profile_id",
        ),
    )


class RoutingAdaptationProposalModel(Base):
    __tablename__ = "routing_adaptation_proposals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    task_profile_id = Column(String(160), nullable=False, index=True)
    routing_memory_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    proposed_changes = Column(JSONB, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="draft", index=True)
    sandbox_validated = Column(Boolean, nullable=False, default=False)
    validation_evidence = Column(JSONB, nullable=False, default=dict)
    block_reason = Column(Text, nullable=True)
    created_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index(
            "ix_routing_adaptation_tenant_task_status",
            "tenant_id",
            "task_profile_id",
            "status",
        ),
    )
