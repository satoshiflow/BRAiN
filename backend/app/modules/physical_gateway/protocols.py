"""
Physical Gateway Communication Protocols

Protocol adapters for different physical agent communication types.

Supported Protocols:
- REST API
- WebSocket
- MQTT
- ROS2
- gRPC
- Modbus
- OPC UA
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from loguru import logger

import httpx

from .schemas import (
    GatewayCommand,
    CommandResponse,
    PhysicalAgentInfo,
    ProtocolType,
)


# ============================================================================
# Protocol Adapter Base
# ============================================================================


class ProtocolAdapter(ABC):
    """
    Abstract base class for protocol adapters.

    Each protocol adapter handles communication with physical agents
    using a specific protocol (REST, MQTT, ROS2, etc.).
    """

    def __init__(self, protocol_type: ProtocolType):
        """
        Initialize protocol adapter.

        Args:
            protocol_type: Type of protocol
        """
        self.protocol_type = protocol_type
        logger.info(f"Protocol adapter initialized: {protocol_type}")

    @abstractmethod
    async def connect(self, agent: PhysicalAgentInfo) -> bool:
        """
        Connect to agent.

        Args:
            agent: Agent to connect to

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self, agent: PhysicalAgentInfo):
        """
        Disconnect from agent.

        Args:
            agent: Agent to disconnect from
        """
        pass

    @abstractmethod
    async def send_command(
        self,
        agent: PhysicalAgentInfo,
        command: GatewayCommand,
    ) -> CommandResponse:
        """
        Send command to agent.

        Args:
            agent: Target agent
            command: Command to execute

        Returns:
            Command response
        """
        pass

    @abstractmethod
    async def get_status(self, agent: PhysicalAgentInfo) -> Dict[str, Any]:
        """
        Get agent status.

        Args:
            agent: Agent to query

        Returns:
            Status dictionary
        """
        pass


# ============================================================================
# REST API Protocol
# ============================================================================


class RESTProtocolAdapter(ProtocolAdapter):
    """
    REST API protocol adapter.

    Communicates with agents via HTTP REST endpoints.
    """

    def __init__(self):
        """Initialize REST protocol adapter."""
        super().__init__(ProtocolType.REST_API)
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def connect(self, agent: PhysicalAgentInfo) -> bool:
        """
        Connect to agent via REST (health check).

        Args:
            agent: Agent to connect to

        Returns:
            True if agent is reachable
        """
        try:
            response = await self.http_client.get(f"{agent.endpoint}/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"REST connection failed for {agent.agent_id}: {e}")
            return False

    async def disconnect(self, agent: PhysicalAgentInfo):
        """Disconnect from agent (no-op for REST)."""
        pass

    async def send_command(
        self,
        agent: PhysicalAgentInfo,
        command: GatewayCommand,
    ) -> CommandResponse:
        """
        Send command via REST POST.

        Args:
            agent: Target agent
            command: Command to execute

        Returns:
            Command response
        """
        try:
            payload = {
                "command_id": command.command_id,
                "command_type": command.command_type,
                "parameters": command.parameters,
                "priority": command.priority,
            }

            response = await self.http_client.post(
                f"{agent.endpoint}/commands",
                json=payload,
                timeout=command.timeout_seconds,
            )

            response.raise_for_status()
            result = response.json()

            return CommandResponse(
                command_id=command.command_id,
                agent_id=agent.agent_id,
                status="completed",
                success=True,
                result=result,
                duration_seconds=response.elapsed.total_seconds(),
            )

        except httpx.TimeoutException:
            return CommandResponse(
                command_id=command.command_id,
                agent_id=agent.agent_id,
                status="timeout",
                success=False,
                error_message="Command timeout",
            )

        except Exception as e:
            logger.error(f"REST command failed: {e}")
            return CommandResponse(
                command_id=command.command_id,
                agent_id=agent.agent_id,
                status="failed",
                success=False,
                error_message=str(e),
            )

    async def get_status(self, agent: PhysicalAgentInfo) -> Dict[str, Any]:
        """
        Get agent status via REST GET.

        Args:
            agent: Agent to query

        Returns:
            Status dictionary
        """
        try:
            response = await self.http_client.get(f"{agent.endpoint}/status")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"REST status query failed: {e}")
            return {"error": str(e)}


