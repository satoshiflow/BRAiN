"""Fleet Telemetry REST API."""
from fastapi import APIRouter, WebSocket
from typing import Dict, Optional
import time

from loguru import logger

router = APIRouter(prefix="/api/telemetry", tags=["Telemetry"])

active_connections: Dict[str, WebSocket] = {}

# EventStream integration (Sprint 4)
try:
    from backend.mission_control_core.core import EventStream, Event
except ImportError:
    EventStream = None
    Event = None
    import warnings
    warnings.warn(
        "[TelemetryService] EventStream not available (mission_control_core not installed)",
        RuntimeWarning
    )

# Module-level EventStream (functional architecture pattern)
_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
    """
    Set the EventStream instance (called at startup).

    Sprint 4 EventStream Integration.
    """
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """
    Emit telemetry event with error handling (non-blocking).

    Charter v1.0 Compliance:
    - Event publishing MUST NOT block business logic
    - Failures are logged but NOT raised
    - Graceful degradation when EventStream unavailable
    """
    global _event_stream

    if _event_stream is None or Event is None:
        logger.debug("[TelemetryService] EventStream not available, skipping event: %s", event_type)
        return

    try:
        # Create and publish event
        event = Event(
            type=event_type,
            source="telemetry_service",
            target=None,
            payload=payload,
        )

        await _event_stream.publish(event)

        logger.debug(
            "[TelemetryService] Event published: %s (robot_id=%s)",
            event_type,
            payload.get("robot_id", "unknown"),
        )

    except Exception as e:
        logger.error(
            "[TelemetryService] Event publishing failed: %s (event_type=%s)",
            e,
            event_type,
            exc_info=True,
        )
        # DO NOT raise - business logic must continue


@router.get("/info")
def get_telemetry_info():
    """Get telemetry system information."""
    return {
        "name": "Fleet Telemetry System",
        "version": "1.0.0",
        "features": ["Real-time metrics", "WebSocket streaming", "Historical data"],
        "active_connections": len(active_connections)
    }


@router.websocket("/ws/{robot_id}")
async def telemetry_websocket(websocket: WebSocket, robot_id: str):
    """
    WebSocket endpoint for real-time telemetry streaming.

    Sprint 4 EventStream Integration:
    - telemetry.connection_established: WebSocket connection established
    - telemetry.connection_closed: WebSocket connection closed
    """
    # Generate unique connection ID
    connection_id = f"ws_{robot_id}_{int(time.time())}"
    connect_time = time.time()

    await websocket.accept()
    active_connections[robot_id] = websocket

    # EVENT: telemetry.connection_established
    await _emit_event_safe(
        event_type="telemetry.connection_established",
        payload={
            "robot_id": robot_id,
            "connection_id": connection_id,
            "connected_at": connect_time,
        }
    )

    try:
        while True:
            data = await websocket.receive_text()
            # Echo for testing
            await websocket.send_text(f"Echo: {data}")

    except Exception:
        # Calculate connection duration
        duration_seconds = time.time() - connect_time

        # EVENT: telemetry.connection_closed
        await _emit_event_safe(
            event_type="telemetry.connection_closed",
            payload={
                "robot_id": robot_id,
                "connection_id": connection_id,
                "duration_seconds": duration_seconds,
                "reason": "client_disconnect",
                "disconnected_at": time.time(),
            }
        )

        # Cleanup
        if robot_id in active_connections:
            del active_connections[robot_id]


@router.get("/robots/{robot_id}/metrics")
async def get_robot_metrics(robot_id: str):
    """
    Get current robot metrics (mock data).

    Sprint 4 EventStream Integration:
    - telemetry.metrics_published: Robot metrics published (optional)
    """
    # Mock metrics data
    metrics = {
        "robot_id": robot_id,
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        "network_latency_ms": 12.5,
        "battery_percentage": 78.0
    }

    # EVENT: telemetry.metrics_published (optional - can be enabled/disabled)
    await _emit_event_safe(
        event_type="telemetry.metrics_published",
        payload={
            "robot_id": robot_id,
            "metrics": {
                "cpu_usage": metrics["cpu_usage"],
                "memory_usage": metrics["memory_usage"],
                "network_latency_ms": metrics["network_latency_ms"],
                "battery_percentage": metrics["battery_percentage"],
            },
            "published_at": time.time(),
        }
    )

    return metrics
