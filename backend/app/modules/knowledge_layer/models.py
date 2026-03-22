from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KnowledgeItemModel(Base):
    __tablename__ = "knowledge_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    type = Column(String(40), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    source = Column(String(120), nullable=False)
    version = Column(Integer, nullable=False, default=1)
    owner = Column(String(120), nullable=False)
    module = Column(String(120), nullable=False, index=True)
    tags = Column(JSONB, nullable=False, default=list)
    content = Column(Text, nullable=False)
    provenance_refs = Column(JSONB, nullable=False, default=list)
    skill_run_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    experience_record_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    evaluation_result_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    valid_until = Column(DateTime(timezone=True), nullable=True)
    superseded_by_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (
        Index("ix_knowledge_items_tenant_type", "tenant_id", "type"),
        Index("ix_knowledge_items_tenant_module", "tenant_id", "module"),
        Index("ix_knowledge_items_run_chain", "tenant_id", "skill_run_id", "experience_record_id", "evaluation_result_id"),
    )
