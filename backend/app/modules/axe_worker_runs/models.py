"""Persistence models for AXE worker run polling surface."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class AXEWorkerRunORM(Base):
    __tablename__ = "axe_worker_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_run_id = Column(String(64), nullable=False, unique=True, index=True)

    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("axe_chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    message_id = Column(UUID(as_uuid=True), nullable=False, index=True)

    principal_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(128), nullable=True, index=True)

    backend_run_id = Column(String(128), nullable=True, index=True)
    backend_run_type = Column(String(32), nullable=False, default="opencode_job")

    status = Column(String(32), nullable=False, default="queued", index=True)
    label = Column(String(160), nullable=False, default="OpenCode worker queued")
    detail = Column(Text, nullable=False, default="Job accepted by BRAiN orchestrator")
    artifacts_json = Column("artifacts", JSONB, nullable=False, default=list)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_axe_worker_runs_session_updated", "session_id", "updated_at"),
    )
