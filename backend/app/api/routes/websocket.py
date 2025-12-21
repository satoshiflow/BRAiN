"""
WebSocket API Routes

WebSocket endpoints for real-time communication.

Endpoints:
    WS /ws/connect        - Main WebSocket connection
    WS /ws/channel/{name} - Channel-specific connection
    POST /api/ws/broadcast - Broadcast message to channel
    GET /api/ws/stats     - WebSocket statistics

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from loguru import logger
from pydantic import BaseModel, Field

from backend.app.core.security import Principal, get_current_principal_optional, require_admin
from backend.app.core.websocket import get_websocket_manager

router = APIRouter(tags=["websocket"])


# ============================================================================
# Request/Response Models
# ============================================================================

class BroadcastRequest(BaseModel):
    """Broadcast message request."""

    channel: str = Field(..., description="Target channel")
    message: Dict[str, Any] = Field(..., description="Message to broadcast")
    type: str = Field(default="broadcast", description="Message type")


class WebSocketStatsResponse(BaseModel):
    """WebSocket statistics response."""

    total_connections: int = Field(..., description="Total active connections")
    total_users: int = Field(..., description="Total unique users")
    total_channels: int = Field(..., description="Total active channels")
    channels: Dict[str, int] = Field(..., description="Subscribers per channel")


class ChannelSubscribersResponse(BaseModel):
    """Channel subscribers response."""

    channel: str = Field(..., description="Channel name")
    subscribers: int = Field(..., description="Number of subscribers")
    connection_ids: List[str] = Field(..., description="Connection IDs")


# ============================================================================
# WebSocket Endpoints
# ============================================================================

@router.websocket("/ws/connect")
async def websocket_connect(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Authentication token"),
):
    """
    Main WebSocket connection endpoint.

    **Authentication:** Optional (via query parameter)

    **Protocol:**
    1. Client connects
    2. Server sends welcome message
    3. Client can send commands:
       - `{"type": "subscribe", "channel": "channel_name"}`
       - `{"type": "unsubscribe", "channel": "channel_name"}`
       - `{"type": "pong"}` (response to ping)
    4. Server broadcasts messages to subscribed channels

    **Example:**
    ```javascript
    const ws = new WebSocket("ws://localhost:8000/ws/connect?token=xxx");

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Received:", data);

        if (data.type === "ping") {
            ws.send(JSON.stringify({type: "pong"}));
        }
    };

    // Subscribe to channel
    ws.send(JSON.stringify({
        type: "subscribe",
        channel: "missions"
    }));
    ```
    """
    manager = get_websocket_manager()

    # Generate connection ID
    connection_id = str(uuid.uuid4())

    # Optional: Authenticate user
    user_id = None
    # TODO: Extract user_id from token if provided

    try:
        # Accept connection
        await manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
        )

        # Message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "subscribe":
                # Subscribe to channel
                channel = data.get("channel")
                if channel:
                    await manager.subscribe(connection_id, channel)

            elif message_type == "unsubscribe":
                # Unsubscribe from channel
                channel = data.get("channel")
                if channel:
                    await manager.unsubscribe(connection_id, channel)

            elif message_type == "pong":
                # Handle pong response
                await manager.handle_pong(connection_id)

            else:
                # Unknown message type
                logger.warning(f"Unknown message type: {message_type}")

    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(connection_id)


@router.websocket("/ws/channel/{channel}")
async def websocket_channel(
    websocket: WebSocket,
    channel: str,
    token: Optional[str] = Query(None, description="Authentication token"),
):
    """
    Channel-specific WebSocket connection.

    Automatically subscribes to specified channel on connection.

    **Authentication:** Optional (via query parameter)

    **Example:**
    ```javascript
    const ws = new WebSocket("ws://localhost:8000/ws/channel/missions?token=xxx");
    ```
    """
    manager = get_websocket_manager()

    # Generate connection ID
    connection_id = str(uuid.uuid4())

    # Optional: Authenticate user
    user_id = None
    # TODO: Extract user_id from token if provided

    try:
        # Accept connection
        await manager.connect(
            websocket=websocket,
            connection_id=connection_id,
            user_id=user_id,
        )

        # Auto-subscribe to channel
        await manager.subscribe(connection_id, channel)

        # Message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            message_type = data.get("type")

            if message_type == "pong":
                await manager.handle_pong(connection_id)
            else:
                logger.debug(f"Received from {connection_id}: {data}")

    except WebSocketDisconnect:
        await manager.disconnect(connection_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(connection_id)


# ============================================================================
# HTTP API Endpoints
# ============================================================================

@router.post("/api/ws/broadcast", status_code=status.HTTP_202_ACCEPTED)
async def broadcast_message(
    request: BroadcastRequest,
    principal: Principal = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Broadcast message to WebSocket channel.

    **Permissions:** Admin only

    **Args:**
    - channel: Target channel name
    - message: Message payload
    - type: Message type (default: "broadcast")

    **Returns:**
    - Broadcast confirmation with subscriber count

    **Example:**
    ```json
    {
        "channel": "missions",
        "message": {
            "mission_id": "mission_123",
            "status": "completed"
        },
        "type": "mission_update"
    }
    ```
    """
    manager = get_websocket_manager()

    # Build message
    full_message = {
        "type": request.type,
        "data": request.message,
    }

    # Broadcast to channel
    await manager.broadcast_to_channel(request.channel, full_message)

    # Get subscriber count
    subscribers = manager.get_channel_subscribers(request.channel)

    return {
        "status": "broadcasted",
        "channel": request.channel,
        "subscribers": len(subscribers),
    }


