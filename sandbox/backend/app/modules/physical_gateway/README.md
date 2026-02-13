# Physical Agents Gateway

**Version:** 1.0.0
**Last Updated:** 2025-12-23

## Overview

The Physical Agents Gateway is a secure, enterprise-grade gateway for managing physical agents, IoT devices, and robotics systems within the BRAiN ecosystem.

### Key Features

- **Multi-Protocol Support**: REST API, WebSocket, MQTT, ROS2, gRPC, Modbus, OPC UA
- **Security-First Design**: Challenge-response authentication, session management, fail-closed architecture
- **Command Validation**: Safety checks, physical constraint validation, capability matching
- **Audit Trail**: Immutable append-only logging with hash-chain integrity
- **MLP Integration**: Builder Toolkit connector for federation layer communication
- **Protocol Adapters**: Abstracted protocol layer for easy integration
- **Fleet Integration**: Seamless integration with Fleet Management system
- **ROS2 Bridge**: Direct integration with ROS2 agents

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                Physical Agents Gateway                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Security   │  │  Validation  │  │  Audit Trail │      │
│  │   Manager    │  │   Engine     │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Physical Gateway Service                   │   │
│  │  - Agent Management                                   │   │
│  │  - Command Orchestration                              │   │
│  │  - Security & Authorization                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │            Protocol Adapters                          │   │
│  │  REST │ WebSocket │ MQTT │ ROS2 │ gRPC │ Modbus      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Builder Toolkit Connector (MLP)               │   │
│  │  - Federation Layer Interface                         │   │
│  │  - Agent Synchronization                              │   │
│  │  - Capability Discovery                               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
    Physical       IoT Devices    Drones         Industrial
    Robots                                        Robots
```

---

## Components

### 1. Security Manager

**File:** `security.py`

Handles authentication and authorization for physical agents.

**Features:**
- Challenge-response authentication using HMAC-SHA256
- Session token management with configurable expiry
- Rate limiting per agent (100 commands/minute default)
- Agent blocking/unblocking
- Fail-closed design

**Usage:**

```python
from app.modules.physical_gateway.security import get_security_manager

security = get_security_manager()

# Generate challenge for agent
challenge = security.generate_challenge("robot_001")

# Verify handshake
handshake = SecurityHandshake(
    agent_id="robot_001",
    challenge=challenge,
    response=compute_response(agent_id, challenge)
)

response = security.verify_handshake(handshake)
if response.success:
    session_token = response.session_token
```

### 2. Command Validator

**File:** `security.py`

Validates commands for safety and correctness.

**Validation Checks:**
- Agent state (error, emergency stop, maintenance)
- Battery level (critical: <5%, low: <20%)
- Physical parameters (velocity, acceleration, force)
- Dangerous command patterns
- Safety score calculation

**Usage:**

```python
from app.modules.physical_gateway.security import get_command_validator

validator = get_command_validator()

validation_result = validator.validate_command(command, agent)

if validation_result.valid:
    # Execute command
    pass
else:
    # Reject command
    print(f"Validation errors: {validation_result.errors}")
```

### 3. Audit Trail Manager

**File:** `audit.py`

Manages immutable audit logging with hash-chain integrity.

**Features:**
- Append-only JSONL storage
- Hash chain for tamper detection
- Event categorization (command, auth, security, agent)
- Query interface with filters
- Integrity verification

**Storage Format:**

```json
{
  "event_id": "EVT-2025-12-23T10:30:45.123456-000001",
  "event_type": "command",
  "action": "command_executed",
  "status": "success",
  "agent_id": "robot_001",
  "command_id": "CMD-robot_001-1703334645123",
  "details": {...},
  "timestamp": "2025-12-23T10:30:45.123456",
  "_hash": "sha256_hash_of_event",
  "_prev_hash": "sha256_hash_of_previous_event"
}
```

**Usage:**

```python
from app.modules.physical_gateway.audit import get_audit_manager

audit = get_audit_manager()

# Log event
audit.log_command_event(
    command_id="CMD-123",
    agent_id="robot_001",
    action="command_executed",
    status="success",
    details={"duration": 2.5}
)

# Query events
events = audit.query_events(
    AuditQuery(
        agent_id="robot_001",
        start_time=datetime(2025, 12, 23),
        limit=100
    )
)

