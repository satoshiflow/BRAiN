from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SkillDefinitionModel(Base):
    __tablename__ = "skill_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    owner_scope = Column(String(16), nullable=False, default="tenant")
    skill_key = Column(String(120), nullable=False, index=True)
    version = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="draft", index=True)
    purpose = Column(Text, nullable=False)
    input_schema = Column(JSONB, nullable=False, default=dict)
    output_schema = Column(JSONB, nullable=False, default=dict)
    required_capabilities = Column(JSONB, nullable=False, default=list)
    optional_capabilities = Column(JSONB, nullable=False, default=list)
    constraints = Column(JSONB, nullable=False, default=dict)
    quality_profile = Column(String(32), nullable=False, default="standard")
    fallback_policy = Column(String(32), nullable=False, default="allowed")
    evaluation_criteria = Column(JSONB, nullable=False, default=dict)
    risk_tier = Column(String(32), nullable=False, default="medium")
    policy_pack_ref = Column(String(120), nullable=False, default="default")
    trust_tier_min = Column(String(32), nullable=False, default="internal")
    value_score = Column(Float, nullable=False, default=0.0)
    effort_saved_hours = Column(Float, nullable=False, default=0.0)
    complexity_level = Column(String(32), nullable=False, default="medium")
    quality_impact = Column(Float, nullable=False, default=0.0)
    premium_tier = Column(String(32), nullable=False, default="free")
    internal_credit_price = Column(Float, nullable=False, default=0.0)
    marketplace_listing_state = Column(String(32), nullable=False, default="internal_only")
    builder_role = Column(String(64), nullable=False, default="manual")
    definition_artifact_refs = Column(JSONB, nullable=False, default=list)
    example_artifact_refs = Column(JSONB, nullable=False, default=list)
    builder_artifact_refs = Column(JSONB, nullable=False, default=list)
    checksum_sha256 = Column(String(64), nullable=False)
    created_by = Column(String(120), nullable=False)
    updated_by = Column(String(120), nullable=False)
    approved_by = Column(String(120), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_skill_definitions_key_version_scope", "skill_key", "version", "owner_scope"),
    )

    @staticmethod
    def build_checksum(payload: dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
