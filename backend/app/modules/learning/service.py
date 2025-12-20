"""Learning from Demonstration Service."""
from typing import Dict, List, Optional
import logging

from app.modules.learning.schemas import (
    Demonstration,
    TrajectoryPlaybackRequest,
    PolicyLearningRequest,
    LearnedPolicy,
    TrajectoryPoint,
)

logger = logging.getLogger(__name__)

class LearningService:
    """Manages learning from demonstration."""
    
    def __init__(self):
        self.demonstrations: Dict[str, Demonstration] = {}
        self.policies: Dict[str, LearnedPolicy] = {}
        self.active_recordings: Dict[str, List[TrajectoryPoint]] = {}
        
    # Demonstration Recording
    def start_recording(self, demo_id: str, robot_id: str, task_name: str) -> bool:
        """Start recording demonstration."""
        if demo_id in self.active_recordings:
            logger.warning(f"Recording already active: {demo_id}")
            return False
        
        self.active_recordings[demo_id] = []
        logger.info(f"Started recording: {demo_id} for {task_name}")
        return True
    
    def add_trajectory_point(self, demo_id: str, point: TrajectoryPoint) -> bool:
        """Add point to active recording."""
        if demo_id not in self.active_recordings:
            logger.warning(f"No active recording: {demo_id}")
            return False
        
        self.active_recordings[demo_id].append(point)
        return True
    
    def stop_recording(self, demo: Demonstration) -> Demonstration:
        """Stop recording and save demonstration."""
        if demo.demo_id in self.active_recordings:
            demo.trajectory = self.active_recordings[demo.demo_id]
            del self.active_recordings[demo.demo_id]
        
        self.demonstrations[demo.demo_id] = demo
        logger.info(f"Saved demonstration: {demo.demo_id} ({len(demo.trajectory)} points)")
        return demo
    
    def get_demonstration(self, demo_id: str) -> Optional[Demonstration]:
        """Get demonstration by ID."""
        return self.demonstrations.get(demo_id)
    
    def list_demonstrations(self, task_name: Optional[str] = None) -> List[Demonstration]:
        """List demonstrations, optionally filtered by task."""
        demos = list(self.demonstrations.values())
        if task_name:
            demos = [d for d in demos if d.task_name == task_name]
        return demos
    
    # Trajectory Playback
    async def playback_trajectory(self, request: TrajectoryPlaybackRequest) -> Dict:
        """Playback demonstration trajectory on robot."""
        demo = self.demonstrations.get(request.demo_id)
        if not demo:
            raise ValueError(f"Demonstration not found: {request.demo_id}")
        
        logger.info(f"Playing back trajectory: {request.demo_id} on {request.robot_id}")
        
        # In production: send trajectory to robot controller
        # For now: return playback info
        return {
            "demo_id": request.demo_id,
            "robot_id": request.robot_id,
            "points_count": len(demo.trajectory),
            "estimated_duration_s": demo.duration_s / request.speed_factor,
            "status": "playback_started"
        }
    
    # Policy Learning
    def learn_policy(self, request: PolicyLearningRequest) -> LearnedPolicy:
        """Learn policy from demonstrations."""
        # Collect demonstrations
        demos = [self.demonstrations[did] for did in request.demo_ids if did in self.demonstrations]
        
        if not demos:
            raise ValueError("No valid demonstrations found")
        
        logger.info(f"Learning policy: {request.policy_id} from {len(demos)} demonstrations")
        
        # Mock policy learning
        # In production: train actual model (BC, DAgger, etc.)
        policy = LearnedPolicy(
            policy_id=request.policy_id,
            task_name=demos[0].task_name,
            algorithm=request.algorithm,
            num_demonstrations=len(demos),
            training_accuracy=0.92,  # Mock accuracy
            validation_accuracy=0.88,
            model_path=f"/models/{request.policy_id}.pt"
        )
        
        self.policies[request.policy_id] = policy
        logger.info(f"Policy learned: {request.policy_id} (acc: {policy.training_accuracy:.2f})")
        return policy
    
    def get_policy(self, policy_id: str) -> Optional[LearnedPolicy]:
        """Get learned policy."""
        return self.policies.get(policy_id)

# Singleton
_learning_service: Optional[LearningService] = None

def get_learning_service() -> LearningService:
    global _learning_service
    if _learning_service is None:
        _learning_service = LearningService()
    return _learning_service