# Verify integrity
is_valid, errors = audit.verify_integrity()
```

### 4. Protocol Adapters

**File:** `protocols.py`

Abstracted protocol layer for multi-protocol support.

**Supported Protocols:**
- **REST API**: HTTP-based communication
- **WebSocket**: Persistent bidirectional communication
- **MQTT**: Pub/sub messaging
- **ROS2**: Integration with ROS2 bridge
- **gRPC**: (Placeholder for future implementation)
- **Modbus**: Industrial automation protocol
- **OPC UA**: Industrial automation standard

**Usage:**

```python
from app.modules.physical_gateway.protocols import ProtocolFactory
from app.modules.physical_gateway.schemas import ProtocolType

# Get protocol adapter
adapter = ProtocolFactory.get_adapter(ProtocolType.REST_API)

# Connect to agent
connected = await adapter.connect(agent)

# Send command
response = await adapter.send_command(agent, command)

# Get status
status = await adapter.get_status(agent)
```

### 5. Builder Toolkit Connector

**File:** `builder_connector.py`

Integration with MLP (Machine Learning Pipeline) and Builder Toolkit.

**Features:**
- Agent synchronization with MLP
- Capability-based agent discovery
- Task delegation to MLP
- Federation layer communication
- Background heartbeat sync

**Usage:**

```python
from app.modules.physical_gateway.builder_connector import get_builder_connector
from app.modules.physical_gateway.schemas import BuilderToolkitConfig

config = BuilderToolkitConfig(
    enabled=True,
    mlp_endpoint="http://mlp.example.com:8100",
    api_key="your_api_key",
    federation_mode=True,
    sync_interval_seconds=60.0
)

connector = get_builder_connector(config)
await connector.start()

# Sync agent with MLP
await connector.sync_agent(agent)

# Discover agents by capability
agents = await connector.discover_capabilities([
    AgentCapability.NAVIGATION,
    AgentCapability.DELIVERY
])

# Delegate task to MLP
result = await connector.delegate_task(
    task_type="multi_robot_delivery",
    task_description="Deliver packages to 5 locations",
    required_capabilities=[AgentCapability.NAVIGATION, AgentCapability.DELIVERY],
    parameters={"locations": [...]}
)
```

### 6. Physical Gateway Service

**File:** `service.py`

Main orchestration service for the gateway.

**Responsibilities:**
- Agent registration and lifecycle management
- Command execution pipeline
- Security and validation orchestration
- Audit logging
- Statistics and health monitoring

**Command Execution Pipeline:**

```
1. Request received
   ↓
2. Agent validation (exists, connected)
   ↓
3. Authorization (session token verification)
   ↓
4. Command validation (safety checks)
   ↓
5. Protocol adapter selection
   ↓
6. Command execution
   ↓
7. Audit logging
   ↓
