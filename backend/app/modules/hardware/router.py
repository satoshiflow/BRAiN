"""Hardware HAL REST API."""
from fastapi import APIRouter
from app.modules.hardware.schemas import RobotHardwareState, MovementCommand

router = APIRouter(prefix="/api/hardware", tags=["Hardware"])

@router.get("/info")
def get_hardware_info():
    return {
        "name": "Hardware Abstraction Layer",
        "version": "1.0.0",
        "supported_platforms": ["unitree_go1", "unitree_go2", "unitree_b2"],
        "features": ["Motor control", "IMU reading", "Battery monitoring"]
    }

@router.post("/robots/{robot_id}/command")
async def send_movement_command(robot_id: str, command: MovementCommand):
    return {"robot_id": robot_id, "status": "command_sent", "command": command}

@router.get("/robots/{robot_id}/state")
async def get_robot_state(robot_id: str):
    return {"robot_id": robot_id, "status": "mock_state"}
