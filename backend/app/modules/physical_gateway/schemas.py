"""
Physical Gateway Schemas

Pydantic models for physical agents gateway.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class PhysicalAgentState(str, Enum):
    """Physical agent operational state."""

    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    CHARGING = "charging"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    EMERGENCY_STOP = "emergency_stop"


class AgentCapability(str, Enum):
    """Physical agent capabilities."""

    NAVIGATION = "navigation"
    MANIPULATION = "manipulation"
    SENSING = "sensing"
    COMMUNICATION = "communication"
    DELIVERY = "delivery"
    INSPECTION = "inspection"
    WELDING = "welding"
    ASSEMBLY = "assembly"
    PAINTING = "painting"
    CLEANING = "cleaning"
    SURVEILLANCE = "surveillance"
    AGRICULTURAL = "agricultural"


class CommandPriority(str, Enum):
    """Command priority levels."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class CommandStatus(str, Enum):
    """Command execution status."""

    PENDING = "pending"
    VALIDATING = "validating"
    AUTHORIZED = "authorized"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class ProtocolType(str, Enum):
    """Communication protocol types."""

    REST_API = "rest_api"
    WEBSOCKET = "websocket"
    MQTT = "mqtt"
    ROS2 = "ros2"
    GRPC = "grpc"
    MODBUS = "modbus"
    OPCUA = "opcua"


# ============================================================================
# Core Models
# ============================================================================


class GatewayInfo(BaseModel):
    """Physical Gateway system information."""

    name: str = "BRAIN Physical Agents Gateway"
    version: str = "1.0.0"
    description: str = "Secure gateway for physical agents and IoT devices"
    status: str = "operational"
    connected_agents: int = 0
    total_commands_processed: int = 0
    uptime_seconds: float = 0.0
    supported_protocols: List[ProtocolType] = Field(default_factory=list)
    security_level: str = "high"
    audit_enabled: bool = True


class Position3D(BaseModel):
    """3D position in space."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    reference_frame: str = "world"


class PhysicalAgentInfo(BaseModel):
    """Physical agent information."""

    agent_id: str = Field(..., description="Unique agent identifier")
    name: str = Field(..., description="Agent name")
    agent_type: str = Field(..., description="Type of physical agent (robot, drone, etc.)")
    state: PhysicalAgentState = PhysicalAgentState.OFFLINE
    capabilities: List[AgentCapability] = Field(default_factory=list)

    # Connection
    protocol: ProtocolType = ProtocolType.REST_API
    endpoint: str = Field(..., description="Agent endpoint URL")
    connected: bool = False
    last_heartbeat: Optional[datetime] = None

    # Status
    battery_percentage: Optional[float] = None
    position: Optional[Position3D] = None
    current_task_id: Optional[str] = None
    error_message: Optional[str] = None

    # Metadata
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None

    # Statistics
    uptime_hours: float = 0.0
    tasks_completed: int = 0
    errors_encountered: int = 0

    # Timestamps
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class AgentRegisterRequest(BaseModel):
    """Request to register a physical agent."""

    agent_id: str
    name: str
    agent_type: str
    capabilities: List[AgentCapability]
    protocol: ProtocolType
    endpoint: str
    firmware_version: Optional[str] = None
    hardware_version: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    initial_position: Optional[Position3D] = None


class AgentUpdateRequest(BaseModel):
    """Request to update agent status."""

    state: Optional[PhysicalAgentState] = None
    battery_percentage: Optional[float] = None
    position: Optional[Position3D] = None
    current_task_id: Optional[str] = None
    error_message: Optional[str] = None


# ============================================================================
# Commands
# ============================================================================


class GatewayCommand(BaseModel):
    """Command to be executed on physical agent."""

    command_id: str = Field(..., description="Unique command identifier")
    agent_id: str = Field(..., description="Target agent ID")
    command_type: str = Field(..., description="Type of command (move, pick, etc.)")
    priority: CommandPriority = CommandPriority.NORMAL

    # Command parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # Security
    requires_authorization: bool = True
    authorized_by: Optional[str] = None
    authorization_token: Optional[str] = None

    # Status
    status: CommandStatus = CommandStatus.PENDING
    validation_result: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    # Timing
    timeout_seconds: float = 300.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CommandRequest(BaseModel):
    """Request to execute a command."""

    agent_id: str
    command_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: CommandPriority = CommandPriority.NORMAL
    timeout_seconds: float = 300.0
    authorization_token: Optional[str] = None


class CommandResponse(BaseModel):
    """Response from command execution."""

    command_id: str
    agent_id: str
    status: CommandStatus
    success: bool
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CommandStatusQuery(BaseModel):
    """Query for command status."""

    command_id: str


# ============================================================================
# Security & Authentication
# ============================================================================


class SecurityHandshake(BaseModel):
    """Security handshake for agent connection."""

    agent_id: str
    challenge: str = Field(..., description="Challenge nonce")
    response: str = Field(..., description="Signed response")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    certificate: Optional[str] = None


class HandshakeResponse(BaseModel):
    """Response to security handshake."""

    success: bool
    session_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ValidationResult(BaseModel):
    """Result of command validation."""

    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    safety_score: float = Field(ge=0.0, le=1.0, default=1.0)
    details: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Audit Trail
# ============================================================================


class AuditEvent(BaseModel):
    """Audit trail event."""

    event_id: str = Field(..., description="Unique event ID")
    event_type: str = Field(..., description="Type of event")
    agent_id: Optional[str] = None
    command_id: Optional[str] = None
    user_id: Optional[str] = None

    # Event details
    action: str = Field(..., description="Action performed")
    status: str = Field(..., description="Event status (success/failure)")
    details: Dict[str, Any] = Field(default_factory=dict)

    # Context
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None

    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AuditQuery(BaseModel):
    """Query for audit trail."""

    agent_id: Optional[str] = None
    command_id: Optional[str] = None
    event_type: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: int = Field(default=100, ge=1, le=1000)


# ============================================================================
# Builder Toolkit / MLP Integration
# ============================================================================


class BuilderToolkitConfig(BaseModel):
    """Builder Toolkit integration configuration."""

    enabled: bool = True
    mlp_endpoint: str = Field(..., description="MLP API endpoint")
    api_key: Optional[str] = None
    federation_mode: bool = False
    sync_interval_seconds: float = 60.0


class MLPAgentSync(BaseModel):
    """Sync status with MLP."""

    agent_id: str
    mlp_agent_id: str
    last_sync: datetime
    sync_status: str
    sync_errors: List[str] = Field(default_factory=list)


# ============================================================================
# Statistics & Monitoring
# ============================================================================


class GatewayStatistics(BaseModel):
    """Gateway operational statistics."""

    total_agents_registered: int = 0
    agents_online: int = 0
    agents_offline: int = 0
    agents_by_state: Dict[str, int] = Field(default_factory=dict)

    total_commands_executed: int = 0
    commands_successful: int = 0
    commands_failed: int = 0
    commands_pending: int = 0
    average_command_duration_seconds: float = 0.0

    total_audit_events: int = 0
    security_violations: int = 0

    uptime_seconds: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class HealthStatus(BaseModel):
    """Gateway health status."""

    healthy: bool = True
    components: Dict[str, bool] = Field(default_factory=dict)
    issues: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
