"""Audit Logging - Models"""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import declarative_base
from enum import Enum

Base = declarative_base()

class AuditEventType(str, Enum):
    OPERATION = "operation"
    SECURITY = "security"
    SYSTEM = "system"

class AuditAction(str, Enum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    EXECUTE = "execute"

class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AuditEventModel(Base):
    __tablename__ = "audit_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False, index=True)
    actor = Column(String(100), nullable=False, index=True)
    actor_type = Column(String(50), nullable=False, default="user")  # user, agent, system
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(100), nullable=True)
    old_values = Column(JSONB, nullable=True)
    new_values = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    severity = Column(String(20), nullable=False, default="info")
    message = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "event_type": self.event_type,
            "action": self.action,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "severity": self.severity,
            "message": self.message,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