8. Response returned
```

---

## API Endpoints

### Gateway Info & Status

#### `GET /api/physical-gateway/info`

Get gateway information.

**Response:**
```json
{
  "name": "BRAIN Physical Agents Gateway",
  "version": "1.0.0",
  "description": "Secure gateway for physical agents and IoT devices",
  "status": "operational",
  "connected_agents": 42,
  "total_commands_processed": 15234,
  "uptime_seconds": 86400.0,
  "supported_protocols": ["REST_API", "WEBSOCKET", "MQTT", "ROS2"],
  "security_level": "high",
  "audit_enabled": true
}
```

#### `GET /api/physical-gateway/health`

Get health status.

**Response:**
```json
{
  "healthy": true,
  "components": {
    "security_manager": true,
    "command_validator": true,
    "audit_manager": true,
    "audit_storage": true,
    "mlp_connector": true
  },
  "issues": [],
  "timestamp": "2025-12-23T10:30:45.123456"
}
```

#### `GET /api/physical-gateway/statistics`

Get comprehensive statistics.

**Response:**
```json
{
  "total_agents_registered": 50,
  "agents_online": 42,
  "agents_offline": 8,
  "agents_by_state": {
    "idle": 30,
    "busy": 10,
    "charging": 2
  },
  "total_commands_executed": 15234,
  "commands_successful": 15100,
  "commands_failed": 134,
  "commands_pending": 5,
  "average_command_duration_seconds": 2.3,
  "total_audit_events": 45678,
  "security_violations": 3,
  "uptime_seconds": 86400.0
}
```

### Agent Management

#### `POST /api/physical-gateway/agents/register`

Register a physical agent.

**Request:**
```json
{
  "agent_id": "delivery_bot_001",
  "name": "Delivery Bot Alpha",
  "agent_type": "delivery_robot",
  "capabilities": ["NAVIGATION", "DELIVERY", "OBSTACLE_AVOIDANCE"],
  "protocol": "ROS2",
  "endpoint": "http://192.168.1.100:8080",
  "firmware_version": "2.1.0",
  "hardware_version": "HW-v3",
  "manufacturer": "RobotCorp",
  "model": "DeliveryBot-X100",
  "serial_number": "DB-2024-001",
  "initial_position": {
    "x": 0.0,
    "y": 0.0,
    "z": 0.0,
    "reference_frame": "world"
  }
}
```

**Response:** `201 Created`
```json
{
  "agent_id": "delivery_bot_001",
  "name": "Delivery Bot Alpha",
  "agent_type": "delivery_robot",
  "state": "OFFLINE",
  "capabilities": ["NAVIGATION", "DELIVERY", "OBSTACLE_AVOIDANCE"],
  "protocol": "ROS2",
  "endpoint": "http://192.168.1.100:8080",
  "connected": false,
  "registered_at": "2025-12-23T10:30:45.123456",
  ...
}
```

#### `GET /api/physical-gateway/agents`

List registered agents.

**Query Parameters:**
- `state` (optional): Filter by state (IDLE, BUSY, CHARGING, etc.)

**Response:**
```json
[
  {
    "agent_id": "delivery_bot_001",
    "name": "Delivery Bot Alpha",
    "state": "IDLE",
    "connected": true,
    "battery_percentage": 85.0,
    ...
  },
  ...
]
```

#### `GET /api/physical-gateway/agents/{agent_id}`

Get agent information.

**Response:**
```json
{
  "agent_id": "delivery_bot_001",
  "name": "Delivery Bot Alpha",
  "agent_type": "delivery_robot",
  "state": "IDLE",
  "capabilities": ["NAVIGATION", "DELIVERY"],
  "protocol": "ROS2",
  "connected": true,
  "battery_percentage": 85.0,
  "position": {"x": 10.5, "y": 5.2, "z": 0.0},
  "current_task_id": null,
  "uptime_hours": 24.5,
  "tasks_completed": 142,
  ...
}
```

#### `PUT /api/physical-gateway/agents/{agent_id}/status`

Update agent status.

**Request:**
```json
{
  "state": "BUSY",
  "battery_percentage": 82.0,
  "position": {"x": 12.0, "y": 6.5, "z": 0.0},
  "current_task_id": "TASK-123"
}
```

**Response:**
```json
{
  "agent_id": "delivery_bot_001",
  "state": "BUSY",
  "battery_percentage": 82.0,
  "position": {"x": 12.0, "y": 6.5, "z": 0.0},
  "current_task_id": "TASK-123",
  "last_updated": "2025-12-23T10:35:00.000000",
  ...
}
```

#### `DELETE /api/physical-gateway/agents/{agent_id}`

Unregister agent.

**Response:**
```json
{
  "success": true,
  "message": "Agent delivery_bot_001 unregistered"
}
```

### Authentication

#### `POST /api/physical-gateway/auth/handshake/initiate`

Initiate authentication handshake.

**Request:**
```json
{
  "agent_id": "delivery_bot_001"
}
```

**Response:**
```json
{
  "agent_id": "delivery_bot_001",
  "challenge": "a1b2c3d4e5f6...hex_nonce"
}
```

#### `POST /api/physical-gateway/auth/handshake/complete`

Complete authentication handshake.

**Request:**
```json
{
  "agent_id": "delivery_bot_001",
  "challenge": "a1b2c3d4e5f6...hex_nonce",
  "response": "hmac_sha256_signature",
  "timestamp": "2025-12-23T10:30:45.123456"
}
```

**Response:**
```json
{
  "success": true,
  "session_token": "session_token_here",
  "expires_at": "2025-12-23T11:30:45.123456",
  "error_message": null
}
```

### Command Execution

#### `POST /api/physical-gateway/commands/execute`

Execute command on agent.

**Headers:**
```
Authorization: Bearer <session_token>
```

**Request:**
```json
{
  "agent_id": "delivery_bot_001",
  "command_type": "navigate_to_location",
  "parameters": {
    "target_position": {"x": 20.0, "y": 15.0, "z": 0.0},
    "max_velocity": 1.5,
    "avoid_obstacles": true
  },
  "priority": "NORMAL",
  "timeout_seconds": 300.0
}
```

**Response:**
```json
{
  "command_id": "CMD-delivery_bot_001-1703334645123",
  "agent_id": "delivery_bot_001",
  "status": "COMPLETED",
  "success": true,
  "result": {
    "distance_traveled": 25.3,
    "time_taken": 18.5,
    "obstacles_avoided": 3
  },
  "error_message": null,
  "duration_seconds": 18.7,
  "timestamp": "2025-12-23T10:35:00.000000"
}
```

#### `GET /api/physical-gateway/commands/{command_id}`

Get command status.

**Response:**
```json
{
  "command_id": "CMD-delivery_bot_001-1703334645123",
  "agent_id": "delivery_bot_001",
  "command_type": "navigate_to_location",
  "status": "COMPLETED",
  "priority": "NORMAL",
  "validation_result": {
    "valid": true,
    "errors": [],
    "warnings": [],
    "safety_score": 0.95
  },
  "execution_result": {...},
  "created_at": "2025-12-23T10:30:00.000000",
  "started_at": "2025-12-23T10:30:01.000000",
  "completed_at": "2025-12-23T10:30:19.700000"
}
```

### Audit Trail

#### `POST /api/physical-gateway/audit`

Query audit trail.

**Request:**
```json
{
  "agent_id": "delivery_bot_001",
  "event_type": "command",
  "start_time": "2025-12-23T00:00:00.000000",
  "end_time": "2025-12-23T23:59:59.999999",
  "limit": 100
}
```

**Response:**
```json
[
  {
    "event_id": "EVT-2025-12-23T10:30:00.123456-000001",
    "event_type": "command",
    "action": "command_executed",
    "status": "success",
    "agent_id": "delivery_bot_001",
    "command_id": "CMD-delivery_bot_001-1703334645123",
    "details": {...},
    "timestamp": "2025-12-23T10:30:00.123456"
  },
  ...
]
```

#### `GET /api/physical-gateway/audit/verify`

Verify audit trail integrity.

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "message": "Audit trail integrity verified"
}
```

