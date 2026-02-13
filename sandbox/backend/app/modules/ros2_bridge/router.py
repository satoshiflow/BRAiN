"""
ROS2 Bridge Router

REST API endpoints for ROS2 communication.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.modules.ros2_bridge.schemas import (
    TopicInfo,
    TopicSubscribeRequest,
    TopicPublishRequest,
    ServiceInfo,
    ServiceCallRequest,
    ServiceCallResponse,
    ActionInfo,
    ActionGoalRequest,
    ActionGoalResponse,
    ActionResult,
    Parameter,
    ParameterGetRequest,
    ParameterSetRequest,
    NodeInfo,
    NodeListResponse,
    BridgeInfo,
    BridgeStatus,
)
from app.modules.ros2_bridge.bridge import get_ros2_bridge

router = APIRouter(prefix="/api/ros2", tags=["ROS2 Bridge"])


# ============================================================================
# BRIDGE MANAGEMENT
# ============================================================================

@router.get("/info", response_model=BridgeInfo)
async def get_bridge_info():
    """Get ROS2 bridge module information and status."""
    bridge = get_ros2_bridge()

    # Auto-connect if not connected
    if not bridge.is_connected():
        await bridge.connect()

    return BridgeInfo(
        name="ROS2 Bridge",
        version="1.0.0",
        description="ROS2 integration bridge for BRAiN robot control",
        status=bridge.get_status(),
        features=[
            "Topic publishing and subscription",
            "Service calls",
            "Action goal management",
            "Parameter get/set",
            "Node discovery",
            "Mock mode for development",
        ],
    )


@router.get("/status", response_model=BridgeStatus)
async def get_bridge_status():
    """Get current ROS2 bridge status."""
    bridge = get_ros2_bridge()
    return bridge.get_status()


@router.post("/connect", status_code=status.HTTP_200_OK)
async def connect_bridge():
    """Connect to ROS2 network."""
    bridge = get_ros2_bridge()

    if bridge.is_connected():
        return {"message": "Already connected", "connected": True}

    success = await bridge.connect()

    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to ROS2 network",
        )

    return {"message": "Connected successfully", "connected": True}


@router.post("/disconnect", status_code=status.HTTP_200_OK)
async def disconnect_bridge():
    """Disconnect from ROS2 network."""
    bridge = get_ros2_bridge()
    await bridge.disconnect()
    return {"message": "Disconnected successfully", "connected": False}


# ============================================================================
# TOPIC OPERATIONS
# ============================================================================

@router.get("/topics", response_model=List[TopicInfo])
async def list_topics():
    """List all available ROS2 topics."""
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    return bridge.list_topics()


@router.post("/topics/subscribe", status_code=status.HTTP_201_CREATED)
async def subscribe_topic(request: TopicSubscribeRequest):
    """
    Subscribe to a ROS2 topic.

    Messages will be cached and can be retrieved via GET /topics/{topic_name}/messages
    """
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    try:
        success = await bridge.subscribe_topic(request)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to subscribe to topic: {request.topic_name}",
            )

        return {
            "message": f"Subscribed to {request.topic_name}",
            "topic_name": request.topic_name,
            "msg_type": request.msg_type,
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.delete("/topics/{topic_name}/subscription", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_topic(topic_name: str):
    """Unsubscribe from a ROS2 topic."""
    bridge = get_ros2_bridge()

    success = await bridge.unsubscribe_topic(topic_name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Not subscribed to topic: {topic_name}",
        )


@router.post("/topics/publish", status_code=status.HTTP_200_OK)
async def publish_message(request: TopicPublishRequest):
    """Publish a message to a ROS2 topic."""
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    try:
        success = await bridge.publish_message(request)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to publish message",
            )

        return {
            "message": "Message published successfully",
            "topic_name": request.topic_name,
        }

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


# ============================================================================
# SERVICE OPERATIONS
# ============================================================================

@router.get("/services", response_model=List[ServiceInfo])
async def list_services():
    """List all available ROS2 services."""
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    return bridge.list_services()


@router.post("/services/call", response_model=ServiceCallResponse)
async def call_service(request: ServiceCallRequest):
    """
    Call a ROS2 service.

    The service will be called synchronously with the specified timeout.
    """
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    try:
        response = await bridge.call_service(request)
        return response

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


# ============================================================================
# ACTION OPERATIONS
# ============================================================================

@router.get("/actions", response_model=List[ActionInfo])
async def list_actions():
    """List all available ROS2 actions."""
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    return bridge.list_actions()


@router.post("/actions/send_goal", response_model=ActionGoalResponse)
async def send_action_goal(request: ActionGoalRequest):
    """
    Send an action goal to ROS2.

    Returns a goal ID that can be used to:
    - Query goal status
    - Cancel the goal
    - Get final result
    """
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    try:
        response = await bridge.send_action_goal(request)
        return response

    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.post("/actions/{goal_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_action_goal(goal_id: str):
    """Cancel an action goal."""
    bridge = get_ros2_bridge()

    success = await bridge.cancel_action_goal(goal_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action goal not found: {goal_id}",
        )

    return {"message": f"Action goal {goal_id} canceled"}


@router.get("/actions/{goal_id}/result", response_model=ActionResult)
async def get_action_result(goal_id: str):
    """Get the result of an action goal."""
    bridge = get_ros2_bridge()

    result = bridge.get_action_result(goal_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action goal not found: {goal_id}",
        )

    return result


# ============================================================================
# PARAMETER OPERATIONS
# ============================================================================

@router.post("/parameters/get", response_model=Parameter)
async def get_parameter(request: ParameterGetRequest):
    """Get a ROS2 parameter value."""
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    param = await bridge.get_parameter(request)

    if param is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Parameter not found: {request.node_name}:{request.parameter_name}",
        )

    return param


@router.post("/parameters/set", status_code=status.HTTP_200_OK)
async def set_parameter(request: ParameterSetRequest):
    """Set a ROS2 parameter value."""
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    success = await bridge.set_parameter(request)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set parameter",
        )

    return {
        "message": "Parameter set successfully",
        "node_name": request.node_name,
        "parameter_name": request.parameter.name,
    }


# ============================================================================
# NODE DISCOVERY
# ============================================================================

@router.get("/nodes", response_model=NodeListResponse)
async def list_nodes():
    """List all discovered ROS2 nodes."""
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    nodes = bridge.list_nodes()

    return NodeListResponse(
        total=len(nodes),
        nodes=nodes,
    )


@router.get("/nodes/{node_name}", response_model=NodeInfo)
async def get_node_info(node_name: str):
    """Get information about a specific ROS2 node."""
    bridge = get_ros2_bridge()

    if not bridge.is_connected():
        await bridge.connect()

    nodes = bridge.list_nodes()
    node = next((n for n in nodes if n.name == node_name), None)

    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found: {node_name}",
        )

    return node
