"""Multi-Robot Collaboration Service."""
from typing import Dict, List, Optional
from datetime import datetime
import logging

from app.modules.collaboration.schemas import (
    FormationConfig,
    CollaborativeTask,
    TaskBid,
    SharedWorldModel,
    RobotPosition,
    TaskAllocationStrategy,
)

logger = logging.getLogger(__name__)

class CollaborationService:
    """Manages multi-robot collaboration."""
    
    def __init__(self):
        self.formations: Dict[str, FormationConfig] = {}
        self.collaborative_tasks: Dict[str, CollaborativeTask] = {}
        self.task_bids: Dict[str, List[TaskBid]] = {}
        self.world_models: Dict[str, SharedWorldModel] = {}
        
    # Formation Control
    def create_formation(self, config: FormationConfig) -> FormationConfig:
        """Create formation configuration."""
        self.formations[config.formation_id] = config
        logger.info(f"Formation created: {config.formation_id} ({config.formation_type})")
        return config
    
    def get_formation(self, formation_id: str) -> Optional[FormationConfig]:
        """Get formation configuration."""
        return self.formations.get(formation_id)
    
    def update_formation(
        self, 
        formation_id: str, 
        robot_positions: List[RobotPosition]
    ) -> FormationConfig:
        """Update robot positions in formation."""
        if formation_id not in self.formations:
            raise ValueError(f"Formation not found: {formation_id}")
        
        formation = self.formations[formation_id]
        formation.robot_positions = robot_positions
        return formation
    
    # Task Allocation
    def create_collaborative_task(self, task: CollaborativeTask) -> CollaborativeTask:
        """Create collaborative task."""
        self.collaborative_tasks[task.task_id] = task
        self.task_bids[task.task_id] = []
        logger.info(f"Collaborative task created: {task.task_id}")
        return task
    
    def submit_bid(self, bid: TaskBid) -> bool:
        """Submit robot bid for task."""
        if bid.task_id not in self.task_bids:
            return False
        
        self.task_bids[bid.task_id].append(bid)
        logger.info(f"Bid submitted: {bid.robot_id} for {bid.task_id} (value: {bid.bid_value})")
        return True
    
    def allocate_task_auction(self, task_id: str) -> List[str]:
        """Allocate task using auction mechanism."""
        if task_id not in self.collaborative_tasks:
            raise ValueError(f"Task not found: {task_id}")
        
        task = self.collaborative_tasks[task_id]
        bids = self.task_bids.get(task_id, [])
        
        # Sort by bid value (lower = better for cost, higher = better for utility)
        # Assuming utility-based: higher is better
        sorted_bids = sorted(bids, key=lambda b: b.bid_value, reverse=True)
        
        # Allocate to top bidders
        allocated = [bid.robot_id for bid in sorted_bids[:task.required_robots]]
        task.assigned_robots = allocated
        
        logger.info(f"Task allocated: {task_id} -> {allocated}")
        return allocated
    
    # Shared World Model
    def create_world_model(self, model: SharedWorldModel) -> SharedWorldModel:
        """Create shared world model."""
        self.world_models[model.model_id] = model
        return model
    
    def update_world_model(
        self, 
        model_id: str, 
        obstacles: Optional[List] = None,
        points_of_interest: Optional[List] = None
    ) -> SharedWorldModel:
        """Update shared world model."""
        if model_id not in self.world_models:
            raise ValueError(f"World model not found: {model_id}")
        
        model = self.world_models[model_id]
        
        if obstacles is not None:
            model.obstacles = obstacles
        if points_of_interest is not None:
            model.points_of_interest = points_of_interest
        
        model.last_updated = datetime.utcnow()
        return model

# Singleton
_collaboration_service: Optional[CollaborationService] = None

def get_collaboration_service() -> CollaborationService:
    global _collaboration_service
    if _collaboration_service is None:
        _collaboration_service = CollaborationService()
    return _collaboration_service
