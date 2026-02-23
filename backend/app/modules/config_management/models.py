"""Config Management - Models"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class ConfigEntryModel(Base):
    __tablename__ = "config_entries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False, index=True)
    value = Column(JSONB, nullable=True)
    type = Column(String(50), nullable=False, default="string")  # string, number, boolean, json
    environment = Column(String(50), nullable=False, default="default")  # dev, staging, prod
    is_secret = Column(Boolean, nullable=False, default=False)
    is_encrypted = Column(Boolean, nullable=False, default=False)
    description = Column(Text, nullable=True)
    version = Column(Integer, nullable=False, default=1)
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self, include_secrets=False):
        result = {
            "id": str(self.id),
            "key": self.key,
            "type": self.type,
            "environment": self.environment,
            "is_secret": self.is_secret,
            "description": self.description,
            "version": self.version,
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if not self.is_secret or include_secrets:
            result["value"] = self.value
        else:
            result["value"] = "***REDACTED***"
        return result
