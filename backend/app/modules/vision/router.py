"""Vision Processing REST API."""
from fastapi import APIRouter, Depends

from app.core.auth_deps import require_auth, get_current_principal, Principal

router = APIRouter(
    prefix="/api/vision",
    tags=["Vision"],
    dependencies=[Depends(require_auth)]
)

@router.get("/info")
def get_vision_info():
    return {
        "name": "Vision Processing",
        "version": "1.0.0",
        "features": ["Object detection", "Person tracking", "Depth estimation"],
        "models": ["yolov8", "mediapipe"]
    }

@router.get("/cameras")
async def list_cameras():
    return {"cameras": [{"id": "camera_0", "resolution": "1280x720", "fps": 30}]}

@router.post("/detect")
async def detect_objects(camera_id: str):
    return {"camera_id": camera_id, "detections": [], "timestamp": "2024-12-19T12:00:00Z"}
