"""Database models for Domain Agent registry."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text
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
