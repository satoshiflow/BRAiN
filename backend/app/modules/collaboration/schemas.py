"""Multi-Robot Collaboration Schemas."""
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class FormationType(str, Enum):
    """Formation patterns."""
    LINE = "line"
    COLUMN = "column"
    WEDGE = "wedge"
    CIRCLE = "circle"
    GRID = "grid"
    CUSTOM = "custom"

class TaskAllocationStrategy(str, Enum):
    """Task allocation strategies."""
    GREEDY = "greedy"
    AUCTION = "auction"
    CONSENSUS = "consensus"
    LEARNING_BASED = "learning_based"

class CoordinationMode(str, Enum):
    """Coordination modes."""
    CENTRALIZED = "centralized"
    DECENTRALIZED = "decentralized"
    HYBRID = "hybrid"

class RobotPosition(BaseModel):
    """Robot position in formation."""
    robot_id: str
    x: float
    y: float
    theta: float = 0.0

class FormationConfig(BaseModel):
    """Formation configuration."""
    formation_id: str
    formation_type: FormationType
    leader_robot_id: Optional[str] = None
    robot_positions: List[RobotPosition]
    spacing: float = Field(default=1.0, ge=0.1)
    
class CollaborativeTask(BaseModel):
    """Task requiring multiple robots."""
    task_id: str
    task_type: str
    description: str
    required_robots: int = Field(ge=1)
    assigned_robots: List[str] = Field(default_factory=list)
    allocation_strategy: TaskAllocationStrategy
    coordination_mode: CoordinationMode
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
class TaskBid(BaseModel):
    """Robot bid for task."""
    robot_id: str
    task_id: str
    bid_value: float = Field(description="Cost/utility score")
    capabilities_match: float = Field(ge=0.0, le=1.0)
    
class SharedWorldModel(BaseModel):
    """Shared world state."""
    model_id: str
    robots: List[str]
    obstacles: List[Dict[str, Any]] = Field(default_factory=list)
    points_of_interest: List[Dict[str, Any]] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
