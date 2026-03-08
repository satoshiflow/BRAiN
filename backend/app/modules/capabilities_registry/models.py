from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CapabilityDefinitionModel(Base):
    __tablename__ = "capability_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    owner_scope = Column(String(16), nullable=False, default="tenant")
    capability_key = Column(String(120), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="draft", index=True)
    domain = Column(String(80), nullable=False)
    description = Column(Text, nullable=False)
    input_schema = Column(JSONB, nullable=False, default=dict)
    output_schema = Column(JSONB, nullable=False, default=dict)
    default_timeout_ms = Column(Integer, nullable=False, default=30000)
    retry_policy = Column(JSONB, nullable=False, default=dict)
    qos_targets = Column(JSONB, nullable=False, default=dict)
    fallback_capability_key = Column(String(120), nullable=True)
    policy_constraints = Column(JSONB, nullable=False, default=dict)
    checksum_sha256 = Column(String(64), nullable=False)
    created_by = Column(String(120), nullable=False)
    updated_by = Column(String(120), nullable=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_capability_definitions_key_version_scope", "capability_key", "version", "owner_scope"),
    )

    @staticmethod
    def build_checksum(payload: dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