@router.post("/api/ws/broadcast/all", status_code=status.HTTP_202_ACCEPTED)
async def broadcast_all(
    message: Dict[str, Any],
    principal: Principal = Depends(require_admin),
) -> Dict[str, Any]:
    """
    Broadcast message to all active WebSocket connections.

    **Permissions:** Admin only

    **Args:**
    - message: Message to broadcast

    **Returns:**
    - Broadcast confirmation with total connections

    **Example:**
    ```json
    {
        "type": "system_announcement",
        "data": {
            "message": "System maintenance in 5 minutes"
        }
    }
    ```
    """
    manager = get_websocket_manager()

    await manager.broadcast_all(message)

    stats = manager.get_stats()

    return {
        "status": "broadcasted",
        "total_connections": stats["total_connections"],
    }


@router.get("/api/ws/stats", response_model=WebSocketStatsResponse)
async def get_websocket_stats(
    principal: Principal = Depends(require_admin),
) -> WebSocketStatsResponse:
    """
    Get WebSocket connection statistics.

    **Permissions:** Admin only

    **Returns:**
    - Connection statistics including channel subscriber counts
    """
    manager = get_websocket_manager()
    stats = manager.get_stats()

    return WebSocketStatsResponse(
        total_connections=stats["total_connections"],
        total_users=stats["total_users"],
        total_channels=stats["total_channels"],
        channels=stats["channels"],
    )


@router.get("/api/ws/channels/{channel}", response_model=ChannelSubscribersResponse)
async def get_channel_subscribers(
    channel: str,
    principal: Principal = Depends(require_admin),
) -> ChannelSubscribersResponse:
    """
    Get subscribers for a specific channel.

    **Permissions:** Admin only

    **Args:**
    - channel: Channel name

    **Returns:**
    - Channel subscriber information
    """
    manager = get_websocket_manager()
    subscribers = manager.get_channel_subscribers(channel)

    return ChannelSubscribersResponse(
        channel=channel,
        subscribers=len(subscribers),
        connection_ids=subscribers,
    )


@router.get("/api/ws/info")
async def get_websocket_info() -> Dict[str, Any]:
    """
    Get WebSocket system information.

    **Returns:**
    - WebSocket configuration and capabilities
    """
    return {
        "name": "BRAiN WebSocket System",
        "version": "1.0.0",
        "features": [
            "Real-time messaging",
            "Channel subscriptions",
            "User-based messaging",
            "Broadcast messaging",
            "Heartbeat/keepalive",
            "Connection pooling",
        ],
        "endpoints": {
            "connect": "ws://localhost:8000/ws/connect",
            "channel": "ws://localhost:8000/ws/channel/{channel}",
        },
        "heartbeat_interval": 30,  # seconds
    }


# ============================================================================
# Exports
# ============================================================================

__all__ = ["router"]
