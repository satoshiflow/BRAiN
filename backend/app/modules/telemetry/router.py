"""Fleet Telemetry REST API."""
from fastapi import APIRouter, WebSocket
from typing import Dict

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])

active_connections: Dict[str, WebSocket] = {}

@router.get("/info")
def get_telemetry_info():
    return {
        "name": "Fleet Telemetry System",
        "version": "1.0.0",
        "features": ["Real-time metrics", "WebSocket streaming", "Historical data"],
        "active_connections": len(active_connections)
    }

@router.websocket("/ws/{robot_id}")
async def telemetry_websocket(websocket: WebSocket, robot_id: str):
    await websocket.accept()
    active_connections[robot_id] = websocket
    try:
        while True:
            data = await websocket.receive_text()
            # Echo for testing
            await websocket.send_text(f"Echo: {data}")
    except:
        del active_connections[robot_id]

@router.get("/robots/{robot_id}/metrics")
async def get_robot_metrics(robot_id: str):
    return {
        "robot_id": robot_id,
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        "network_latency_ms": 12.5,
        "battery_percentage": 78.0
    }
