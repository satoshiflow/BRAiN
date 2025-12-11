from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AgentStatus(BaseModel):
    id: str
    name: str
    role: Optional[str] = None
    state: str
    last_heartbeat: Optional[datetime] = None
    missions_running: int = 0


class SupervisorHealth(BaseModel):
    status: str
    timestamp: datetime


class SupervisorStatus(BaseModel):
    status: str
    timestamp: datetime
    total_missions: int
    running_missions: int
    pending_missions: int
    completed_missions: int
    failed_missions: int
    cancelled_missions: int
    agents: List[AgentStatus] = []