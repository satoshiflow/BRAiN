"""
Agent Management System

Core module for agent registration, lifecycle management, and discovery.

Features:
- Agent registration with capabilities
- Heartbeat monitoring
- Automatic offline detection
- EventStream integration
"""

from .models import AgentModel, AgentStatus
from .schemas import (
    AgentRegister, AgentUpdate, AgentHeartbeat,
    AgentResponse, AgentListResponse, AgentStats
)
from .service import AgentService, get_agent_service
from .router import router

__all__ = [
    "AgentModel",
    "AgentStatus", 
    "AgentRegister",
    "AgentUpdate",
    "AgentHeartbeat",
    "AgentResponse",
    "AgentListResponse",
    "AgentStats",
    "AgentService",
    "get_agent_service",
    "router",
]
