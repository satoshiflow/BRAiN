"""Hardware HAL REST API."""
from fastapi import APIRouter, Depends
from typing import Optional
import time
import logging

from app.core.auth_deps import require_auth, require_operator, get_current_principal, Principal

from .schemas import RobotHardwareState, MovementCommand

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/hardware",
    tags=["Hardware"],
    dependencies=[Depends(require_auth)]
)

# Optional EventStream import (Sprint 5: EventStream Integration)
try:
    from app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level EventStream (Sprint 5: EventStream Integration)
_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for Hardware module (Sprint 5)."""
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit Hardware event with error handling (non-blocking).

    Args:
        event_type: Event type (e.g., "hardware.command_sent")
        payload: Event payload dictionary

    Note:
        - Never raises exceptions
        - Logs failures at ERROR level
        - Gracefully handles missing EventStream
    """
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[HardwareRouter] EventStream not available, skipping event")
        return

    try:
        event = Event(
            type=event_type,
            source="hardware_router",
            target=None,  # Override per event
            payload=payload
        )
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"[HardwareRouter] Event publishing failed: {e}", exc_info=True)


@router.get("/info")
async def get_hardware_info():
    """Get hardware module information.

    Returns:
        dict: Module information

    Events:
        - hardware.info_queried (optional): Info endpoint accessed
    """
    result = {
        "name": "Hardware Abstraction Layer",
        "version": "1.0.0",
        "supported_platforms": ["unitree_go1", "unitree_go2", "unitree_b2"],
        "features": ["Motor control", "IMU reading", "Battery monitoring"]
    }

    # EVENT: hardware.info_queried (optional - Sprint 5)
    await _emit_event_safe("hardware.info_queried", {
        "version": result["version"],
        "queried_at": time.time(),
    })

    return result


@router.post("/robots/{robot_id}/command")
async def send_movement_command(robot_id: str, command: MovementCommand):
    """Send movement command to robot.

    Args:
        robot_id: Robot identifier
        command: Movement command (linear_x, linear_y, angular_z)

    Returns:
        dict: Command acknowledgment

    Events:
        - hardware.command_sent (required): Movement command issued
    """
    result = {"robot_id": robot_id, "status": "command_sent", "command": command}

    # EVENT: hardware.command_sent (required - Sprint 5)
    await _emit_event_safe("hardware.command_sent", {
        "robot_id": robot_id,
        "command_type": "movement",  # Fixed type for MovementCommand
        "command": command.model_dump(),
        "sent_at": time.time(),
    })

    return result


@router.get("/robots/{robot_id}/state")
async def get_robot_state(robot_id: str):
    """Get robot hardware state.

    Args:
        robot_id: Robot identifier

    Returns:
        dict: Robot state

    Events:
        - hardware.state_queried (optional): State endpoint accessed
    """
    result = {"robot_id": robot_id, "status": "mock_state"}

    # EVENT: hardware.state_queried (optional - Sprint 5)
    await _emit_event_safe("hardware.state_queried", {
        "robot_id": robot_id,
        "queried_at": time.time(),
    })

    return result
