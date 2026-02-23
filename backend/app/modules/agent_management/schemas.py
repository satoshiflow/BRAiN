"""
Agent Management System - Pydantic Schemas

Validation schemas for agent management.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    """Agent lifecycle states"""
    REGISTERED = "registered"
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"
    TERMINATED = "terminated"


class AgentCapability(BaseModel):
    """Agent capability definition"""
    name: str = Field(..., description="Capability name")
    description: Optional[str] = Field(default=None, description="Capability description")
    version: Optional[str] = Field(default=None, description="Capability version")


# ============================================================================
# CRUD Schemas
# ============================================================================

class AgentRegister(BaseModel):
    """Schema for registering a new agent"""
    agent_id: str = Field(..., min_length=1, max_length=100, description="Unique agent identifier")
    name: str = Field(..., min_length=1, max_length=255, description="Agent display name")
    description: Optional[str] = Field(default=None, description="Agent description")
    agent_type: str = Field(default="worker", description="Agent type (worker, supervisor, specialist)")
    version: Optional[str] = Field(default=None, description="Agent software version")
    capabilities: List[str] = Field(default_factory=list, description="List of capability names")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")
    heartbeat_interval: int = Field(default=60, ge=10, le=3600, description="Heartbeat interval in seconds")


class AgentUpdate(BaseModel):
    """Schema for updating an existing agent"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None)
    status: Optional[AgentStatus] = Field(default=None)
    capabilities: Optional[List[str]] = Field(default=None)
    config: Optional[Dict[str, Any]] = Field(default=None)
    heartbeat_interval: Optional[int] = Field(default=None, ge=10, le=3600)


class AgentHeartbeat(BaseModel):
    """Schema for agent heartbeat"""
    agent_id: str = Field(..., description="Agent identifier")
    status: AgentStatus = Field(default=AgentStatus.ACTIVE, description="Current agent status")
    tasks_completed: Optional[int] = Field(default=None, ge=0)
    tasks_failed: Optional[int] = Field(default=None, ge=0)
    avg_task_duration_ms: Optional[float] = Field(default=None, ge=0)
    metrics: Optional[Dict[str, Any]] = Field(default=None, description="Additional metrics")


class AgentResponse(BaseModel):
    """Schema for agent response"""
    id: UUID = Field(..., description="Agent UUID")
    agent_id: str = Field(..., description="Agent identifier")
    name: str = Field(...)
    description: Optional[str] = Field(default=None)
    status: AgentStatus = Field(...)
    agent_type: str = Field(...)
    version: Optional[str] = Field(default=None)
    capabilities: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    last_heartbeat: Optional[datetime] = Field(default=None)
    heartbeat_interval: int = Field(...)
    missed_heartbeats: int = Field(...)
    tasks_completed: int = Field(...)
    tasks_failed: int = Field(...)
    avg_task_duration_ms: Optional[float] = Field(default=None)
    host: Optional[str] = Field(default=None)
    pid: Optional[int] = Field(default=None)
    registered_at: datetime = Field(...)
    activated_at: Optional[datetime] = Field(default=None)
    last_active_at: Optional[datetime] = Field(default=None)
    
    class Config:
        from_attributes = True


class AgentListResponse(BaseModel):
    """Schema for listing agents"""
    items: List[AgentResponse] = Field(default_factory=list)
    total: int = Field(..., description="Total number of agents")
    by_status: Dict[str, int] = Field(default_factory=dict, description="Count by status")


class AgentStats(BaseModel):
    """Schema for agent statistics"""
    total_agents: int = Field(...)
    active_count: int = Field(...)
    offline_count: int = Field(...)
    degraded_count: int = Field(...)
    total_tasks_completed: int = Field(...)
    total_tasks_failed: int = Field(...)
    avg_uptime_percent: Optional[float] = Field(default=None)


# ============================================================================
# Event Schemas
# ============================================================================

class AgentEvent(BaseModel):
    """Base schema for agent events"""
    event_type: str = Field(..., description="Event type")
    agent_id: str = Field(..., description="Agent identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)


class AgentRegisteredEvent(AgentEvent):
    """Event: Agent registered"""
    event_type: str = "agent.registered"
    data: Dict[str, Any] = Field(default_factory=dict)


class AgentActivatedEvent(AgentEvent):
    """Event: Agent became active"""
    event_type: str = "agent.activated"


class AgentHeartbeatEvent(AgentEvent):
    """Event: Agent heartbeat received"""
    event_type: str = "agent.heartbeat"
    data: Dict[str, Any] = Field(default_factory=dict)


class AgentDegradedEvent(AgentEvent):
    """Event: Agent status degraded"""
    event_type: str = "agent.degraded"
    reason: Optional[str] = Field(default=None)


class AgentOfflineEvent(AgentEvent):
    """Event: Agent went offline"""
    event_type: str = "agent.offline"
    missed_heartbeats: int = Field(...)
    last_heartbeat: Optional[datetime] = Field(default=None)


class AgentRecoveredEvent(AgentEvent):
    """Event: Agent recovered from offline/degraded"""
    event_type: str = "agent.recovered"
    previous_status: str = Field(...)


class AgentTerminatedEvent(AgentEvent):
    """Event: Agent terminated"""
    event_type: str = "agent.terminated"
    reason: Optional[str] = Field(default=None)
