from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base


Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProviderAccountModel(Base):
    __tablename__ = "provider_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(64), nullable=True, index=True)
    owner_scope = Column(String(16), nullable=False, default="system")
    slug = Column(String(120), nullable=False)
    display_name = Column(String(160), nullable=False)
    provider_type = Column(String(32), nullable=False, default="cloud")
    base_url = Column(String(255), nullable=False)
    auth_mode = Column(String(32), nullable=False, default="api_key")
    is_enabled = Column(Boolean, nullable=False, default=True)
    is_local = Column(Boolean, nullable=False, default=False)
    supports_chat = Column(Boolean, nullable=False, default=True)
    supports_embeddings = Column(Boolean, nullable=False, default=False)
    supports_responses = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    health_status = Column(String(16), nullable=False, default="unknown")
    last_health_at = Column(DateTime(timezone=True), nullable=True)
    last_health_error = Column(Text, nullable=True)
    created_by = Column(String(120), nullable=False)
    updated_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "owner_scope", "slug", name="uq_provider_accounts_scope_slug"),
        Index("ix_provider_accounts_scope_enabled", "owner_scope", "is_enabled"),
    )


class ProviderCredentialModel(Base):
    __tablename__ = "provider_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("provider_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    secret_ciphertext = Column(Text, nullable=False)
    key_hint_last4 = Column(String(8), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(120), nullable=False)
    updated_by = Column(String(120), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        Index("ix_provider_credentials_provider_active", "provider_id", "is_active"),
    )


class ProviderModelModel(Base):
    __tablename__ = "provider_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("provider_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(160), nullable=False)
    display_name = Column(String(160), nullable=True)
    capabilities = Column(JSONB, nullable=False, default=dict)
    is_enabled = Column(Boolean, nullable=False, default=True)
    priority = Column(Integer, nullable=False, default=100)
    cost_class = Column(String(32), nullable=True)
    latency_class = Column(String(32), nullable=True)
    quality_class = Column(String(32), nullable=True)
    supports_tools = Column(Boolean, nullable=False, default=False)
    supports_json = Column(Boolean, nullable=False, default=False)
    supports_streaming = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        UniqueConstraint("provider_id", "model_name", name="uq_provider_models_provider_model_name"),
        Index("ix_provider_models_provider_enabled_priority", "provider_id", "is_enabled", "priority"),
    )


class ProviderHealthCheckModel(Base):
    __tablename__ = "provider_health_checks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("provider_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(16), nullable=False, default="unknown")
    latency_ms = Column(Integer, nullable=True)
    error_code = Column(String(64), nullable=True)
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime(timezone=True), nullable=False, default=utcnow)
    created_by = Column(String(120), nullable=False)

    __table_args__ = (
        Index("ix_provider_health_checks_provider_checked_at", "provider_id", "checked_at"),
    )
