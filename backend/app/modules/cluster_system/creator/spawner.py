"""
Cluster Spawner

Spawns agents from blueprint definitions.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from loguru import logger
import uuid

from ..models import ClusterAgent, AgentRole
from app.modules.genesis.core import (
    get_genesis_service,
    SpawnAgentRequest,
    GenesisAgentResult,
)
from app.modules.genesis.core.exceptions import GenesisError, EthicsViolationError


class ClusterSpawner:
    """
    Spawns agents for cluster based on blueprint.

    Integrates with Genesis module for agent creation.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.genesis = get_genesis_service()

    def _resolve_genesis_blueprint_id(self, agent_def: Dict[str, Any]) -> str:
        """
        Resolve Genesis blueprint ID from cluster agent definition.

        Priority:
        1. Explicit genesis_blueprint_id field
        2. Infer from role + capabilities
        3. Default fallback
        """
        # Priority 1: Explicit mapping
        if "genesis_blueprint_id" in agent_def:
            return agent_def["genesis_blueprint_id"]

        # Priority 2: Role-based defaults
        role = agent_def.get("role", "worker")
        capabilities = agent_def.get("capabilities", [])

        if role == "supervisor":
            return "fleet_coordinator_v1"

        if role in ["specialist", "lead"]:
            cap_str = " ".join(capabilities).lower()
            if "code" in cap_str or "development" in cap_str:
                return "code_specialist_v1"
            if "ops" in cap_str or "operation" in cap_str:
                return "ops_specialist_v1"
            if "safety" in cap_str or "monitor" in cap_str:
                return "safety_monitor_v1"
            if "nav" in cap_str or "plan" in cap_str:
                return "navigation_planner_v1"

        # Priority 3: Default fallback
        logger.warning(f"No Genesis blueprint match for role={role}, using default")
        return "ops_specialist_v1"

    def _derive_trait_overrides(self, cluster_config: Dict[str, Any]) -> Dict[str, Any]:
        """Derive Genesis trait overrides from cluster configuration."""
        overrides = {}

        # Temperature → Behavioral traits
        temp = cluster_config.get("temperature", 0.7)
        if temp >= 0.8:  # High temperature = creative
            overrides["behavioral.creativity"] = 0.8
        elif temp <= 0.4:  # Low temperature = precise
            overrides["behavioral.decisiveness"] = 0.9
            overrides["performance.accuracy_target"] = 0.95

        # Explicit trait overrides (if provided in cluster config)
        if "traits" in cluster_config:
            overrides.update(cluster_config["traits"])

        return overrides

    def _map_role_enum(self, role_str: str) -> AgentRole:
        """Map role string to AgentRole enum."""
        role_map = {
            "supervisor": AgentRole.SUPERVISOR,
            "lead": AgentRole.LEAD,
            "specialist": AgentRole.SPECIALIST,
            "worker": AgentRole.WORKER
        }
        return role_map.get(role_str, AgentRole.WORKER)

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
        """Spawn supervisor agent using Genesis module."""
        logger.info(f"Spawning supervisor for cluster {cluster_id}")

        # Step 1: Resolve Genesis blueprint
        genesis_blueprint_id = self._resolve_genesis_blueprint_id(agent_def)
        logger.debug(f"Using Genesis blueprint: {genesis_blueprint_id}")

        # Step 2: Prepare trait overrides
        cluster_config = agent_def.get("config", {})
        trait_overrides = self._derive_trait_overrides(cluster_config)

        # Step 3: Generate agent ID hint
        supervisor_name = agent_def.get("name", "supervisor").lower().replace(" ", "_")
        agent_id_hint = f"{cluster_id}_{supervisor_name}"

        # Step 4: Call Genesis to spawn agent
        try:
            spawn_request = SpawnAgentRequest(
                blueprint_id=genesis_blueprint_id,
                agent_id=agent_id_hint,
                trait_overrides=trait_overrides,
                seed=None  # Allow non-deterministic
            )

            genesis_result: GenesisAgentResult = await self.genesis.spawn_agent(spawn_request)
            logger.info(f"Genesis created agent: {genesis_result.agent_id}")

        except EthicsViolationError as e:
            logger.error(f"Ethics violation during supervisor spawn: {e}")
            raise RuntimeError(f"Cannot spawn supervisor: Ethics violation - {e}")
        except GenesisError as e:
            logger.error(f"Genesis error during supervisor spawn: {e}")
            raise RuntimeError(f"Cannot spawn supervisor: {e}")

        # Step 5: Create ClusterAgent DB entry with REAL agent_id
        agent = ClusterAgent(
            id=str(uuid.uuid4()),
            cluster_id=cluster_id,
            agent_id=genesis_result.agent_id,  # REAL Genesis agent ID
            role=AgentRole.SUPERVISOR,
            supervisor_id=None,
            capabilities=agent_def.get("capabilities", []),
            skills=agent_def.get("skills", []),
            config={
                **cluster_config,
                "genesis_blueprint_id": genesis_blueprint_id,
                "genesis_dna_snapshot_id": genesis_result.dna_snapshot_id,
            },
            status="active"
        )

        self.db.add(agent)
        await self.db.flush()

        return agent

    async def spawn_worker(
        self,
        cluster_id: str,
        agent_def: Dict[str, Any],
        supervisor_id: str
    ) -> ClusterAgent:
        """Spawn worker/specialist agent using Genesis module."""
        role_str = agent_def.get("role", "worker")
        logger.debug(f"Spawning {role_str} for cluster {cluster_id}")

        # Step 1: Resolve Genesis blueprint
        genesis_blueprint_id = self._resolve_genesis_blueprint_id(agent_def)

        # Step 2: Prepare trait overrides
        cluster_config = agent_def.get("config", {})
        trait_overrides = self._derive_trait_overrides(cluster_config)

        # Step 3: Generate agent ID hint
        agent_name = agent_def.get("name", role_str).lower().replace(" ", "_")
        agent_id_hint = f"{cluster_id}_{agent_name}_{uuid.uuid4().hex[:4]}"

        # Step 4: Call Genesis (graceful failure for workers)
        try:
            spawn_request = SpawnAgentRequest(
                blueprint_id=genesis_blueprint_id,
                agent_id=agent_id_hint,
                trait_overrides=trait_overrides,
                seed=None
            )

            genesis_result: GenesisAgentResult = await self.genesis.spawn_agent(spawn_request)
            logger.info(f"Genesis created agent: {genesis_result.agent_id}")

        except (EthicsViolationError, GenesisError) as e:
            logger.error(f"Genesis spawn failed for {role_str}: {e}")
            # Non-fatal for workers: create failed entry and continue
            failed_agent = ClusterAgent(
                id=str(uuid.uuid4()),
                cluster_id=cluster_id,
                agent_id=f"failed-{uuid.uuid4().hex[:8]}",
                role=self._map_role_enum(role_str),
                supervisor_id=supervisor_id,
                capabilities=agent_def.get("capabilities", []),
                skills=agent_def.get("skills", []),
                config={"error": str(e)},
                status="spawn_failed",
                last_error=str(e)
            )
            self.db.add(failed_agent)
            await self.db.flush()
            return failed_agent

        # Step 5: Create ClusterAgent DB entry with REAL agent_id
        role = self._map_role_enum(role_str)

        agent = ClusterAgent(
            id=str(uuid.uuid4()),
            cluster_id=cluster_id,
            agent_id=genesis_result.agent_id,  # REAL Genesis agent ID
            role=role,
            supervisor_id=supervisor_id,
            capabilities=agent_def.get("capabilities", []),
            skills=agent_def.get("skills", []),
            config={
                **cluster_config,
                "genesis_blueprint_id": genesis_blueprint_id,
                "genesis_dna_snapshot_id": genesis_result.dna_snapshot_id,
            },
            status="active"
        )

        self.db.add(agent)
        await self.db.flush()

        return agent
