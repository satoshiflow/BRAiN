"""
Physical Gateway Tests

Tests for physical agents gateway module.
"""

import sys
import os

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient
from backend.main import app

from app.modules.physical_gateway.schemas import (
    AgentCapability,
    ProtocolType,
    CommandPriority,
    PhysicalAgentState,
)

client = TestClient(app)

# ============================================================================
# Gateway Info Tests
# ============================================================================


def test_get_gateway_info():
    """Test gateway info endpoint."""
    response = client.get("/api/physical-gateway/info")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "BRAIN Physical Agents Gateway"
    assert data["version"] == "1.0.0"
    assert "uptime_seconds" in data
    assert isinstance(data["connected_agents"], int)
    assert data["security_level"] == "high"
    assert data["audit_enabled"] is True


def test_get_gateway_health():
    """Test gateway health endpoint."""
    response = client.get("/api/physical-gateway/health")

    assert response.status_code == 200
    data = response.json()

    assert "healthy" in data
    assert "components" in data
    assert data["components"]["security_manager"] is True
    assert data["components"]["command_validator"] is True


def test_get_gateway_statistics():
    """Test gateway statistics endpoint."""
    response = client.get("/api/physical-gateway/statistics")

    assert response.status_code == 200
    data = response.json()

    assert "total_agents_registered" in data
    assert "total_commands_executed" in data
    assert "agents_online" in data
    assert "uptime_seconds" in data


# ============================================================================
# Agent Management Tests
# ============================================================================


def test_register_agent():
    """Test agent registration."""
    payload = {
        "agent_id": "test_robot_001",
        "name": "Test Robot Alpha",
        "agent_type": "delivery_robot",
        "capabilities": ["NAVIGATION", "DELIVERY"],
        "protocol": "REST_API",
        "endpoint": "http://localhost:9000",
        "firmware_version": "1.0.0",
        "manufacturer": "TestCorp",
        "model": "TR-100",
    }

    response = client.post("/api/physical-gateway/agents/register", json=payload)

    assert response.status_code == 201
    data = response.json()

    assert data["agent_id"] == "test_robot_001"
    assert data["name"] == "Test Robot Alpha"
    assert data["state"] == "OFFLINE"
    assert data["connected"] is False
    assert "registered_at" in data


def test_register_duplicate_agent():
    """Test registering duplicate agent fails."""
    payload = {
        "agent_id": "test_robot_001",
        "name": "Test Robot Alpha",
        "agent_type": "delivery_robot",
        "capabilities": ["NAVIGATION"],
        "protocol": "REST_API",
        "endpoint": "http://localhost:9000",
    }

    # First registration should succeed
    response1 = client.post("/api/physical-gateway/agents/register", json=payload)
    assert response1.status_code == 201

    # Duplicate should fail
    response2 = client.post("/api/physical-gateway/agents/register", json=payload)
    assert response2.status_code == 400


def test_list_agents():
    """Test listing agents."""
    # Register test agent
    payload = {
        "agent_id": "test_robot_002",
        "name": "Test Robot Beta",
        "agent_type": "drone",
        "capabilities": ["NAVIGATION"],
        "protocol": "ROS2",
        "endpoint": "http://localhost:9001",
    }
    client.post("/api/physical-gateway/agents/register", json=payload)

    # List all agents
    response = client.get("/api/physical-gateway/agents")

    assert response.status_code == 200
    agents = response.json()

    assert isinstance(agents, list)
    assert len(agents) > 0

    # Check if our test agent is in the list
    agent_ids = [a["agent_id"] for a in agents]
    assert "test_robot_002" in agent_ids


