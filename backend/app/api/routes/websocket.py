"""
WebSocket API Router - Real-time updates for dashboards

Provides WebSocket endpoints for live data streaming to frontend
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set, Dict, List
import asyncio
import json
import time
from loguru import logger

router = APIRouter(prefix="/api/ws", tags=["websocket"])

# ========== Connection Manager ==========

class ConnectionManager:
    """Manages WebSocket connections and broadcasts"""

    def __init__(self):
        # Map of channel_name -> set of active websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str):
        """Accept WebSocket connection and add to channel"""
        await websocket.accept()
        async with self._lock:
            if channel not in self.active_connections:
                self.active_connections[channel] = set()
            self.active_connections[channel].add(websocket)
        logger.info(f"WebSocket connected to channel: {channel}")

    async def disconnect(self, websocket: WebSocket, channel: str):
        """Remove WebSocket from channel"""
        async with self._lock:
            if channel in self.active_connections:
                self.active_connections[channel].discard(websocket)
                if not self.active_connections[channel]:
                    del self.active_connections[channel]
        logger.info(f"WebSocket disconnected from channel: {channel}")

    async def broadcast(self, channel: str, message: dict):
        """Broadcast message to all clients in channel"""
        async with self._lock:
            if channel not in self.active_connections:
                return

            # Convert message to JSON
            json_message = json.dumps(message)

            # Send to all connections in channel
            dead_connections = set()
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_text(json_message)
                except Exception as e:
                    logger.warning(f"Failed to send to WebSocket: {e}")
                    dead_connections.add(connection)

            # Clean up dead connections
            if dead_connections:
                self.active_connections[channel] -= dead_connections

    def get_connection_count(self, channel: str) -> int:
        """Get number of active connections in channel"""
        return len(self.active_connections.get(channel, set()))


# Singleton instance
_connection_manager: ConnectionManager | None = None


def get_connection_manager() -> ConnectionManager:
    """Get singleton ConnectionManager"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


# ========== WebSocket Endpoints ==========


@router.websocket("/maintenance")
async def websocket_maintenance(websocket: WebSocket):
    """
    WebSocket endpoint for real-time maintenance updates

    Streams:
    - Health metrics updates
    - New anomaly detections
    - Failure predictions
    - Maintenance schedule changes
    """
    manager = get_connection_manager()
    channel = "maintenance"

    await manager.connect(websocket, channel)

    try:
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()

            # Client can send ping to keep alive
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            else:
                # Echo back for debugging
                await websocket.send_text(json.dumps({"type": "echo", "data": data}))

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error in maintenance channel: {e}")
        await manager.disconnect(websocket, channel)


@router.websocket("/simulator")
async def websocket_simulator(websocket: WebSocket):
    """
    WebSocket endpoint for real-time simulator updates

    Streams:
    - Robot status changes
    - Simulator start/stop events
    - Health metric updates (from simulator)
    """
    manager = get_connection_manager()
    channel = "simulator"

    await manager.connect(websocket, channel)

    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            else:
                await websocket.send_text(json.dumps({"type": "echo", "data": data}))

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error in simulator channel: {e}")
        await manager.disconnect(websocket, channel)


@router.websocket("/collaboration")
async def websocket_collaboration(websocket: WebSocket):
    """
    WebSocket endpoint for real-time collaboration updates

    Streams:
    - Task allocation changes
    - Formation updates
    - Shared world model changes
    """
    manager = get_connection_manager()
    channel = "collaboration"

    await manager.connect(websocket, channel)

    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            else:
                await websocket.send_text(json.dumps({"type": "echo", "data": data}))

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error in collaboration channel: {e}")
        await manager.disconnect(websocket, channel)


@router.websocket("/navigation")
async def websocket_navigation(websocket: WebSocket):
    """
    WebSocket endpoint for real-time navigation updates

    Streams:
    - Robot position updates
    - Path planning changes
    - Obstacle detection events
    """
    manager = get_connection_manager()
    channel = "navigation"

    await manager.connect(websocket, channel)

    try:
        while True:
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong", "timestamp": time.time()}))
            else:
                await websocket.send_text(json.dumps({"type": "echo", "data": data}))

    except WebSocketDisconnect:
        await manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error in navigation channel: {e}")
        await manager.disconnect(websocket, channel)


@router.get("/status")
async def get_websocket_status():
    """Get WebSocket connection statistics"""
    manager = get_connection_manager()

    return {
        "active_channels": list(manager.active_connections.keys()),
        "connections": {
            channel: manager.get_connection_count(channel)
            for channel in manager.active_connections.keys()
        },
        "total_connections": sum(
            manager.get_connection_count(channel)
            for channel in manager.active_connections.keys()
        ),
    }


# ========== Broadcast Helper Functions ==========

async def broadcast_health_metric(component_id: str, health_score: float, timestamp: float):
    """Broadcast health metric update to maintenance channel"""
    manager = get_connection_manager()
    await manager.broadcast("maintenance", {
        "type": "health_metric",
        "component_id": component_id,
        "health_score": health_score,
        "timestamp": timestamp,
    })


async def broadcast_anomaly_detected(anomaly_type: str, severity: str, component_id: str):
    """Broadcast anomaly detection to maintenance channel"""
    manager = get_connection_manager()
    await manager.broadcast("maintenance", {
        "type": "anomaly_detected",
        "anomaly_type": anomaly_type,
        "severity": severity,
        "component_id": component_id,
        "timestamp": time.time(),
    })


async def broadcast_simulator_status(status: str, robot_count: int):
    """Broadcast simulator status change to simulator channel"""
    manager = get_connection_manager()
    await manager.broadcast("simulator", {
        "type": "simulator_status",
        "status": status,
        "robot_count": robot_count,
        "timestamp": time.time(),
    })


async def broadcast_task_allocated(task_id: str, robot_ids: List[str]):
    """Broadcast task allocation to collaboration channel"""
    manager = get_connection_manager()
    await manager.broadcast("collaboration", {
        "type": "task_allocated",
        "task_id": task_id,
        "robot_ids": robot_ids,
        "timestamp": time.time(),
    })


async def broadcast_formation_updated(formation_id: str, formation_type: str):
    """Broadcast formation update to collaboration channel"""
    manager = get_connection_manager()
    await manager.broadcast("collaboration", {
        "type": "formation_updated",
        "formation_id": formation_id,
        "formation_type": formation_type,
        "timestamp": time.time(),
    })
