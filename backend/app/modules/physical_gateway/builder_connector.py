"""
Builder Toolkit Connector

Integration with MLP (Machine Learning Pipeline) and Builder Toolkit
for federation layer communication and advanced agent coordination.

Features:
- MLP API integration
- Federation layer interface
- Agent synchronization
- Capability discovery
- Task delegation
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from loguru import logger

import httpx

from .schemas import (
    BuilderToolkitConfig,
    MLPAgentSync,
    PhysicalAgentInfo,
    AgentCapability,
)


# ============================================================================
# Builder Toolkit Connector
# ============================================================================


class BuilderToolkitConnector:
    """
    Connector for MLP/Builder Toolkit integration.

    Provides:
    - Federation layer communication
    - Agent capability synchronization
    - Task delegation to MLP
    - Collaborative multi-agent coordination
    """

    def __init__(self, config: BuilderToolkitConfig):
        """
        Initialize Builder Toolkit connector.

        Args:
            config: Builder Toolkit configuration
        """
        self.config = config
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            headers={"Authorization": f"Bearer {config.api_key}"} if config.api_key else {},
        )

        # Sync tracking
        self.agent_sync_status: Dict[str, MLPAgentSync] = {}  # agent_id -> sync status

        # Background sync task
        self.sync_task: Optional[asyncio.Task] = None
        self.running = False

        logger.info(
            f"Builder Toolkit Connector initialized "
            f"(endpoint: {config.mlp_endpoint}, federation: {config.federation_mode})"
        )

    # ========================================================================
    # Lifecycle
    # ========================================================================

    async def start(self):
        """Start background synchronization."""
        if self.config.enabled and not self.running:
            self.running = True
            self.sync_task = asyncio.create_task(self._sync_loop())
            logger.info("Builder Toolkit Connector started")

    async def stop(self):
        """Stop background synchronization."""
        self.running = False
        if self.sync_task:
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        await self.http_client.aclose()
        logger.info("Builder Toolkit Connector stopped")

    # ========================================================================
    # Agent Synchronization
    # ========================================================================

    async def sync_agent(self, agent: PhysicalAgentInfo) -> bool:
        """
        Synchronize agent with MLP.

        Args:
            agent: Agent to synchronize

        Returns:
            True if sync successful
        """
        if not self.config.enabled:
            return False

        try:
            # Register agent with MLP
            payload = {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "type": agent.agent_type,
                "capabilities": [cap.value for cap in agent.capabilities],
                "protocol": agent.protocol.value,
                "endpoint": agent.endpoint,
                "state": agent.state.value,
                "battery_percentage": agent.battery_percentage,
                "position": (
                    agent.position.model_dump() if agent.position else None
                ),
                "metadata": {
                    "firmware_version": agent.firmware_version,
                    "hardware_version": agent.hardware_version,
                    "manufacturer": agent.manufacturer,
                    "model": agent.model,
                },
            }

            response = await self.http_client.post(
                f"{self.config.mlp_endpoint}/agents/register",
                json=payload,
            )

            response.raise_for_status()
            mlp_data = response.json()

            # Update sync status
            self.agent_sync_status[agent.agent_id] = MLPAgentSync(
                agent_id=agent.agent_id,
                mlp_agent_id=mlp_data.get("mlp_agent_id", agent.agent_id),
                last_sync=datetime.utcnow(),
                sync_status="success",
                sync_errors=[],
            )

            logger.info(f"✅ Agent synced with MLP: {agent.agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to sync agent with MLP: {e}")

            # Update sync status with error
            self.agent_sync_status[agent.agent_id] = MLPAgentSync(
                agent_id=agent.agent_id,
                mlp_agent_id=agent.agent_id,
                last_sync=datetime.utcnow(),
                sync_status="failed",
                sync_errors=[str(e)],
            )

            return False

    async def unsync_agent(self, agent_id: str) -> bool:
        """
        Remove agent from MLP.

        Args:
            agent_id: Agent to remove

        Returns:
            True if removal successful
        """
        if not self.config.enabled:
            return False

        try:
            response = await self.http_client.delete(
                f"{self.config.mlp_endpoint}/agents/{agent_id}"
            )

            response.raise_for_status()

            # Remove sync status
            if agent_id in self.agent_sync_status:
                del self.agent_sync_status[agent_id]

            logger.info(f"✅ Agent removed from MLP: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to remove agent from MLP: {e}")
            return False

    # ========================================================================
    # Capability Discovery
    # ========================================================================

    async def discover_capabilities(
        self,
        required_capabilities: List[AgentCapability],
    ) -> List[Dict[str, Any]]:
        """
        Discover agents with required capabilities via MLP.

        Args:
            required_capabilities: List of required capabilities

        Returns:
            List of matching agents from MLP
        """
        if not self.config.enabled:
            return []

        try:
            payload = {
                "capabilities": [cap.value for cap in required_capabilities],
            }

            response = await self.http_client.post(
                f"{self.config.mlp_endpoint}/agents/discover",
                json=payload,
            )

            response.raise_for_status()
            agents = response.json().get("agents", [])

            logger.info(
                f"Discovered {len(agents)} agents with capabilities: "
                f"{required_capabilities}"
            )

            return agents

        except Exception as e:
            logger.error(f"Capability discovery failed: {e}")
            return []

    # ========================================================================
    # Task Delegation
    # ========================================================================

    async def delegate_task(
        self,
        task_type: str,
        task_description: str,
        required_capabilities: List[AgentCapability],
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Delegate task to MLP for execution.

        Args:
            task_type: Type of task
            task_description: Task description
            required_capabilities: Required agent capabilities
            parameters: Task parameters

        Returns:
            Task delegation response or None if failed
        """
        if not self.config.enabled:
            return None

        try:
            payload = {
                "task_type": task_type,
                "description": task_description,
                "required_capabilities": [cap.value for cap in required_capabilities],
                "parameters": parameters or {},
                "source": "brain_physical_gateway",
            }

            response = await self.http_client.post(
                f"{self.config.mlp_endpoint}/tasks/delegate",
                json=payload,
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Task delegated to MLP: {result.get('task_id')}")
            return result

        except Exception as e:
            logger.error(f"Task delegation failed: {e}")
            return None

    # ========================================================================
    # Federation Layer
    # ========================================================================

    async def federate_command(
        self,
        command_type: str,
        agent_id: str,
        parameters: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Send command through federation layer.

        Args:
            command_type: Type of command
            agent_id: Target agent ID
            parameters: Command parameters

        Returns:
            Federation response or None if failed
        """
        if not self.config.federation_mode:
            return None

        try:
            payload = {
                "command_type": command_type,
                "agent_id": agent_id,
                "parameters": parameters,
                "source_gateway": "brain_physical_gateway",
            }

            response = await self.http_client.post(
                f"{self.config.mlp_endpoint}/federation/command",
                json=payload,
            )

            response.raise_for_status()
            result = response.json()

            logger.info(f"✅ Command federated: {command_type} -> {agent_id}")
            return result

        except Exception as e:
            logger.error(f"Federation command failed: {e}")
            return None

    async def query_federation_status(self) -> Dict[str, Any]:
        """
        Query federation layer status.

        Returns:
            Federation status dictionary
        """
        if not self.config.federation_mode:
            return {"enabled": False}

        try:
            response = await self.http_client.get(
                f"{self.config.mlp_endpoint}/federation/status"
            )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Federation status query failed: {e}")
            return {"error": str(e)}

    # ========================================================================
    # Background Sync Loop
    # ========================================================================

    async def _sync_loop(self):
        """Background synchronization loop."""
        logger.info("Background sync loop started")

        while self.running:
            try:
                # Heartbeat to MLP
                await self._send_heartbeat()

                # Wait for next sync interval
                await asyncio.sleep(self.config.sync_interval_seconds)

            except asyncio.CancelledError:
                break

            except Exception as e:
                logger.error(f"Sync loop error: {e}")
                await asyncio.sleep(5.0)  # Wait before retry

        logger.info("Background sync loop stopped")

    async def _send_heartbeat(self):
        """Send heartbeat to MLP."""
        try:
            payload = {
                "gateway_id": "brain_physical_gateway",
                "timestamp": datetime.utcnow().isoformat(),
                "synced_agents": len(self.agent_sync_status),
                "federation_enabled": self.config.federation_mode,
            }

            response = await self.http_client.post(
                f"{self.config.mlp_endpoint}/heartbeat",
                json=payload,
            )

            if response.status_code == 200:
                logger.debug("Heartbeat sent to MLP")

        except Exception as e:
            logger.debug(f"Heartbeat failed: {e}")

    # ========================================================================
    # Status & Statistics
    # ========================================================================

    def get_sync_status(self, agent_id: str) -> Optional[MLPAgentSync]:
        """
        Get sync status for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Sync status or None if not found
        """
        return self.agent_sync_status.get(agent_id)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get connector statistics.

        Returns:
            Statistics dictionary
        """
        successful_syncs = sum(
            1 for s in self.agent_sync_status.values() if s.sync_status == "success"
        )
        failed_syncs = sum(
            1 for s in self.agent_sync_status.values() if s.sync_status == "failed"
        )

        return {
            "enabled": self.config.enabled,
            "federation_mode": self.config.federation_mode,
            "mlp_endpoint": self.config.mlp_endpoint,
            "total_synced_agents": len(self.agent_sync_status),
            "successful_syncs": successful_syncs,
            "failed_syncs": failed_syncs,
            "running": self.running,
        }


# ============================================================================
# Singleton
# ============================================================================

_builder_connector: Optional[BuilderToolkitConnector] = None


def get_builder_connector(
    config: Optional[BuilderToolkitConfig] = None,
) -> BuilderToolkitConnector:
    """
    Get singleton BuilderToolkitConnector instance.

    Args:
        config: Configuration (only used on first call)

    Returns:
        BuilderToolkitConnector instance
    """
    global _builder_connector

    if _builder_connector is None:
        if config is None:
            # Default configuration
            config = BuilderToolkitConfig(
                enabled=False,  # Disabled by default
                mlp_endpoint="http://localhost:8100",
            )

        _builder_connector = BuilderToolkitConnector(config)

    return _builder_connector
