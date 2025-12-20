"""Learning from Demonstration REST API."""
from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional

from app.modules.learning.schemas import (
    Demonstration,
    TrajectoryPoint,
    TrajectoryPlaybackRequest,
    PolicyLearningRequest,
    LearnedPolicy,
)
from app.modules.learning.service import get_learning_service

router = APIRouter(prefix="/api/learning", tags=["Learning"])

@router.get("/info")
def get_learning_info():
    return {
        "name": "Learning from Demonstration",
        "version": "1.0.0",
        "features": [
            "Trajectory recording",
            "Demonstration playback",
            "Policy learning (BC, DAgger)",
            "Model persistence"
        ],
        "algorithms": ["behavioral_cloning", "dagger", "gail"]
    }

# Recording Endpoints
@router.post("/demonstrations/start-recording", status_code=status.HTTP_201_CREATED)
def start_recording(demo_id: str, robot_id: str, task_name: str):
    """Start recording demonstration."""
    service = get_learning_service()
    success = service.start_recording(demo_id, robot_id, task_name)
    if not success:
        raise HTTPException(status_code=400, detail="Recording already active")
    return {"message": "Recording started", "demo_id": demo_id}

@router.post("/demonstrations/{demo_id}/add-point")
def add_trajectory_point(demo_id: str, point: TrajectoryPoint):
    """Add trajectory point to active recording."""
    service = get_learning_service()
    success = service.add_trajectory_point(demo_id, point)
    if not success:
        raise HTTPException(status_code=404, detail="No active recording")
    return {"message": "Point added"}

@router.post("/demonstrations/stop-recording", response_model=Demonstration)
def stop_recording(demo: Demonstration):
    """Stop recording and save demonstration."""
    service = get_learning_service()
    return service.stop_recording(demo)

@router.get("/demonstrations", response_model=List[Demonstration])
def list_demonstrations(task_name: Optional[str] = Query(None)):
    """List demonstrations, optionally filtered by task."""
    service = get_learning_service()
    return service.list_demonstrations(task_name)

@router.get("/demonstrations/{demo_id}", response_model=Demonstration)
def get_demonstration(demo_id: str):
    """Get demonstration by ID."""
    service = get_learning_service()
    demo = service.get_demonstration(demo_id)
    if not demo:
        raise HTTPException(status_code=404, detail="Demonstration not found")
    return demo

# Playback Endpoints
@router.post("/playback")
async def playback_trajectory(request: TrajectoryPlaybackRequest):
    """Playback demonstration trajectory on robot."""
    service = get_learning_service()
    try:
        result = await service.playback_trajectory(request)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Policy Learning Endpoints
@router.post("/policies/learn", response_model=LearnedPolicy, status_code=status.HTTP_201_CREATED)
def learn_policy(request: PolicyLearningRequest):
    """Learn policy from demonstrations."""
    service = get_learning_service()
    try:
        return service.learn_policy(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/policies/{policy_id}", response_model=LearnedPolicy)
def get_policy(policy_id: str):
    """Get learned policy."""
    service = get_learning_service()
    policy = service.get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy
