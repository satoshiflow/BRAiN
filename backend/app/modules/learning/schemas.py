"""Learning from Demonstration Schemas."""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class DemonstrationMode(str, Enum):
    """Demonstration recording modes."""
    TELEOPERATION = "teleoperation"
    KINESTHETIC = "kinesthetic"
    VISION_BASED = "vision_based"

class TrajectoryPoint(BaseModel):
    """Single point in trajectory."""
    timestamp: float
    position: Dict[str, float] = Field(description="x, y, z coordinates")
    velocity: Dict[str, float] = Field(description="vx, vy, vz")
    orientation: Optional[Dict[str, float]] = None
    gripper_state: Optional[float] = None

class Demonstration(BaseModel):
    """Recorded demonstration."""
    demo_id: str
    robot_id: str
    task_name: str
    mode: DemonstrationMode
    trajectory: List[TrajectoryPoint]
    duration_s: float
    success: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)

class TrajectoryPlaybackRequest(BaseModel):
    """Request to playback trajectory."""
    demo_id: str
    robot_id: str
    speed_factor: float = Field(default=1.0, ge=0.1, le=5.0)
    loop: bool = False

class PolicyLearningRequest(BaseModel):
    """Request to learn policy from demonstrations."""
    policy_id: str
    demo_ids: List[str] = Field(min_items=1)
    algorithm: str = Field(default="behavioral_cloning")
    hyperparameters: Dict[str, Any] = Field(default_factory=dict)

class LearnedPolicy(BaseModel):
    """Learned policy."""
    policy_id: str
    task_name: str
    algorithm: str
    num_demonstrations: int
    training_accuracy: float = Field(ge=0.0, le=1.0)
    validation_accuracy: Optional[float] = None
    model_path: Optional[str] = None
    trained_at: datetime = Field(default_factory=datetime.utcnow)
