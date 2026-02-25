"""
Physical Gateway API Router

FastAPI routes for physical agents gateway.

Endpoints:
- GET /api/physical-gateway/info
- GET /api/physical-gateway/health
- GET /api/physical-gateway/statistics

- POST /api/physical-gateway/agents/register
- DELETE /api/physical-gateway/agents/{agent_id}
- GET /api/physical-gateway/agents
- GET /api/physical-gateway/agents/{agent_id}
- PUT /api/physical-gateway/agents/{agent_id}/status

- POST /api/physical-gateway/auth/handshake/initiate
- POST /api/physical-gateway/auth/handshake/complete

- POST /api/physical-gateway/commands/execute
- GET /api/physical-gateway/commands/{command_id}

- GET /api/physical-gateway/audit
- GET /api/physical-gateway/audit/verify
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Header, Depends
from loguru import logger

from app.core.auth_deps import require_auth, get_current_principal, Principal

from .service import get_physical_gateway_service
from .schemas import (
    GatewayInfo,
    PhysicalAgentInfo,
    PhysicalAgentState,
    AgentRegisterRequest,
    AgentUpdateRequest,
    CommandRequest,
    CommandResponse,
    GatewayCommand,
    SecurityHandshake,
    HandshakeResponse,
    AuditQuery,
    AuditEvent,
    GatewayStatistics,
    HealthStatus,
)

# ============================================================================
# Router
# ============================================================================

router = APIRouter(
    prefix="/api/physical-gateway",
    tags=["physical-gateway"],
    dependencies=[Depends(require_auth)]
)


# ============================================================================
# Gateway Info & Status
# ============================================================================


@router.get("/info", response_model=GatewayInfo)
async def get_gateway_info():
    """
    Get physical gateway information.

    Returns gateway system information including version, uptime,
    and connected agents count.
    """
    try:
        service = get_physical_gateway_service()
        return service.get_info()
    except Exception as e:
        logger.error(f"Failed to get gateway info: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health", response_model=HealthStatus)
async def get_gateway_health():
    """
    Get physical gateway health status.

    Returns health status of gateway components.
    """
    try:
        service = get_physical_gateway_service()
        return service.get_health_status()
    except Exception as e:
        logger.error(f"Failed to get gateway health: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/statistics", response_model=GatewayStatistics)
async def get_gateway_statistics():
    """
    Get physical gateway statistics.

    Returns comprehensive statistics about agents, commands,
    and audit trail.
    """
    try:
        service = get_physical_gateway_service()
        return service.get_statistics()
    except Exception as e:
        logger.error(f"Failed to get gateway statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Agent Management
# ============================================================================


@router.post("/agents/register", response_model=PhysicalAgentInfo, status_code=201)
async def register_agent(request: AgentRegisterRequest):
    """
    Register a physical agent.

    Registers a new physical agent with the gateway.
    The agent must complete authentication handshake before
    executing commands.

    Args:
        request: Agent registration request

    Returns:
        Registered agent information

    Raises:
        400: If agent already registered
        500: Internal server error
    """
    try:
        service = get_physical_gateway_service()
        agent = await service.register_agent(request)
        return agent
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/agents/{agent_id}", response_model=dict)
async def unregister_agent(agent_id: str):
    """
    Unregister a physical agent.

    Removes agent from gateway and revokes all sessions.

    Args:
        agent_id: Agent identifier

    Returns:
        Success confirmation

    Raises:
        404: If agent not found
        500: Internal server error
    """
    try:
        service = get_physical_gateway_service()
        success = await service.unregister_agent(agent_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return {"success": True, "message": f"Agent {agent_id} unregistered"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agents", response_model=List[PhysicalAgentInfo])
async def list_agents(state: Optional[PhysicalAgentState] = None):
    """
    List registered physical agents.

    Args:
        state: Optional state filter

    Returns:
        List of registered agents
    """
    try:
        service = get_physical_gateway_service()
        return service.list_agents(state=state)
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/agents/{agent_id}", response_model=PhysicalAgentInfo)
async def get_agent(agent_id: str):
    """
    Get agent information.

    Args:
        agent_id: Agent identifier

    Returns:
        Agent information

    Raises:
        404: If agent not found
    """
    try:
        service = get_physical_gateway_service()
        agent = service.get_agent(agent_id)

        if not agent:
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

        return agent

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/agents/{agent_id}/status", response_model=PhysicalAgentInfo)
async def update_agent_status(agent_id: str, request: AgentUpdateRequest):
    """
    Update agent status.

    Updates agent state, battery level, position, etc.

    Args:
        agent_id: Agent identifier
        request: Update request

    Returns:
        Updated agent information

    Raises:
        404: If agent not found
        500: Internal server error
    """
    try:
        service = get_physical_gateway_service()
        agent = await service.update_agent_status(agent_id, request)
        return agent

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update agent status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Authentication
# ============================================================================


@router.post("/auth/handshake/initiate", response_model=dict)
async def initiate_handshake(agent_id: str):
    """
    Initiate security handshake.

    Generates challenge nonce for agent authentication.

    Args:
        agent_id: Agent identifier

    Returns:
        Challenge nonce
    """
    try:
        service = get_physical_gateway_service()
        challenge = service.initiate_handshake(agent_id)
        return {"agent_id": agent_id, "challenge": challenge}

    except Exception as e:
        logger.error(f"Failed to initiate handshake: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auth/handshake/complete", response_model=HandshakeResponse)
async def complete_handshake(handshake: SecurityHandshake):
    """
    Complete security handshake.

    Verifies challenge response and issues session token.

    Args:
        handshake: Handshake request with signed response

    Returns:
        Handshake response with session token
    """
    try:
        service = get_physical_gateway_service()
        response = service.complete_handshake(handshake)
        return response

    except Exception as e:
        logger.error(f"Failed to complete handshake: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Command Execution
# ============================================================================


@router.post("/commands/execute", response_model=CommandResponse)
async def execute_command(
    request: CommandRequest,
    authorization: Optional[str] = Header(None),
):
    """
    Execute command on physical agent.

    Validates, authorizes, and executes command on target agent.

    Security:
    - Requires valid session token in Authorization header
    - Command is validated for safety
    - All commands are logged in audit trail

    Args:
        request: Command execution request
        authorization: Session token (format: "Bearer <token>")

    Returns:
        Command execution response

    Raises:
        400: Invalid request
        401: Unauthorized
        500: Internal server error
    """
    try:
        # Extract session token
        session_token = None
        if authorization and authorization.startswith("Bearer "):
            session_token = authorization[7:]  # Remove "Bearer " prefix

        service = get_physical_gateway_service()
        response = await service.execute_command(request, session_token)
        return response

    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/commands/{command_id}", response_model=GatewayCommand)
async def get_command_status(command_id: str):
    """
    Get command status.

    Args:
        command_id: Command identifier

    Returns:
        Command information and status

    Raises:
        404: If command not found
    """
    try:
        service = get_physical_gateway_service()
        command = service.get_command_status(command_id)

        if not command:
            raise HTTPException(
                status_code=404, detail=f"Command {command_id} not found"
            )

        return command

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get command status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Audit Trail
# ============================================================================


@router.post("/audit", response_model=List[AuditEvent])
async def query_audit_trail(query: AuditQuery):
    """
    Query audit trail.

    Queries audit trail with optional filters.

    Args:
        query: Audit query parameters

    Returns:
        List of matching audit events
    """
    try:
        service = get_physical_gateway_service()
        events = service.query_audit_trail(query)
        return events

    except Exception as e:
        logger.error(f"Failed to query audit trail: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/audit/verify", response_model=dict)
async def verify_audit_integrity():
    """
    Verify audit trail integrity.

    Verifies hash chain integrity of audit trail.

    Returns:
        Verification result with any errors found
    """
    try:
        service = get_physical_gateway_service()
        is_valid, errors = service.verify_audit_integrity()

        return {
            "valid": is_valid,
            "errors": errors,
            "message": "Audit trail integrity verified" if is_valid else "Integrity check failed",
        }

    except Exception as e:
        logger.error(f"Failed to verify audit integrity: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Utility Endpoints
# ============================================================================


@router.get("/protocols", response_model=List[str])
async def list_supported_protocols():
    """
    List supported communication protocols.

    Returns:
        List of protocol names
    """
    return [
        "REST_API",
        "WEBSOCKET",
        "MQTT",
        "ROS2",
        "GRPC",
        "MODBUS",
        "OPCUA",
    ]
