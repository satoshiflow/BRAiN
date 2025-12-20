"""Multi-Robot Collaboration REST API."""
from fastapi import APIRouter, HTTPException, status
from typing import List

from app.modules.collaboration.schemas import (
    FormationConfig,
    CollaborativeTask,
    TaskBid,
    SharedWorldModel,
    RobotPosition,
)
from app.modules.collaboration.service import get_collaboration_service

router = APIRouter(prefix="/api/collaboration", tags=["Collaboration"])

@router.get("/info")
def get_collaboration_info():
    return {
        "name": "Multi-Robot Collaboration",
        "version": "1.0.0",
        "features": [
            "Formation control",
            "Task allocation (auction, greedy, consensus)",
            "Shared world models",
            "Coordinated execution"
        ]
    }

# Formation Endpoints
@router.post("/formations", response_model=FormationConfig, status_code=status.HTTP_201_CREATED)
def create_formation(config: FormationConfig):
    """Create formation configuration."""
    service = get_collaboration_service()
    return service.create_formation(config)

@router.get("/formations/{formation_id}", response_model=FormationConfig)
def get_formation(formation_id: str):
    """Get formation configuration."""
    service = get_collaboration_service()
    formation = service.get_formation(formation_id)
    if not formation:
        raise HTTPException(status_code=404, detail="Formation not found")
    return formation

@router.put("/formations/{formation_id}", response_model=FormationConfig)
def update_formation(formation_id: str, robot_positions: List[RobotPosition]):
    """Update formation robot positions."""
    service = get_collaboration_service()
    try:
        return service.update_formation(formation_id, robot_positions)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Task Allocation Endpoints
@router.post("/tasks", response_model=CollaborativeTask, status_code=status.HTTP_201_CREATED)
def create_collaborative_task(task: CollaborativeTask):
    """Create collaborative task."""
    service = get_collaboration_service()
    return service.create_collaborative_task(task)

@router.post("/tasks/{task_id}/bids", status_code=status.HTTP_201_CREATED)
def submit_task_bid(task_id: str, bid: TaskBid):
    """Submit robot bid for task."""
    service = get_collaboration_service()
    success = service.submit_bid(bid)
    if not success:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Bid submitted", "task_id": task_id, "robot_id": bid.robot_id}

@router.post("/tasks/{task_id}/allocate", response_model=List[str])
def allocate_task(task_id: str):
    """Allocate task using auction mechanism."""
    service = get_collaboration_service()
    try:
        allocated = service.allocate_task_auction(task_id)
        return allocated
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Shared World Model Endpoints
@router.post("/world-models", response_model=SharedWorldModel, status_code=status.HTTP_201_CREATED)
def create_world_model(model: SharedWorldModel):
    """Create shared world model."""
    service = get_collaboration_service()
    return service.create_world_model(model)

@router.put("/world-models/{model_id}", response_model=SharedWorldModel)
def update_world_model(model_id: str, obstacles: List = None, points_of_interest: List = None):
    """Update shared world model."""
    service = get_collaboration_service()
    try:
        return service.update_world_model(model_id, obstacles, points_of_interest)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