---

## Security Model

### Challenge-Response Authentication

1. **Agent requests challenge:**
   ```
   POST /auth/handshake/initiate
   ```

2. **Gateway generates nonce:**
   ```
   challenge = random_hex(32)
   ```

3. **Agent computes HMAC:**
   ```
   response = HMAC-SHA256(master_key, agent_id + ":" + challenge)
   ```

4. **Agent sends response:**
   ```
   POST /auth/handshake/complete
   {challenge, response}
   ```

5. **Gateway verifies and issues session token:**
   ```
   if HMAC_matches:
       return session_token (valid 60 minutes)
   ```

### Command Authorization

1. **Session token in Authorization header**
2. **Rate limiting: 100 commands/minute per agent**
3. **Command validation: safety checks, physical constraints**
4. **Audit logging: all commands logged**

### Fail-Closed Design

- **No direct system access**: All commands validated
- **Invalid auth → Reject**
- **Validation fails → Reject**
- **Agent blocked → Reject all commands**
- **Session expired → Re-authenticate required**

---

## Integration Examples

### Example 1: Register and Control Delivery Robot

```python
import httpx

base_url = "http://localhost:8000/api/physical-gateway"

# 1. Register agent
register_response = httpx.post(
    f"{base_url}/agents/register",
    json={
        "agent_id": "delivery_bot_001",
        "name": "Delivery Bot Alpha",
        "agent_type": "delivery_robot",
        "capabilities": ["NAVIGATION", "DELIVERY"],
        "protocol": "ROS2",
        "endpoint": "http://192.168.1.100:8080",
    }
)

# 2. Initiate handshake
challenge_response = httpx.post(
    f"{base_url}/auth/handshake/initiate",
    params={"agent_id": "delivery_bot_001"}
)
challenge = challenge_response.json()["challenge"]

# 3. Complete handshake (agent computes HMAC response)
response = compute_hmac_response("delivery_bot_001", challenge)
handshake_response = httpx.post(
    f"{base_url}/auth/handshake/complete",
    json={
        "agent_id": "delivery_bot_001",
        "challenge": challenge,
        "response": response,
        "timestamp": datetime.utcnow().isoformat()
    }
)
session_token = handshake_response.json()["session_token"]

# 4. Execute command
command_response = httpx.post(
    f"{base_url}/commands/execute",
    headers={"Authorization": f"Bearer {session_token}"},
    json={
        "agent_id": "delivery_bot_001",
        "command_type": "navigate_to_location",
        "parameters": {"target_position": {"x": 20.0, "y": 15.0, "z": 0.0}},
        "priority": "NORMAL",
        "timeout_seconds": 300.0
    }
)

print(command_response.json())
```

