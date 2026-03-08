from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ModuleLifecycleModel(Base):
    __tablename__ = "module_lifecycle"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(String(120), nullable=False, unique=True, index=True)
    owner_scope = Column(String(16), nullable=False, default="system")
    classification = Column(String(20), nullable=False)
    lifecycle_status = Column(String(20), nullable=False, index=True)
    canonical_path = Column(String(255), nullable=False)
    active_routes = Column(JSONB, nullable=False, default=list)
    data_owner = Column(String(120), nullable=False)
    auth_surface = Column(Text, nullable=False)
    event_contract_status = Column(String(32), nullable=False)
    audit_policy = Column(String(120), nullable=False)
    migration_adapter = Column(String(255), nullable=True)
    kill_switch = Column(String(120), nullable=True)
    replacement_target = Column(String(120), nullable=True)
    sunset_phase = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (Index("ix_module_lifecycle_status_classification", "lifecycle_status", "classification"),)
