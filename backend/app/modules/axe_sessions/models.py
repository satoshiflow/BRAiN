"""Database models for AXE chat sessions."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class AXEChatSessionORM(Base):
    __tablename__ = "axe_chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    principal_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(128), nullable=True, index=True)
    title = Column(String(200), nullable=False, default="New Chat")
    preview = Column(String(300), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    message_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    last_message_at = Column(DateTime, nullable=True, index=True)

    messages = relationship(
        "AXEChatMessageORM",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'deleted')", name="ck_axe_chat_sessions_status"),
    )


class AXEChatMessageORM(Base):
    __tablename__ = "axe_chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("axe_chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    attachments_json = Column("attachments", JSONB, nullable=False, default=list)
    message_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    session = relationship("AXEChatSessionORM", back_populates="messages")

    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant')", name="ck_axe_chat_messages_role"),
    )
