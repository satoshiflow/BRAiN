from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProviderBindingModel(Base):
    __tablename__ = "provider_bindings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    owner_scope = Column(String(16), nullable=False, default="system")
    capability_id = Column(UUID(as_uuid=True), nullable=True)
    capability_key = Column(String(120), nullable=False, index=True)
    capability_version = Column(Integer, nullable=False)
    provider_key = Column(String(120), nullable=False)
    provider_type = Column(String(32), nullable=False, default="service")
    adapter_key = Column(String(120), nullable=False)
    endpoint_ref = Column(String(255), nullable=False)
    model_or_tool_ref = Column(String(255), nullable=True)
    region = Column(String(64), nullable=True)
    priority = Column(Integer, nullable=False, default=100)
    weight = Column(Float, nullable=True)
    cost_profile = Column(JSONB, nullable=False, default=dict)
    sla_profile = Column(JSONB, nullable=False, default=dict)
    policy_constraints = Column(JSONB, nullable=False, default=dict)
    status = Column(String(32), nullable=False, default="draft", index=True)
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    config = Column(JSONB, nullable=False, default=dict)
    definition_artifact_refs = Column(JSONB, nullable=False, default=list)
    evidence_artifact_refs = Column(JSONB, nullable=False, default=list)
    created_by = Column(String(120), nullable=False)
    updated_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_provider_bindings_capability_status_priority", "capability_key", "capability_version", "status", "priority"),
    )
