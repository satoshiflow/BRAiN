"""
Agent Management System - Database Models

Core module for agent registration, lifecycle management, and discovery.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum, Integer, Float, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class AgentStatus(str, Enum):
    """Agent lifecycle states"""
    REGISTERED = "registered"      # Just created, not yet active
    ACTIVE = "active"              # Running and healthy
    DEGRADED = "degraded"          # Running but with issues
    OFFLINE = "offline"            # Missed heartbeats
    MAINTENANCE = "maintenance"    # Manual maintenance mode
    TERMINATED = "terminated"      # Gracefully shut down


class AgentModel(Base):
    """
    Agent database model.
    
    Represents a registered agent in the system with its
    capabilities, status, and metadata.
    """
    __tablename__ = "agents"
    
    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(SQLEnum(AgentStatus), nullable=False, default=AgentStatus.REGISTERED)
    
    # Capabilities & Configuration
    agent_type = Column(String(50), nullable=False, default="worker")
    version = Column(String(50), nullable=True)
    capabilities = Column(JSONB, nullable=False, default=list)
    config = Column(JSONB, nullable=False, default=dict)
    
    # Runtime Info
    last_heartbeat = Column(DateTime, nullable=True)
    heartbeat_interval = Column(Integer, nullable=False, default=60)
    missed_heartbeats = Column(Integer, nullable=False, default=0)
    
    # Performance Metrics
    tasks_completed = Column(Integer, nullable=False, default=0)
    tasks_failed = Column(Integer, nullable=False, default=0)
    avg_task_duration_ms = Column(Float, nullable=True)
    
    # Connection Info
    host = Column(String(255), nullable=True)
    pid = Column(Integer, nullable=True)
    
    # Timestamps
    registered_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    activated_at = Column(DateTime, nullable=True)
    last_active_at = Column(DateTime, nullable=True)
    terminated_at = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, agent_id={self.agent_id}, status={self.status})>"
    
    def to_dict(self) -> dict:
        """Convert model to dictionary"""
        return {
            "id": str(self.id),
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "agent_type": self.agent_type,
            "version": self.version,
            "capabilities": self.capabilities,
            "config": self.config,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "heartbeat_interval": self.heartbeat_interval,
            "missed_heartbeats": self.missed_heartbeats,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "avg_task_duration_ms": self.avg_task_duration_ms,
            "host": self.host,
            "pid": self.pid,
            "registered_at": self.registered_at.isoformat() if self.registered_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
            "last_active_at": self.last_active_at.isoformat() if self.last_active_at else None,
            "terminated_at": self.terminated_at.isoformat() if self.terminated_at else None,
        }
