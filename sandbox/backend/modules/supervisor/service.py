from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Dict, List, Optional

from .schemas import (
    AgentStatus,
    AgentState,
    SupervisorStatus,
    SystemComponentStatus,
    AgentControlRequest,
    AgentControlResponse,
)


@dataclass
class _SupervisorConfig:
    allow_kill: bool = True
    allow_pause: bool = True
    allow_restart: bool = True


class AgentRegistry:
    """In-memory registry for agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentStatus] = {}
        self._lock = RLock()

    def upsert_agent(self, agent: AgentStatus) -> AgentStatus:
        with self._lock:
            self._agents[agent.id] = agent
            return agent

    def get_agent(self, agent_id: str) -> Optional[AgentStatus]:
        with self._lock:
            return self._agents.get(agent_id)

    def all_agents(self) -> List[AgentStatus]:
        with self._lock:
            return list(self._agents.values())

    def remove_agent(self, agent_id: str) -> None:
        with self._lock:
            self._agents.pop(agent_id, None)


class SupervisorService:
    def __init__(self, started_at: Optional[datetime] = None) -> None:
        self._started_at = started_at or datetime.now(timezone.utc)
        self._config = _SupervisorConfig()
        self._registry = AgentRegistry()

    @property
    def registry(self) -> AgentRegistry:
        return self._registry

    def _compute_uptime(self) -> float:
        now = datetime.now(timezone.utc)
        return (now - self._started_at).total_seconds()

    def get_status(self) -> SupervisorStatus:
        agents = self._registry.all_agents()

        total_agents = len(agents)
        healthy_agents = sum(1 for a in agents if a.state == AgentState.HEALTHY)
        degraded_agents = sum(1 for a in agents if a.state == AgentState.DEGRADED)
        offline_agents = sum(1 for a in agents if a.state == AgentState.OFFLINE)

        active_missions = len([a for a in agents if a.current_mission_id])

        components = [
            SystemComponentStatus(name="postgres", healthy=True),
            SystemComponentStatus(name="redis", healthy=True),
            SystemComponentStatus(name="qdrant", healthy=True),
        ]

        global_state = "healthy"
        if degraded_agents > 0 or offline_agents > 0:
            global_state = "degraded"
        if total_agents > 0 and offline_agents == total_agents:
            global_state = "offline"

        return SupervisorStatus(
            uptime_seconds=self._compute_uptime(),
            started_at=self._started_at,
            global_state=global_state,
            components=components,
            total_agents=total_agents,
            healthy_agents=healthy_agents,
            degraded_agents=degraded_agents,
            offline_agents=offline_agents,
            active_missions=active_missions,
        )

    def list_agents(self) -> List[AgentStatus]:
        return self._registry.all_agents()

    def control_agent(self, request: AgentControlRequest) -> AgentControlResponse:
        agent = self._registry.get_agent(request.agent_id)
        if not agent:
            return AgentControlResponse(success=False, message="Agent not found", agent=None)

        if request.action == request.action.PAUSE:
            if agent.state == AgentState.HEALTHY:
                agent.state = AgentState.DEGRADED
                self._registry.upsert_agent(agent)
                return AgentControlResponse(success=True, message="Agent paused (state=degraded)", agent=agent)
            return AgentControlResponse(success=False, message=f"Cannot pause agent in state {agent.state}", agent=agent)

        if request.action == request.action.RESUME:
            if agent.state in (AgentState.DEGRADED, AgentState.UNKNOWN):
                agent.state = AgentState.HEALTHY
                self._registry.upsert_agent(agent)
                return AgentControlResponse(success=True, message="Agent resumed (state=healthy)", agent=agent)
            return AgentControlResponse(success=False, message=f"Cannot resume agent in state {agent.state}", agent=agent)

        if request.action == request.action.KILL:
            if not self._config.allow_kill:
                return AgentControlResponse(success=False, message="Kill operation disabled by configuration", agent=agent)
            agent.state = AgentState.OFFLINE
            self._registry.upsert_agent(agent)
            return AgentControlResponse(success=True, message="Agent marked as offline", agent=agent)

        if request.action == request.action.RESTART:
            if not self._config.allow_restart:
                return AgentControlResponse(success=False, message="Restart operation disabled by configuration", agent=agent)
            agent.state = AgentState.HEALTHY
            self._registry.upsert_agent(agent)
            return AgentControlResponse(success=True, message="Agent restarted (state=healthy)", agent=agent)

        return AgentControlResponse(success=False, message="Unsupported action", agent=agent)


_supervisor_service = SupervisorService()


def get_supervisor_service() -> SupervisorService:
    return _supervisor_service
