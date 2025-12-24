"""
Physical Gateway Service

Main service orchestrating physical agents gateway operations.

Features:
- Agent registration and lifecycle management
- Command execution with validation and authorization
- Multi-protocol support
- Security and audit trail
- MLP/Builder Toolkit integration
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from .schemas import (
    GatewayInfo,
    PhysicalAgentInfo,
    PhysicalAgentState,
    AgentRegisterRequest,
    AgentUpdateRequest,
    GatewayCommand,
    CommandRequest,
    CommandResponse,
    CommandStatus,
    SecurityHandshake,
    HandshakeResponse,
    ValidationResult,
    AuditQuery,
    AuditEvent,
    GatewayStatistics,
    HealthStatus,
    BuilderToolkitConfig,
    ProtocolType,
)
from .security import get_security_manager, get_command_validator
from .audit import get_audit_manager
from .protocols import ProtocolFactory
from .builder_connector import get_builder_connector


# ============================================================================
# Physical Gateway Service
# ============================================================================


class PhysicalGatewayService:
    """
    Physical Agents Gateway Service.

    Orchestrates:
    - Agent registration and management
    - Command execution and validation
    - Security and authentication
    - Audit trail
    - Protocol adapters
    - MLP integration
    """

    def __init__(self):
        """Initialize Physical Gateway Service."""
        self.name = "BRAIN Physical Agents Gateway"
        self.version = "1.0.0"
        self.start_time = time.time()

        # Storage
        self.agents: Dict[str, PhysicalAgentInfo] = {}  # agent_id -> agent_info
        self.commands: Dict[str, GatewayCommand] = {}  # command_id -> command

        # Components
        self.security_manager = get_security_manager()
        self.command_validator = get_command_validator()
        self.audit_manager = get_audit_manager()

        # Builder Toolkit (optional)
        self.builder_connector = None  # Initialized on demand

        # Statistics
        self.total_commands_processed = 0
        self.successful_commands = 0
        self.failed_commands = 0

        logger.info("Physical Gateway Service initialized")

    # ========================================================================
    # Gateway Info
    # ========================================================================

    def get_info(self) -> GatewayInfo:
        """
        Get gateway information.

        Returns:
            Gateway info
        """
        uptime = time.time() - self.start_time

        return GatewayInfo(
            name=self.name,
            version=self.version,
            description="Secure gateway for physical agents and IoT devices",
            status="operational",
            connected_agents=len([a for a in self.agents.values() if a.connected]),
            total_commands_processed=self.total_commands_processed,
            uptime_seconds=uptime,
            supported_protocols=[
                ProtocolType.REST_API,
                ProtocolType.WEBSOCKET,
                ProtocolType.MQTT,
                ProtocolType.ROS2,
            ],
            security_level="high",
            audit_enabled=True,
        )

    # ========================================================================
    # Agent Management
    # ========================================================================

    async def register_agent(
        self,
        request: AgentRegisterRequest,
    ) -> PhysicalAgentInfo:
        """
        Register a physical agent.

        Args:
            request: Agent registration request

        Returns:
            Registered agent information

        Raises:
            ValueError: If agent already registered
        """
        agent_id = request.agent_id

        # Check if already registered
        if agent_id in self.agents:
            raise ValueError(f"Agent {agent_id} already registered")

        # Create agent
        agent = PhysicalAgentInfo(
            agent_id=agent_id,
            name=request.name,
            agent_type=request.agent_type,
            state=PhysicalAgentState.OFFLINE,
            capabilities=request.capabilities,
            protocol=request.protocol,
            endpoint=request.endpoint,
            connected=False,
            firmware_version=request.firmware_version,
            hardware_version=request.hardware_version,
            manufacturer=request.manufacturer,
            model=request.model,
            serial_number=request.serial_number,
            position=request.initial_position,
        )

        # Store agent
        self.agents[agent_id] = agent

        # Audit log
        self.audit_manager.log_agent_event(
            agent_id=agent_id,
            action="agent_registered",
            status="success",
            details={
                "name": request.name,
                "type": request.agent_type,
                "protocol": request.protocol.value,
            },
        )

        # Sync with MLP if enabled
        if self.builder_connector:
            await self.builder_connector.sync_agent(agent)

        logger.info(f"✅ Agent registered: {agent_id} ({request.name})")

        return agent

    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister a physical agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if unregistered successfully
        """
        if agent_id not in self.agents:
            return False

        agent = self.agents[agent_id]

        # Disconnect if connected
        if agent.connected:
            await self._disconnect_agent(agent)

        # Remove from storage
        del self.agents[agent_id]

        # Revoke security session
        self.security_manager.revoke_session(agent_id)

        # Audit log
        self.audit_manager.log_agent_event(
            agent_id=agent_id,
            action="agent_unregistered",
            status="success",
        )

        # Unsync from MLP if enabled
        if self.builder_connector:
            await self.builder_connector.unsync_agent(agent_id)

        logger.info(f"✅ Agent unregistered: {agent_id}")

        return True

    def get_agent(self, agent_id: str) -> Optional[PhysicalAgentInfo]:
        """
        Get agent information.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent info or None if not found
        """
        return self.agents.get(agent_id)

    def list_agents(
        self,
        state: Optional[PhysicalAgentState] = None,
    ) -> List[PhysicalAgentInfo]:
        """
        List registered agents.

        Args:
            state: Optional state filter

        Returns:
            List of agents
        """
        agents = list(self.agents.values())

        if state:
            agents = [a for a in agents if a.state == state]

        return agents

    async def update_agent_status(
        self,
        agent_id: str,
        request: AgentUpdateRequest,
    ) -> PhysicalAgentInfo:
        """
        Update agent status.

        Args:
            agent_id: Agent identifier
            request: Update request

        Returns:
            Updated agent information

        Raises:
            ValueError: If agent not found
        """
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Update fields
        if request.state is not None:
            agent.state = request.state

        if request.battery_percentage is not None:
            agent.battery_percentage = request.battery_percentage

        if request.position is not None:
            agent.position = request.position

        if request.current_task_id is not None:
            agent.current_task_id = request.current_task_id

        if request.error_message is not None:
            agent.error_message = request.error_message

        agent.last_updated = datetime.utcnow()
        agent.last_heartbeat = datetime.utcnow()

        # Audit log
        self.audit_manager.log_agent_event(
            agent_id=agent_id,
            action="agent_status_updated",
            status="success",
            details={"state": agent.state.value if agent.state else None},
        )

        # Sync with MLP if enabled
        if self.builder_connector:
            await self.builder_connector.sync_agent(agent)

        return agent

    async def _disconnect_agent(self, agent: PhysicalAgentInfo):
        """
        Disconnect agent.

        Args:
            agent: Agent to disconnect
        """
        try:
            adapter = ProtocolFactory.get_adapter(agent.protocol)
            await adapter.disconnect(agent)
            agent.connected = False
            agent.state = PhysicalAgentState.OFFLINE
        except Exception as e:
            logger.error(f"Failed to disconnect agent {agent.agent_id}: {e}")

    # ========================================================================
    # Authentication
    # ========================================================================

    def initiate_handshake(self, agent_id: str) -> str:
        """
        Initiate security handshake for agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Challenge nonce
        """
        challenge = self.security_manager.generate_challenge(agent_id)

        # Audit log
        self.audit_manager.log_auth_event(
            agent_id=agent_id,
            action="handshake_initiated",
            status="success",
        )

        return challenge

    def complete_handshake(
        self,
        handshake: SecurityHandshake,
    ) -> HandshakeResponse:
        """
        Complete security handshake.

        Args:
            handshake: Handshake request from agent

        Returns:
            Handshake response with session token
        """
        response = self.security_manager.verify_handshake(handshake)

        # Audit log
        self.audit_manager.log_auth_event(
            agent_id=handshake.agent_id,
            action="handshake_completed",
            status="success" if response.success else "failure",
            details={"error": response.error_message} if not response.success else {},
        )

        # Update agent connection status
        if response.success and handshake.agent_id in self.agents:
            agent = self.agents[handshake.agent_id]
            agent.connected = True
            agent.state = PhysicalAgentState.IDLE
            agent.last_heartbeat = datetime.utcnow()

        return response

    # ========================================================================
    # Command Execution
    # ========================================================================

    async def execute_command(
        self,
        request: CommandRequest,
        session_token: Optional[str] = None,
    ) -> CommandResponse:
        """
        Execute command on physical agent.

        Args:
            request: Command request
            session_token: Session token for authorization

        Returns:
            Command response
        """
        agent_id = request.agent_id
        start_time = time.time()

        # Check if agent exists
        agent = self.agents.get(agent_id)
        if not agent:
            return CommandResponse(
                command_id=f"CMD-{int(time.time() * 1000)}",
                agent_id=agent_id,
                status=CommandStatus.REJECTED,
                success=False,
                error_message=f"Agent {agent_id} not found",
            )

        # Create command
        command_id = f"CMD-{agent_id}-{int(time.time() * 1000)}"
        command = GatewayCommand(
            command_id=command_id,
            agent_id=agent_id,
            command_type=request.command_type,
            priority=request.priority,
            parameters=request.parameters,
            timeout_seconds=request.timeout_seconds,
        )

        self.commands[command_id] = command

        # Audit log: command received
        self.audit_manager.log_command_event(
            command_id=command_id,
            agent_id=agent_id,
            action="command_received",
            status="success",
            details={
                "command_type": request.command_type,
                "priority": request.priority.value,
            },
        )

        # Step 1: Authorization
        command.status = CommandStatus.VALIDATING
        authorized, auth_error = self.security_manager.authorize_command(
            agent_id=agent_id,
            command=command,
            session_token=session_token,
        )

        if not authorized:
            command.status = CommandStatus.REJECTED
            command.error_message = auth_error

            self.audit_manager.log_security_event(
                action="command_rejected",
                status="failure",
                agent_id=agent_id,
                details={"reason": auth_error, "command_id": command_id},
            )

            return CommandResponse(
                command_id=command_id,
                agent_id=agent_id,
                status=CommandStatus.REJECTED,
                success=False,
                error_message=auth_error,
            )

        command.status = CommandStatus.AUTHORIZED

        # Step 2: Validation
        validation_result = self.command_validator.validate_command(command, agent)
        command.validation_result = validation_result.model_dump()

        if not validation_result.valid:
            command.status = CommandStatus.REJECTED
            command.error_message = f"Validation failed: {validation_result.errors}"

            self.audit_manager.log_command_event(
                command_id=command_id,
                agent_id=agent_id,
                action="command_validation_failed",
                status="failure",
                details={"errors": validation_result.errors},
            )

            return CommandResponse(
                command_id=command_id,
                agent_id=agent_id,
                status=CommandStatus.REJECTED,
                success=False,
                error_message=command.error_message,
            )

        # Step 3: Execute via protocol adapter
        command.status = CommandStatus.EXECUTING
        command.started_at = datetime.utcnow()

        try:
            adapter = ProtocolFactory.get_adapter(agent.protocol)
            response = await adapter.send_command(agent, command)

            # Update command
            command.status = CommandStatus.COMPLETED if response.success else CommandStatus.FAILED
            command.completed_at = datetime.utcnow()
            command.execution_result = response.result

            # Update statistics
            self.total_commands_processed += 1
            if response.success:
                self.successful_commands += 1
            else:
                self.failed_commands += 1

            # Audit log
            self.audit_manager.log_command_event(
                command_id=command_id,
                agent_id=agent_id,
                action="command_executed",
                status="success" if response.success else "failure",
                details={
                    "duration_seconds": response.duration_seconds,
                    "result": response.result,
                },
            )

            duration = time.time() - start_time
            response.duration_seconds = duration

            return response

        except Exception as e:
            logger.error(f"Command execution failed: {e}")

            command.status = CommandStatus.FAILED
            command.error_message = str(e)
            command.completed_at = datetime.utcnow()

            self.failed_commands += 1

            self.audit_manager.log_command_event(
                command_id=command_id,
                agent_id=agent_id,
                action="command_execution_error",
                status="failure",
                details={"error": str(e)},
            )

            return CommandResponse(
                command_id=command_id,
                agent_id=agent_id,
                status=CommandStatus.FAILED,
                success=False,
                error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    def get_command_status(self, command_id: str) -> Optional[GatewayCommand]:
        """
        Get command status.

        Args:
            command_id: Command identifier

        Returns:
            Command or None if not found
        """
        return self.commands.get(command_id)

    # ========================================================================
    # Audit Trail
    # ========================================================================

    def query_audit_trail(self, query: AuditQuery) -> List[AuditEvent]:
        """
        Query audit trail.

        Args:
            query: Audit query parameters

        Returns:
            List of audit events
        """
        return self.audit_manager.query_events(query)

    def verify_audit_integrity(self) -> tuple[bool, List[str]]:
        """
        Verify audit trail integrity.

        Returns:
            (is_valid, list_of_errors)
        """
        return self.audit_manager.verify_integrity()

    # ========================================================================
    # Statistics & Health
    # ========================================================================

    def get_statistics(self) -> GatewayStatistics:
        """
        Get gateway statistics.

        Returns:
            Gateway statistics
        """
        agents_by_state: Dict[str, int] = {}
        for state in PhysicalAgentState:
            count = len([a for a in self.agents.values() if a.state == state])
            if count > 0:
                agents_by_state[state.value] = count

        # Command statistics
        pending_commands = len(
            [c for c in self.commands.values() if c.status == CommandStatus.PENDING]
        )

        # Average command duration
        completed_commands = [
            c
            for c in self.commands.values()
            if c.status == CommandStatus.COMPLETED and c.started_at and c.completed_at
        ]

        avg_duration = 0.0
        if completed_commands:
            durations = [
                (c.completed_at - c.started_at).total_seconds()
                for c in completed_commands
            ]
            avg_duration = sum(durations) / len(durations)

        # Audit statistics
        audit_stats = self.audit_manager.get_statistics()

        return GatewayStatistics(
            total_agents_registered=len(self.agents),
            agents_online=len([a for a in self.agents.values() if a.connected]),
            agents_offline=len([a for a in self.agents.values() if not a.connected]),
            agents_by_state=agents_by_state,
            total_commands_executed=self.total_commands_processed,
            commands_successful=self.successful_commands,
            commands_failed=self.failed_commands,
            commands_pending=pending_commands,
            average_command_duration_seconds=avg_duration,
            total_audit_events=audit_stats["total_events"],
            security_violations=0,  # Would track from audit events
            uptime_seconds=time.time() - self.start_time,
        )

    def get_health_status(self) -> HealthStatus:
        """
        Get gateway health status.

        Returns:
            Health status
        """
        issues: List[str] = []
        components: Dict[str, bool] = {}

        # Check components
        components["security_manager"] = True
        components["command_validator"] = True
        components["audit_manager"] = True

        # Check audit file
        audit_stats = self.audit_manager.get_statistics()
        components["audit_storage"] = audit_stats["storage_size_bytes"] > 0

        # Check MLP connector
        if self.builder_connector:
            mlp_stats = self.builder_connector.get_statistics()
            components["mlp_connector"] = mlp_stats["running"]

        # Overall health
        healthy = all(components.values())

        return HealthStatus(
            healthy=healthy,
            components=components,
            issues=issues,
        )

    # ========================================================================
    # MLP Integration
    # ========================================================================

    async def initialize_mlp_connector(
        self,
        config: BuilderToolkitConfig,
    ):
        """
        Initialize MLP/Builder Toolkit connector.

        Args:
            config: Builder Toolkit configuration
        """
        self.builder_connector = get_builder_connector(config)
        await self.builder_connector.start()
        logger.info("MLP connector initialized and started")

    async def shutdown(self):
        """Shutdown gateway service."""
        logger.info("Shutting down Physical Gateway Service...")

        # Stop MLP connector
        if self.builder_connector:
            await self.builder_connector.stop()

        # Cleanup protocol adapters
        await ProtocolFactory.cleanup()

        logger.info("✅ Physical Gateway Service shut down")


# ============================================================================
# Singleton
# ============================================================================

_gateway_service: Optional[PhysicalGatewayService] = None


def get_physical_gateway_service() -> PhysicalGatewayService:
    """Get singleton PhysicalGatewayService instance."""
    global _gateway_service
    if _gateway_service is None:
        _gateway_service = PhysicalGatewayService()
    return _gateway_service
