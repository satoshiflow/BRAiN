"""
Simulator API Router - Control the robot simulator
"""

from fastapi import APIRouter
from .robot_simulator import get_simulator

router = APIRouter(prefix="/api/simulator", tags=["simulator"])


@router.post("/start")
async def start_simulator():
    """Start the robot simulator"""
    simulator = get_simulator()
    await simulator.start()
    return {
        "status": "started",
        "robots": list(simulator.robots.keys()),
        "message": "Simulator running. Robots will send health metrics every 5 seconds.",
    }


@router.post("/stop")
async def stop_simulator():
    """Stop the robot simulator"""
    simulator = get_simulator()
    await simulator.stop()
    return {"status": "stopped"}


@router.get("/status")
async def get_simulator_status():
    """Get simulator status"""
    simulator = get_simulator()
    return {
        "running": simulator.running,
        "robot_count": len(simulator.robots),
        "robots": [
            simulator.get_robot_status(robot_id) for robot_id in simulator.robots.keys()
        ],
    }


@router.get("/info")
async def get_simulator_info():
    """Get simulator information"""
    return {
        "module": "Robot Simulator",
        "version": "1.0.0",
        "description": "Simulates multiple robots with health degradation, anomalies, and predictions",
        "features": [
            "Auto-generates health metrics every 5 seconds",
            "Simulates 5 robots (robot_01 to robot_05)",
            "Health degrades over time",
            "Triggers anomalies (temperature spikes, vibration)",
            "Generates failure predictions for low-health components",
        ],
        "endpoints": {
            "start": "POST /api/simulator/start",
            "stop": "POST /api/simulator/stop",
            "status": "GET /api/simulator/status",
        },
    }
