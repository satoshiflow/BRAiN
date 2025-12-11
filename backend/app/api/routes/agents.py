from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["Agents"])


class AgentSummary(BaseModel):
    id: str
    kind: Literal["system", "user"]
    label: str
    description: Optional[str] = None


AGENTS: List[AgentSummary] = [
    AgentSummary(
        id="agent_test_1",
        kind="user",
        label="Test Agent 1",
        description="Manuell angelegter Test-Agent",
    ),
    AgentSummary(
        id="supervisor",
        kind="system",
        label="Supervisor Agent",
        description="Überwacht Missions und Agents",
    ),
    AgentSummary(
        id="policy_engine",
        kind="system",
        label="Policy Engine",
        description="Evaluates outputs against policies",
    ),
    AgentSummary(
        id="immune_core",
        kind="system",
        label="Immune Core",
        description="Threat detection and self-healing",
    ),
]


@router.get("/api/agents", response_model=List[AgentSummary])
def list_agents(kind: Optional[str] = None) -> List[AgentSummary]:
    if kind in ("system", "user"):
        return [a for a in AGENTS if a.kind == kind]
    return AGENTS


@router.get("/api/agents/{agent_id}", response_model=AgentSummary)
def get_agent(agent_id: str) -> AgentSummary:
    for agent in AGENTS:
        if agent.id == agent_id:
            return agent
    raise HTTPException(status_code=404, detail="Agent not found")
