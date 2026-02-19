"""
AXE Identity Database Models

Manages AXE personality identities with system prompts, capabilities,
and version tracking.
"""

from sqlalchemy import Column, String, Text, Boolean, Integer, TIMESTAMP, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from app.core.database import Base
import uuid
from datetime import datetime


class AXEIdentityORM(Base):
    """
    AXE Identity Model

    Stores different AXE personas with system prompts and capabilities.
    Only one identity can be active at a time.
    """
    __tablename__ = "axe_identities"

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Basic Info
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)

    # System Prompt (Core Identity)
    system_prompt = Column(Text, nullable=False)

    # Flexible Attributes
    personality = Column(JSONB, default={})
    capabilities = Column(ARRAY(String), default=[])

    # Status
    is_active = Column(Boolean, default=False, index=True)

    # Version Control
    version = Column(Integer, default=1)

    # Timestamps
    created_at = Column(TIMESTAMP, default=datetime.utcnow, index=True)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Audit
    created_by = Column(String(255))

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "(is_active = FALSE) OR "
            "((SELECT COUNT(*) FROM axe_identities WHERE is_active = TRUE) <= 1)",
            name="one_active_identity"
        ),
    )

    def __repr__(self):
        return f"<AXEIdentity(id={self.id}, name={self.name}, active={self.is_active})>"
