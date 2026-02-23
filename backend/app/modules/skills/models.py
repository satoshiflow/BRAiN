"""
Skills Module - Database Models

SQLAlchemy models for the PicoClaw-style Skill System.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class SkillCategory(str, Enum):
    """Categories for organizing skills"""
    API = "api"
    FILE = "file"
    COMMUNICATION = "communication"
    ANALYSIS = "analysis"
    CUSTOM = "custom"


class SkillModel(Base):
    """
    Skill database model.
    
    Stores skill definitions with their manifests and handler paths.
    """
    __tablename__ = "skills"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(SQLEnum(SkillCategory), nullable=False, default=SkillCategory.CUSTOM)
    manifest = Column(JSONB, nullable=False, default=dict)
    handler_path = Column(String(255), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    is_builtin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self) -> str:
        return f"<Skill(id={self.id}, name={self.name}, category={self.category}, enabled={self.enabled})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "category": self.category.value if isinstance(self.category, SkillCategory) else self.category,
            "manifest": self.manifest,
            "handler_path": self.handler_path,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