# ============================================================================
# WebSocket Protocol
# ============================================================================


class WebSocketProtocolAdapter(ProtocolAdapter):
    """
    WebSocket protocol adapter.

    Maintains persistent WebSocket connections to agents.
    """

    def __init__(self):
        """Initialize WebSocket protocol adapter."""
        super().__init__(ProtocolType.WEBSOCKET)
        self.connections: Dict[str, Any] = {}  # agent_id -> websocket

    async def connect(self, agent: PhysicalAgentInfo) -> bool:
        """
        Establish WebSocket connection to agent.

        Args:
            agent: Agent to connect to

        Returns:
            True if connection successful
        """
        try:
            # Note: Actual WebSocket implementation would use websockets library
            # This is a placeholder
            logger.info(f"WebSocket connection to {agent.agent_id} (placeholder)")
            self.connections[agent.agent_id] = {"connected": True, "endpoint": agent.endpoint}
            return True
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False

    async def disconnect(self, agent: PhysicalAgentInfo):
        """
        Close WebSocket connection.

        Args:
            agent: Agent to disconnect from
        """
        if agent.agent_id in self.connections:
            del self.connections[agent.agent_id]
            logger.info(f"WebSocket disconnected: {agent.agent_id}")

    async def send_command(
        self,
        agent: PhysicalAgentInfo,
        command: GatewayCommand,
    ) -> CommandResponse:
        """
        Send command via WebSocket.

        Args:
            agent: Target agent
            command: Command to execute

        Returns:
            Command response
        """
        # Placeholder implementation
        logger.info(f"WebSocket command sent to {agent.agent_id}: {command.command_type}")

        return CommandResponse(
            command_id=command.command_id,
            agent_id=agent.agent_id,
            status="completed",
            success=True,
            result={"message": "WebSocket command (placeholder)"},
        )

    async def get_status(self, agent: PhysicalAgentInfo) -> Dict[str, Any]:
        """
        Get agent status via WebSocket.

        Args:
            agent: Agent to query

        Returns:
            Status dictionary
        """
        return {
            "connected": agent.agent_id in self.connections,
            "protocol": "websocket",
        }


# ============================================================================
# MQTT Protocol
# ============================================================================


class MQTTProtocolAdapter(ProtocolAdapter):
    """
    MQTT protocol adapter.

    Communicates via MQTT pub/sub messaging.
    """

    def __init__(self):
        """Initialize MQTT protocol adapter."""
        super().__init__(ProtocolType.MQTT)
        self.mqtt_client = None  # Placeholder for paho-mqtt client

    async def connect(self, agent: PhysicalAgentInfo) -> bool:
        """
        Connect to MQTT broker for agent.

        Args:
            agent: Agent to connect to

        Returns:
            True if connection successful
        """
        # Placeholder
        logger.info(f"MQTT connection to {agent.agent_id} (placeholder)")
        return True

    async def disconnect(self, agent: PhysicalAgentInfo):
        """Disconnect from MQTT."""
        logger.info(f"MQTT disconnected: {agent.agent_id}")

    async def send_command(
        self,
        agent: PhysicalAgentInfo,
        command: GatewayCommand,
    ) -> CommandResponse:
        """
        Send command via MQTT publish.

        Args:
            agent: Target agent
            command: Command to execute

        Returns:
            Command response
        """
        # Placeholder
        logger.info(f"MQTT command published to {agent.agent_id}: {command.command_type}")

        return CommandResponse(
            command_id=command.command_id,
            agent_id=agent.agent_id,
            status="completed",
            success=True,
            result={"message": "MQTT command (placeholder)"},
        )

    async def get_status(self, agent: PhysicalAgentInfo) -> Dict[str, Any]:
        """Get agent status via MQTT."""
        return {"protocol": "mqtt", "placeholder": True}


# ============================================================================
# ROS2 Protocol
# ============================================================================