def test_get_agent():
    """Test getting agent information."""
    # Register test agent
    agent_id = "test_robot_003"
    payload = {
        "agent_id": agent_id,
        "name": "Test Robot Gamma",
        "agent_type": "industrial_robot",
        "capabilities": ["MANIPULATION"],
        "protocol": "MODBUS",
        "endpoint": "http://localhost:9002",
    }
    client.post("/api/physical-gateway/agents/register", json=payload)

    # Get agent
    response = client.get(f"/api/physical-gateway/agents/{agent_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["agent_id"] == agent_id
    assert data["name"] == "Test Robot Gamma"
    assert data["agent_type"] == "industrial_robot"


def test_get_nonexistent_agent():
    """Test getting nonexistent agent returns 404."""
    response = client.get("/api/physical-gateway/agents/nonexistent_agent")

    assert response.status_code == 404


def test_update_agent_status():
    """Test updating agent status."""
    # Register test agent
    agent_id = "test_robot_004"
    payload = {
        "agent_id": agent_id,
        "name": "Test Robot Delta",
        "agent_type": "delivery_robot",
        "capabilities": ["NAVIGATION"],
        "protocol": "REST_API",
        "endpoint": "http://localhost:9003",
    }
    client.post("/api/physical-gateway/agents/register", json=payload)

    # Update status
    update_payload = {
        "state": "IDLE",
        "battery_percentage": 85.0,
        "position": {"x": 10.0, "y": 5.0, "z": 0.0},
    }

    response = client.put(
        f"/api/physical-gateway/agents/{agent_id}/status", json=update_payload
    )

    assert response.status_code == 200
    data = response.json()

    assert data["state"] == "IDLE"
    assert data["battery_percentage"] == 85.0
    assert data["position"]["x"] == 10.0


def test_unregister_agent():
    """Test unregistering agent."""
    # Register test agent
    agent_id = "test_robot_005"
    payload = {
        "agent_id": agent_id,
        "name": "Test Robot Epsilon",
        "agent_type": "drone",
        "capabilities": ["NAVIGATION"],
        "protocol": "WEBSOCKET",
        "endpoint": "ws://localhost:9004",
    }
    client.post("/api/physical-gateway/agents/register", json=payload)

    # Unregister
    response = client.delete(f"/api/physical-gateway/agents/{agent_id}")

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True

    # Verify agent is gone
    get_response = client.get(f"/api/physical-gateway/agents/{agent_id}")
    assert get_response.status_code == 404


# ============================================================================
# Authentication Tests
# ============================================================================


def test_initiate_handshake():
    """Test initiating authentication handshake."""
    # Register test agent
    agent_id = "test_robot_006"
    payload = {
        "agent_id": agent_id,
        "name": "Test Robot Zeta",
        "agent_type": "iot_gateway",
        "capabilities": ["SENSING"],
        "protocol": "MQTT",
        "endpoint": "mqtt://localhost:1883",
    }
    client.post("/api/physical-gateway/agents/register", json=payload)

    # Initiate handshake
    response = client.post(
        "/api/physical-gateway/auth/handshake/initiate", params={"agent_id": agent_id}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["agent_id"] == agent_id
    assert "challenge" in data
    assert len(data["challenge"]) == 64  # 32 bytes in hex = 64 characters


# ============================================================================
# Command Execution Tests
# ============================================================================


def test_execute_command_without_auth():
    """Test executing command without authentication fails."""
    # Register test agent
    agent_id = "test_robot_007"
    payload = {
        "agent_id": agent_id,
        "name": "Test Robot Eta",
        "agent_type": "delivery_robot",
        "capabilities": ["NAVIGATION"],
        "protocol": "REST_API",
        "endpoint": "http://localhost:9005",
    }
    client.post("/api/physical-gateway/agents/register", json=payload)

    # Try to execute command without session token
    command_payload = {
        "agent_id": agent_id,
        "command_type": "navigate_to_location",
        "parameters": {"target_position": {"x": 10.0, "y": 5.0, "z": 0.0}},
        "priority": "NORMAL",
        "timeout_seconds": 300.0,
    }

    response = client.post(
        "/api/physical-gateway/commands/execute", json=command_payload
    )

    assert response.status_code == 200  # Request accepted
    data = response.json()

    # But command should be rejected due to missing auth
    assert data["success"] is False
    assert "token" in data["error_message"].lower() or "session" in data["error_message"].lower()


# ============================================================================
# Audit Trail Tests
# ============================================================================


def test_query_audit_trail():
    """Test querying audit trail."""
    query_payload = {
        "limit": 10,
    }

    response = client.post("/api/physical-gateway/audit", json=query_payload)

    assert response.status_code == 200
    events = response.json()

    assert isinstance(events, list)
    # Events should exist from previous test operations


def test_verify_audit_integrity():
    """Test audit trail integrity verification."""
    response = client.get("/api/physical-gateway/audit/verify")

    assert response.status_code == 200
    data = response.json()

    assert "valid" in data
    assert data["valid"] is True
    assert "errors" in data
    assert len(data["errors"]) == 0


# ============================================================================
# Utility Tests
# ============================================================================


def test_list_supported_protocols():
    """Test listing supported protocols."""
    response = client.get("/api/physical-gateway/protocols")

    assert response.status_code == 200
    protocols = response.json()

    assert isinstance(protocols, list)
    assert "REST_API" in protocols
    assert "WEBSOCKET" in protocols
    assert "MQTT" in protocols
    assert "ROS2" in protocols


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_agent_lifecycle():
    """Test complete agent lifecycle."""
    agent_id = "lifecycle_test_robot"

    # 1. Register
    register_payload = {
        "agent_id": agent_id,
        "name": "Lifecycle Test Robot",
        "agent_type": "test_robot",
        "capabilities": ["NAVIGATION", "SENSING"],
        "protocol": "REST_API",
        "endpoint": "http://localhost:9999",
    }

    register_response = client.post(
        "/api/physical-gateway/agents/register", json=register_payload
    )
    assert register_response.status_code == 201

    # 2. Get agent
    get_response = client.get(f"/api/physical-gateway/agents/{agent_id}")
    assert get_response.status_code == 200

    # 3. Update status
    update_payload = {
        "state": "IDLE",
        "battery_percentage": 95.0,
    }
    update_response = client.put(
        f"/api/physical-gateway/agents/{agent_id}/status", json=update_payload
    )
    assert update_response.status_code == 200

    # 4. Initiate handshake
    handshake_init_response = client.post(
        "/api/physical-gateway/auth/handshake/initiate", params={"agent_id": agent_id}
    )
    assert handshake_init_response.status_code == 200

    # 5. Query audit trail for this agent
    audit_payload = {"agent_id": agent_id, "limit": 100}
    audit_response = client.post("/api/physical-gateway/audit", json=audit_payload)
    assert audit_response.status_code == 200
    events = audit_response.json()
    assert len(events) > 0  # Should have registration, status update, handshake events

    # 6. Unregister
    delete_response = client.delete(f"/api/physical-gateway/agents/{agent_id}")
    assert delete_response.status_code == 200

    # 7. Verify agent is gone
    get_after_delete = client.get(f"/api/physical-gateway/agents/{agent_id}")
    assert get_after_delete.status_code == 404