### Example 2: IoT Device Integration

```python
from app.modules.physical_gateway.service import get_physical_gateway_service
from app.modules.physical_gateway.schemas import (
    AgentRegisterRequest,
    AgentCapability,
    ProtocolType,
)

service = get_physical_gateway_service()

# Register IoT gateway
await service.register_agent(
    AgentRegisterRequest(
        agent_id="iot_gateway_001",
        name="IoT Gateway Alpha",
        agent_type="iot_gateway",
        capabilities=[
            AgentCapability.SENSING,
            AgentCapability.COMMUNICATION,
        ],
        protocol=ProtocolType.MQTT,
        endpoint="mqtt://192.168.1.50:1883",
    )
)

# Execute sensor read command
response = await service.execute_command(
    CommandRequest(
        agent_id="iot_gateway_001",
        command_type="read_sensor_data",
        parameters={"sensor_ids": ["temp_01", "humidity_01"]},
    ),
    session_token=session_token
)
```

---

## Configuration

### Environment Variables

```bash
# Gateway Configuration
PHYSICAL_GATEWAY_MASTER_KEY=your_secret_key_here
PHYSICAL_GATEWAY_SESSION_TIMEOUT_MINUTES=60
PHYSICAL_GATEWAY_RATE_LIMIT_COMMANDS=100
PHYSICAL_GATEWAY_RATE_LIMIT_WINDOW_SECONDS=60

# MLP/Builder Toolkit
MLP_ENABLED=true
MLP_ENDPOINT=http://mlp.example.com:8100
MLP_API_KEY=your_mlp_api_key
MLP_FEDERATION_MODE=true
MLP_SYNC_INTERVAL_SECONDS=60

# Audit Trail
AUDIT_STORAGE_PATH=storage/audit/physical_gateway_audit.jsonl
```

---

## Agent Blueprints

Located in: `backend/brain/agents/agent_blueprints/`

Available blueprints:
- **IoT Gateway Agent** (`iot_gateway_agent.py`)
- **Industrial Robot Agent** (`industrial_robot_agent.py`)
- **Delivery Robot Agent** (`delivery_robot_agent.py`)
- **Drone Agent** (`drone_agent.py`)
- **Agricultural Robot Agent** (`agricultural_robot_agent.py`)
- **Fleet Coordinator** (`fleet_coordinator.py`)
- **Navigation Planner** (`navigation_planner.py`)
- **Safety Monitor** (`safety_monitor.py`)

---

## Testing

Run tests:

```bash
cd backend
pytest tests/test_physical_gateway.py -v
```

---

## Troubleshooting

### Issue: Agent authentication fails

**Solution:**
- Verify challenge-response computation uses correct HMAC algorithm
- Check that master key matches on both sides
- Ensure challenge hasn't expired (5-minute window)

### Issue: Command validation fails

**Solution:**
- Check agent state (must not be ERROR or EMERGENCY_STOP)
- Verify battery level (>5% required)
- Review command parameters against safety limits
- Check safety score (must be ≥0.5)

### Issue: Audit trail integrity check fails

**Solution:**
- Do not manually edit audit log file
- Check for disk corruption
- Verify file permissions
- Restore from backup if necessary

---

## Future Enhancements

- [ ] gRPC protocol adapter implementation
- [ ] Advanced anomaly detection in command patterns
- [ ] Multi-tenancy support
- [ ] Enhanced MLP federation features
- [ ] Real-time dashboard for gateway monitoring
- [ ] Kubernetes deployment configuration
- [ ] Performance benchmarking suite

---

## License

Copyright © 2025 BRAiN Project. All rights reserved.

---

## Support

For questions or issues, please contact:
- **Technical Support**: support@brain-project.example.com
- **Documentation**: https://docs.brain-project.example.com
- **GitHub Issues**: https://github.com/brain-project/brain/issues
