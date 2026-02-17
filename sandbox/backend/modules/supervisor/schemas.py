from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class AgentControlAction(str, Enum):
    PAUSE = "pause"
    RESUME = "resume"
    KILL = "kill"
    RESTART = "restart"


class SystemComponentStatus(BaseModel):
    name: str
    healthy: bool
    details: Optional[Dict[str, str]] = None


class AgentStatus(BaseModel):
    id: str = Field(..., description="Internal agent identifier")
    name: str = Field(..., description="Human readable agent name")
    state: AgentState
    last_heartbeat: Optional[datetime] = None
    current_mission_id: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    meta: Dict[str, str] = Field(default_factory=dict)


class SupervisorStatus(BaseModel):
    uptime_seconds: float
    started_at: datetime
    global_state: str
    components: List[SystemComponentStatus]
    total_agents: int
    healthy_agents: int
    degraded_agents: int
    offline_agents: int
    active_missions: int


class AgentControlRequest(BaseModel):
    agent_id: str
    action: AgentControlAction
    reason: Optional[str] = None
    requested_by: Optional[str] = None


class AgentControlResponse(BaseModel):
    success: bool
    message: str
    agent: Optional[AgentStatus] = None
