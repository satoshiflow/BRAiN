"""
Base Cluster Class

Abstract base class for all agent clusters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from backend.brain.agents.base_agent import BaseAgent


class BaseCluster(ABC):
    """
    Abstract base class for agent clusters.

    A cluster groups related agents together and provides
    workflow orchestration capabilities.
    """

    def __init__(self, cluster_id: str, name: str, version: str):
        """
        Initialize cluster.

        Args:
            cluster_id: Unique cluster identifier
            name: Human-readable cluster name
            version: Semantic version (e.g., "1.0.0")
        """
        self.cluster_id = cluster_id
        self.name = name
        self.version = version
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent_id: str, agent: BaseAgent):
        """
        Register an agent in the cluster.

        Args:
            agent_id: Unique agent identifier within cluster
            agent: Agent instance
        """
        self.agents[agent_id] = agent

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """
        Get agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)

    def list_agents(self) -> Dict[str, str]:
        """
        List all agents in cluster.

        Returns:
            Dict mapping agent_id to agent class name
        """
        return {
            agent_id: agent.__class__.__name__
            for agent_id, agent in self.agents.items()
        }

    @abstractmethod
    async def execute_workflow(
        self,
        workflow_type: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a multi-agent workflow.

        Args:
            workflow_type: Type of workflow to execute
            params: Workflow parameters

        Returns:
            Workflow execution results

        Raises:
            ValueError: If workflow_type is unknown
        """
        pass

    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all agents in cluster.

        Returns:
            Dict with health status for each agent
        """
        health = {}

        for agent_id, agent in self.agents.items():
            try:
                # Basic health check - can agent respond?
                result = await agent.run("health_check")
                health[agent_id] = "healthy" if result.success else "unhealthy"
            except Exception as e:
                health[agent_id] = f"error: {str(e)}"

        overall_health = "healthy" if all(
            status == "healthy" for status in health.values()
        ) else "degraded"

        return {
            "cluster": self.cluster_id,
            "name": self.name,
            "version": self.version,
            "agents": health,
            "overall": overall_health,
            "agent_count": len(self.agents)
        }

    def get_info(self) -> Dict[str, Any]:
        """
        Get cluster information.

        Returns:
            Dict with cluster metadata
        """
        return {
            "cluster_id": self.cluster_id,
            "name": self.name,
            "version": self.version,
            "agent_count": len(self.agents),
            "agents": self.list_agents()
        }
