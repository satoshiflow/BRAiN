"""
Cluster Spawner

Spawns agents from blueprint definitions.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from loguru import logger
import uuid

from ..models import ClusterAgent, AgentRole


class ClusterSpawner:
    """
    Spawns agents for cluster based on blueprint.

    Integrates with Genesis module for agent creation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def spawn_from_blueprint(
        self,
        cluster_id: str,
        blueprint: Dict[str, Any]
    ) -> List[ClusterAgent]:
        """
        Spawn all agents defined in blueprint.

        Args:
            cluster_id: Target cluster ID
            blueprint: Parsed blueprint dict

        Returns:
            List[ClusterAgent]: Spawned agents

        Raises:
            RuntimeError: If spawning fails
        """
        logger.info(f"Spawning agents for cluster {cluster_id}")

        agents_def = blueprint.get("agents", [])
        spawned_agents = []

        # First, spawn supervisor
        supervisor_def = next((a for a in agents_def if a.get("role") == "supervisor"), None)
        if not supervisor_def:
            raise RuntimeError("No supervisor defined in blueprint")

        supervisor = await self.spawn_supervisor(cluster_id, supervisor_def)
        spawned_agents.append(supervisor)

        logger.info(f"Spawned supervisor: {supervisor.agent_id}")

        # Then spawn specialists and initial workers
        for agent_def in agents_def:
            role = agent_def.get("role")

            if role == "supervisor":
                continue  # Already spawned

            # Determine count
            count = agent_def.get("count", 1)
            if isinstance(count, str) and "-" in count:
                # Range like "0-5", use min value for initial spawn
                min_count = int(count.split("-")[0])
                count = min_count
            elif not isinstance(count, int):
                count = 1

            # Determine supervisor
            reports_to = agent_def.get("reports_to")
            if reports_to:
                # Find agent with this name
                parent = next((a for a in spawned_agents if a.capabilities and reports_to in str(a.capabilities)), supervisor)
                supervisor_id = parent.agent_id
            else:
                supervisor_id = supervisor.agent_id

            # Spawn agents
            for i in range(count):
                agent = await self.spawn_worker(
                    cluster_id,
                    agent_def,
                    supervisor_id
                )
                spawned_agents.append(agent)
                logger.debug(f"Spawned {role}: {agent.agent_id}")

        logger.info(f"Spawned {len(spawned_agents)} agents for cluster {cluster_id}")
        return spawned_agents

    async def spawn_supervisor(
        self,
        cluster_id: str,
        agent_def: Dict[str, Any]
    ) -> ClusterAgent:
        """Spawn supervisor agent"""
        logger.info(f"Spawning supervisor for cluster {cluster_id}")

        # TODO: Integrate with Genesis module to actually create agent
        # For now, create ClusterAgent entry only

        agent_id = f"agent-{str(uuid.uuid4())[:8]}"

        agent = ClusterAgent(
            id=str(uuid.uuid4()),
            cluster_id=cluster_id,
            agent_id=agent_id,
            role=AgentRole.SUPERVISOR,
            supervisor_id=None,  # Supervisor has no supervisor
            capabilities=agent_def.get("capabilities", []),
            skills=agent_def.get("skills", []),
            config=agent_def.get("config", {}),
            status="active"
        )

        self.db.add(agent)
        await self.db.flush()

        logger.debug(f"Created supervisor agent: {agent_id}")
        return agent

    async def spawn_worker(
        self,
        cluster_id: str,
        agent_def: Dict[str, Any],
        supervisor_id: str
    ) -> ClusterAgent:
        """Spawn worker agent"""
        logger.debug(f"Spawning worker for cluster {cluster_id}")

        # TODO: Integrate with Genesis module to actually create agent
        # For now, create ClusterAgent entry only

        agent_id = f"agent-{str(uuid.uuid4())[:8]}"

        # Map role string to AgentRole enum
        role_str = agent_def.get("role", "worker")
        role_map = {
            "supervisor": AgentRole.SUPERVISOR,
            "lead": AgentRole.LEAD,
            "specialist": AgentRole.SPECIALIST,
            "worker": AgentRole.WORKER
        }
        role = role_map.get(role_str, AgentRole.WORKER)

        agent = ClusterAgent(
            id=str(uuid.uuid4()),
            cluster_id=cluster_id,
            agent_id=agent_id,
            role=role,
            supervisor_id=supervisor_id,
            capabilities=agent_def.get("capabilities", []),
            skills=agent_def.get("skills", []),
            config=agent_def.get("config", {}),
            status="active"
        )

        self.db.add(agent)
        await self.db.flush()

        return agent
