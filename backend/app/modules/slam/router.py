"""SLAM REST API."""
from fastapi import APIRouter, Depends

from app.core.auth_deps import require_auth, get_current_principal, Principal

router = APIRouter(
    prefix="/api/slam",
    tags=["SLAM"],
    dependencies=[Depends(require_auth)]
)

@router.get("/info")
def get_slam_info():
    return {
        "name": "SLAM Integration",
        "version": "1.0.0",
        "backends": ["nav2", "slam_toolbox", "cartographer"],
        "features": ["Mapping", "Localization", "Loop closure"]
    }

@router.get("/map")
async def get_current_map():
    return {"status": "mock_map", "resolution": 0.05, "size": [100, 100]}

@router.get("/pose")
async def get_robot_pose():
    return {"x": 0.0, "y": 0.0, "theta": 0.0, "confidence": 0.95}
