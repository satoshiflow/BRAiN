"""
WebSocket Connection Manager

Enhanced WebSocket management with:
- Connection pooling
- Room/channel subscriptions
- Message broadcasting
- Authentication
- Heartbeat/keepalive
- Connection state tracking

Created: 2025-12-20
Phase: 5 - Developer Experience & Advanced Features
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel, Field


# ============================================================================
# WebSocket Models
# ============================================================================

class WebSocketMessage(BaseModel):
    """WebSocket message structure."""

    type: str = Field(..., description="Message type")
    channel: Optional[str] = Field(None, description="Target channel")
    data: Dict[str, Any] = Field(default={}, description="Message payload")
    timestamp: float = Field(default_factory=time.time, description="Message timestamp")


class ConnectionInfo(BaseModel):
    """WebSocket connection information."""

    connection_id: str = Field(..., description="Unique connection ID")
    user_id: Optional[str] = Field(None, description="Authenticated user ID")
    channels: Set[str] = Field(default_factory=set, description="Subscribed channels")
    connected_at: float = Field(default_factory=time.time, description="Connection timestamp")
    last_ping: float = Field(default_factory=time.time, description="Last ping timestamp")
    metadata: Dict[str, Any] = Field(default={}, description="Custom metadata")


# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class WebSocketManager:
    """
    WebSocket connection manager with channel support.

    Features:
    - Connection pooling
    - Channel subscriptions (pub/sub)
    - Broadcast messaging
    - User-based messaging
    - Connection tracking
    - Heartbeat monitoring
    """

    def __init__(self):
        # Active connections: {connection_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}

        # Connection info: {connection_id: ConnectionInfo}
        self.connection_info: Dict[str, ConnectionInfo] = {}

        # Channel subscriptions: {channel: {connection_ids}}
        self.channels: Dict[str, Set[str]] = {}

        # User connections: {user_id: {connection_ids}}
        self.user_connections: Dict[str, Set[str]] = {}

        # Heartbeat task
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.heartbeat_interval = 30.0  # 30 seconds

    # ========================================================================
    # Connection Management
    # ========================================================================

    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Accept and register WebSocket connection.

        Args:
            websocket: WebSocket instance
            connection_id: Unique connection identifier
            user_id: Optional authenticated user ID
            metadata: Optional connection metadata
        """
        await websocket.accept()

        self.active_connections[connection_id] = websocket
        self.connection_info[connection_id] = ConnectionInfo(
            connection_id=connection_id,
            user_id=user_id,
            metadata=metadata or {},
        )

        # Track user connections
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

        logger.info(f"WebSocket connected: {connection_id} (user: {user_id})")

        # Send welcome message
        await self.send_personal(
            connection_id,
            {
                "type": "connected",
                "connection_id": connection_id,
                "timestamp": time.time(),
            },
        )

        # Start heartbeat task if not running
        if not self.heartbeat_task or self.heartbeat_task.done():
            self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def disconnect(self, connection_id: str):
        """
        Disconnect and cleanup WebSocket connection.

        Args:
            connection_id: Connection to disconnect
        """
        if connection_id not in self.active_connections:
            return

        # Get connection info
        info = self.connection_info.get(connection_id)

        # Unsubscribe from all channels
        if info:
            for channel in list(info.channels):
                await self.unsubscribe(connection_id, channel)

            # Remove from user connections
            if info.user_id and info.user_id in self.user_connections:
                self.user_connections[info.user_id].discard(connection_id)
                if not self.user_connections[info.user_id]:
                    del self.user_connections[info.user_id]

        # Remove connection
        del self.active_connections[connection_id]
        if connection_id in self.connection_info:
            del self.connection_info[connection_id]

        logger.info(f"WebSocket disconnected: {connection_id}")

    # ========================================================================
    # Channel Management
    # ========================================================================

    async def subscribe(self, connection_id: str, channel: str):
        """
        Subscribe connection to channel.

        Args:
            connection_id: Connection to subscribe
            channel: Channel name
        """
        if connection_id not in self.active_connections:
            return

        # Add to channel
        if channel not in self.channels:
            self.channels[channel] = set()
        self.channels[channel].add(connection_id)

        # Update connection info
        if connection_id in self.connection_info:
            self.connection_info[connection_id].channels.add(channel)

        logger.info(f"Connection {connection_id} subscribed to channel: {channel}")

        # Send subscription confirmation
        await self.send_personal(
            connection_id,
            {
                "type": "subscribed",
                "channel": channel,
                "timestamp": time.time(),
            },
        )

    async def unsubscribe(self, connection_id: str, channel: str):
        """
        Unsubscribe connection from channel.

        Args:
            connection_id: Connection to unsubscribe
            channel: Channel name
        """
        if channel in self.channels:
            self.channels[channel].discard(connection_id)
            if not self.channels[channel]:
                del self.channels[channel]

        # Update connection info
        if connection_id in self.connection_info:
            self.connection_info[connection_id].channels.discard(channel)

        logger.info(f"Connection {connection_id} unsubscribed from channel: {channel}")

        # Send unsubscription confirmation
        await self.send_personal(
            connection_id,
            {
                "type": "unsubscribed",
                "channel": channel,
                "timestamp": time.time(),
            },
        )

    # ========================================================================
    # Message Sending
    # ========================================================================

    async def send_personal(self, connection_id: str, message: Dict[str, Any]):
        """
        Send message to specific connection.

        Args:
            connection_id: Target connection
            message: Message to send
        """
        if connection_id not in self.active_connections:
            return

        websocket = self.active_connections[connection_id]

        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to {connection_id}: {e}")
            await self.disconnect(connection_id)

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """
        Send message to all connections of a user.

        Args:
            user_id: Target user ID
            message: Message to send
        """
        if user_id not in self.user_connections:
            return

        connection_ids = list(self.user_connections[user_id])

        for connection_id in connection_ids:
            await self.send_personal(connection_id, message)

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]):
        """
        Broadcast message to all subscribers of a channel.

        Args:
            channel: Target channel
            message: Message to broadcast
        """
        if channel not in self.channels:
            return

        connection_ids = list(self.channels[channel])

        logger.info(f"Broadcasting to channel {channel}: {len(connection_ids)} connections")

        # Add channel to message
        message["channel"] = channel

        for connection_id in connection_ids:
            await self.send_personal(connection_id, message)

    async def broadcast_all(self, message: Dict[str, Any]):
        """
        Broadcast message to all active connections.

        Args:
            message: Message to broadcast
        """
        connection_ids = list(self.active_connections.keys())

        logger.info(f"Broadcasting to all: {len(connection_ids)} connections")

        for connection_id in connection_ids:
            await self.send_personal(connection_id, message)

    # ========================================================================
    # Connection State
    # ========================================================================

    def get_connection_info(self, connection_id: str) -> Optional[ConnectionInfo]:
        """Get connection information."""
        return self.connection_info.get(connection_id)

    def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a user."""
        return list(self.user_connections.get(user_id, set()))

    def get_channel_subscribers(self, channel: str) -> List[str]:
        """Get all connection IDs subscribed to a channel."""
        return list(self.channels.get(channel, set()))

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "total_users": len(self.user_connections),
            "total_channels": len(self.channels),
            "channels": {
                channel: len(subscribers)
                for channel, subscribers in self.channels.items()
            },
        }

    # ========================================================================
    # Heartbeat
    # ========================================================================

    async def _heartbeat_loop(self):
        """Background task to send heartbeat pings."""
        logger.info("WebSocket heartbeat started")

        while self.active_connections:
            await asyncio.sleep(self.heartbeat_interval)

            connection_ids = list(self.active_connections.keys())

            for connection_id in connection_ids:
                try:
                    await self.send_personal(
                        connection_id,
                        {
                            "type": "ping",
                            "timestamp": time.time(),
                        },
                    )

                    # Update last ping
                    if connection_id in self.connection_info:
                        self.connection_info[connection_id].last_ping = time.time()

                except Exception as e:
                    logger.error(f"Heartbeat failed for {connection_id}: {e}")
                    await self.disconnect(connection_id)

        logger.info("WebSocket heartbeat stopped")

    async def handle_pong(self, connection_id: str):
        """Handle pong response from client."""
        if connection_id in self.connection_info:
            self.connection_info[connection_id].last_ping = time.time()


# ============================================================================
# Singleton Manager
# ============================================================================

_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get global WebSocket manager instance."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "WebSocketMessage",
    "ConnectionInfo",
    "WebSocketManager",
    "get_websocket_manager",
]