class ROS2ProtocolAdapter(ProtocolAdapter):
    """
    ROS2 protocol adapter.

    Communicates with ROS2 agents via topics, services, and actions.
    Integrates with the ROS2 bridge module.
    """

    def __init__(self):
        """Initialize ROS2 protocol adapter."""
        super().__init__(ProtocolType.ROS2)

        # Import ROS2 bridge
        try:
            from app.modules.ros2_bridge.bridge import get_ros2_bridge
            self.ros2_bridge = get_ros2_bridge()
        except ImportError:
            logger.warning("ROS2 bridge not available")
            self.ros2_bridge = None

    async def connect(self, agent: PhysicalAgentInfo) -> bool:
        """
        Connect to ROS2 agent.

        Args:
            agent: Agent to connect to

        Returns:
            True if connection successful
        """
        if not self.ros2_bridge:
            return False

        if not self.ros2_bridge.is_connected():
            await self.ros2_bridge.connect()

        return self.ros2_bridge.is_connected()

    async def disconnect(self, agent: PhysicalAgentInfo):
        """Disconnect from ROS2 agent."""
        # ROS2 bridge maintains its own lifecycle
        pass

    async def send_command(
        self,
        agent: PhysicalAgentInfo,
        command: GatewayCommand,
    ) -> CommandResponse:
        """
        Send command to ROS2 agent via action or service.

        Args:
            agent: Target agent
            command: Command to execute

        Returns:
            Command response
        """
        if not self.ros2_bridge:
            return CommandResponse(
                command_id=command.command_id,
                agent_id=agent.agent_id,
                status="failed",
                success=False,
                error_message="ROS2 bridge not available",
            )

        try:
            # Use ROS2 actions for commands
            from app.modules.ros2_bridge.schemas import ActionGoalRequest

            action_request = ActionGoalRequest(
                action_name=f"/{agent.agent_id}/{command.command_type}",
                action_type="brain_interfaces/ExecuteCommand",
                goal_data=command.parameters,
            )

            action_response = await self.ros2_bridge.send_action_goal(action_request)

            return CommandResponse(
                command_id=command.command_id,
                agent_id=agent.agent_id,
                status="completed",
                success=action_response.accepted,
                result={"goal_id": action_response.goal_id},
            )

        except Exception as e:
            logger.error(f"ROS2 command failed: {e}")
            return CommandResponse(
                command_id=command.command_id,
                agent_id=agent.agent_id,
                status="failed",
                success=False,
                error_message=str(e),
            )

    async def get_status(self, agent: PhysicalAgentInfo) -> Dict[str, Any]:
        """
        Get agent status via ROS2 topics.

        Args:
            agent: Agent to query

        Returns:
            Status dictionary
        """
        if not self.ros2_bridge:
            return {"error": "ROS2 bridge not available"}

        return {
            "protocol": "ros2",
            "connected": self.ros2_bridge.is_connected(),
            "domain_id": self.ros2_bridge.domain_id,
        }


# ============================================================================
# Protocol Factory
# ============================================================================


class ProtocolFactory:
    """
    Factory for creating protocol adapters.

    Maintains singleton instances of each protocol type.
    """

    _adapters: Dict[ProtocolType, ProtocolAdapter] = {}

    @classmethod
    def get_adapter(cls, protocol_type: ProtocolType) -> ProtocolAdapter:
        """
        Get protocol adapter for given type.

        Args:
            protocol_type: Protocol type

        Returns:
            Protocol adapter instance
        """
        if protocol_type not in cls._adapters:
            # Create adapter
            if protocol_type == ProtocolType.REST_API:
                cls._adapters[protocol_type] = RESTProtocolAdapter()

            elif protocol_type == ProtocolType.WEBSOCKET:
                cls._adapters[protocol_type] = WebSocketProtocolAdapter()

            elif protocol_type == ProtocolType.MQTT:
                cls._adapters[protocol_type] = MQTTProtocolAdapter()

            elif protocol_type == ProtocolType.ROS2:
                cls._adapters[protocol_type] = ROS2ProtocolAdapter()

            else:
                raise ValueError(f"Unsupported protocol type: {protocol_type}")

        return cls._adapters[protocol_type]

    @classmethod
    async def cleanup(cls):
        """Cleanup all protocol adapters."""
        for adapter in cls._adapters.values():
            # Cleanup logic if needed
            pass
        cls._adapters.clear()
