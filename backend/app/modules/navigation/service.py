"""
Advanced Navigation Service

Business logic for social-aware navigation, dynamic obstacle avoidance,
formation control, and context-aware path planning.
"""

from typing import Dict, List, Optional, Tuple
import time
import math
from collections import defaultdict

from .schemas import (
    NavigationGoal,
    PlannedPath,
    PathSegment,
    Position2D,
    Velocity2D,
    Obstacle,
    ObstacleType,
    SocialZone,
    NavigationStatus,
    NavigationContext,
    NavigationBehavior,
    PathPlanningMode,
    SocialNavigationParams,
    FormationNavigationRequest,
    DynamicObstacleAvoidanceRequest,
    AvoidanceManeuver,
    ObstacleAvoidanceStrategy,
    ContextAdaptationRequest,
    AdaptedNavigationParams,
)


class AdvancedNavigationService:
    """
    Service for advanced navigation capabilities.

    Provides social-aware path planning, dynamic obstacle avoidance,
    formation navigation, and context adaptation.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize service."""
        if self._initialized:
            return

        # In-memory storage
        self.goals: Dict[str, NavigationGoal] = {}
        self.paths: Dict[str, PlannedPath] = {}
        self.status: Dict[str, NavigationStatus] = {}  # robot_id -> status
        self.obstacles: Dict[str, List[Obstacle]] = defaultdict(list)  # robot_id -> obstacles

        # Default social navigation parameters
        self.social_params = SocialNavigationParams()

        self._initialized = True

    # ========== Path Planning ==========

    def plan_path(self, goal: NavigationGoal) -> PlannedPath:
        """
        Plan a path to the goal using specified planning mode.

        Considers social constraints, dynamic obstacles, and context.
        """
        self.goals[goal.goal_id] = goal

        # Get current robot status
        current_status = self.status.get(goal.robot_id)
        if not current_status:
            # Initialize with default position
            current_position = Position2D(x=0.0, y=0.0, theta=0.0)
        else:
            current_position = current_status.current_position

        # Plan path based on mode
        if goal.planning_mode == PathPlanningMode.SOCIAL_AWARE:
            path = self._plan_social_aware_path(current_position, goal)
        elif goal.planning_mode == PathPlanningMode.FORMATION:
            path = self._plan_formation_path(current_position, goal)
        elif goal.planning_mode == PathPlanningMode.DYNAMIC_WINDOW:
            path = self._plan_dwa_path(current_position, goal)
        else:
            # Default: direct path
            path = self._plan_direct_path(current_position, goal)

        self.paths[path.path_id] = path
        return path

    def _plan_direct_path(self, start: Position2D, goal: NavigationGoal) -> PlannedPath:
        """Plan direct (shortest) path."""
        # Simple straight-line path
        distance = math.sqrt(
            (goal.target_position.x - start.x) ** 2 +
            (goal.target_position.y - start.y) ** 2
        )

        duration = distance / goal.max_velocity

        # Generate waypoints
        num_segments = max(int(duration / 0.5), 2)  # 0.5s per segment
        segments = []

        for i in range(num_segments + 1):
            t = i / num_segments
            pos = Position2D(
                x=start.x + t * (goal.target_position.x - start.x),
                y=start.y + t * (goal.target_position.y - start.y),
                theta=math.atan2(
                    goal.target_position.y - start.y,
                    goal.target_position.x - start.x
                )
            )
            vel = Velocity2D(
                linear=goal.max_velocity if i < num_segments else 0.0,
                angular=0.0
            )
            segments.append(PathSegment(
                position=pos,
                velocity=vel,
                timestamp=time.time() + i * (duration / num_segments)
            ))

        return PlannedPath(
            path_id=f"path_{goal.goal_id}_{int(time.time())}",
            goal_id=goal.goal_id,
            robot_id=goal.robot_id,
            segments=segments,
            total_distance=distance,
            estimated_duration=duration,
            safety_score=0.8,
        )

    def _plan_social_aware_path(self, start: Position2D, goal: NavigationGoal) -> PlannedPath:
        """
        Plan socially-aware path that respects human personal space.

        Uses modified A* with social cost function.
        """
        # Get obstacles (especially humans)
        obstacles = self.obstacles.get(goal.robot_id, [])
        humans = [obs for obs in obstacles if obs.obstacle_type == ObstacleType.HUMAN]

        # Start with direct path
        path = self._plan_direct_path(start, goal)

        # Modify path to avoid human personal space
        modified_segments = []
        social_cost = 0.0

        for segment in path.segments:
            # Check proximity to humans
            min_human_dist = float('inf')
            for human in humans:
                dist = math.sqrt(
                    (segment.position.x - human.position.x) ** 2 +
                    (segment.position.y - human.position.y) ** 2
                )
                min_human_dist = min(min_human_dist, dist)

                # Add social cost based on zone violation
                if dist < self.social_params.intimate_zone_radius:
                    social_cost += 10.0
                elif dist < self.social_params.personal_zone_radius:
                    social_cost += 5.0
                elif dist < self.social_params.social_zone_radius:
                    social_cost += 1.0

            # Deform path if too close to humans
            if min_human_dist < goal.min_human_distance:
                # Simple deformation: move perpendicular to human
                # (production: use proper path deformation algorithm)
                segment.position.x += 0.2  # Mock deformation
                segment.position.y += 0.2

            modified_segments.append(segment)

        path.segments = modified_segments
        path.social_cost = social_cost
        path.safety_score = max(0.5, 1.0 - social_cost / 50.0)

        return path

    def _plan_formation_path(self, start: Position2D, goal: NavigationGoal) -> PlannedPath:
        """Plan path for formation navigation."""
        # Similar to direct path but considers formation constraints
        return self._plan_direct_path(start, goal)

    def _plan_dwa_path(self, start: Position2D, goal: NavigationGoal) -> PlannedPath:
        """
        Plan path using Dynamic Window Approach.

        Good for dynamic obstacle avoidance.
        """
        # Simplified DWA (production: full DWA implementation)
        return self._plan_direct_path(start, goal)

    # ========== Dynamic Obstacle Avoidance ==========

    def compute_avoidance_maneuver(
        self,
        request: DynamicObstacleAvoidanceRequest
    ) -> AvoidanceManeuver:
        """
        Compute avoidance maneuver for dynamic obstacles.

        Uses social force model for human-aware avoidance.
        """
        # Predict obstacle positions
        predicted_collisions = []

        for obstacle in request.detected_obstacles:
            if obstacle.velocity:
                # Predict future position
                future_pos = Position2D(
                    x=obstacle.position.x + obstacle.velocity.linear * request.prediction_horizon_s,
                    y=obstacle.position.y,
                    theta=obstacle.position.theta
                )

                # Check if on collision course
                dist_to_future = math.sqrt(
                    (future_pos.x - request.goal_position.x) ** 2 +
                    (future_pos.y - request.goal_position.y) ** 2
                )

                if dist_to_future < obstacle.radius + 0.5:  # Safety margin
                    predicted_collisions.append(obstacle)

        # Compute avoidance based on strategy
        if request.avoidance_strategy == ObstacleAvoidanceStrategy.STOP_AND_WAIT:
            if predicted_collisions:
                maneuver_type = "stop"
                recommended_vel = Velocity2D(linear=0.0, angular=0.0)
                duration = 2.0
                collision_risk = 0.8
            else:
                maneuver_type = "continue"
                recommended_vel = request.current_velocity
                duration = 1.0
                collision_risk = 0.1

        elif request.avoidance_strategy == ObstacleAvoidanceStrategy.SOCIAL_FORCE:
            # Social force model
            repulsive_force_x = 0.0
            repulsive_force_y = 0.0

            for obstacle in request.detected_obstacles:
                dx = request.current_position.x - obstacle.position.x
                dy = request.current_position.y - obstacle.position.y
                dist = math.sqrt(dx ** 2 + dy ** 2)

                if dist < 5.0:  # Influence range
                    # Repulsive force (inversely proportional to distance)
                    force_magnitude = 2.0 / (dist ** 2 + 0.1)

                    # Higher force for humans
                    if obstacle.obstacle_type == ObstacleType.HUMAN:
                        force_magnitude *= 2.0

                    repulsive_force_x += (dx / dist) * force_magnitude
                    repulsive_force_y += (dy / dist) * force_magnitude

            # Attractive force toward goal
            goal_dx = request.goal_position.x - request.current_position.x
            goal_dy = request.goal_position.y - request.current_position.y
            goal_dist = math.sqrt(goal_dx ** 2 + goal_dy ** 2)

            attractive_force_x = (goal_dx / goal_dist) * 1.0
            attractive_force_y = (goal_dy / goal_dist) * 1.0

            # Combined force
            total_force_x = attractive_force_x + repulsive_force_x
            total_force_y = attractive_force_y + repulsive_force_y

            # Convert to velocity
            force_magnitude = math.sqrt(total_force_x ** 2 + total_force_y ** 2)
            recommended_linear = min(force_magnitude, 1.0)  # Cap at 1 m/s

            # Compute angular velocity to align with force direction
            desired_angle = math.atan2(total_force_y, total_force_x)
            current_angle = request.current_position.theta or 0.0
            angle_diff = desired_angle - current_angle

            # Normalize angle difference
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi

            recommended_angular = angle_diff * 0.5  # Proportional control

            recommended_vel = Velocity2D(
                linear=recommended_linear,
                angular=recommended_angular
            )

            maneuver_type = "social_force_avoid"
            duration = 1.0
            collision_risk = 0.3 if predicted_collisions else 0.1

        else:
            # Default: slow down
            maneuver_type = "slow"
            recommended_vel = Velocity2D(
                linear=request.current_velocity.linear * 0.5,
                angular=request.current_velocity.angular
            )
            duration = 1.5
            collision_risk = 0.5

        # Calculate safety margin
        min_distance = float('inf')
        for obstacle in request.detected_obstacles:
            dist = math.sqrt(
                (request.current_position.x - obstacle.position.x) ** 2 +
                (request.current_position.y - obstacle.position.y) ** 2
            )
            min_distance = min(min_distance, dist - obstacle.radius)

        return AvoidanceManeuver(
            maneuver_id=f"maneuver_{request.robot_id}_{int(time.time())}",
            robot_id=request.robot_id,
            recommended_velocity=recommended_vel,
            duration_s=duration,
            safety_margin=max(min_distance, 0.0),
            collision_risk=collision_risk,
            maneuver_type=maneuver_type
        )

    # ========== Formation Navigation ==========

    def plan_formation_navigation(
        self,
        request: FormationNavigationRequest
    ) -> Dict[str, PlannedPath]:
        """
        Plan coordinated paths for formation navigation.

        Returns individual paths for each robot in formation.
        """
        paths = {}

        # Leader gets direct path
        leader_goal = NavigationGoal(
            goal_id=f"formation_leader_{request.formation_id}",
            robot_id=request.leader_id,
            target_position=request.target_position,
            planning_mode=PathPlanningMode.DIRECT
        )

        leader_path = self.plan_path(leader_goal)
        paths[request.leader_id] = leader_path

        # Followers maintain relative positions
        # (Simplified: production would use proper formation control)
        for i, follower_id in enumerate(request.robot_ids):
            if follower_id == request.leader_id:
                continue

            # Offset position based on formation type
            offset_x = -request.inter_robot_distance * (i + 1)
            offset_y = 0.0

            follower_target = Position2D(
                x=request.target_position.x + offset_x,
                y=request.target_position.y + offset_y,
                theta=request.target_position.theta
            )

            follower_goal = NavigationGoal(
                goal_id=f"formation_follower_{request.formation_id}_{follower_id}",
                robot_id=follower_id,
                target_position=follower_target,
                planning_mode=PathPlanningMode.FORMATION
            )

            paths[follower_id] = self.plan_path(follower_goal)

        return paths

    # ========== Context Adaptation ==========

    def adapt_to_context(
        self,
        request: ContextAdaptationRequest
    ) -> AdaptedNavigationParams:
        """
        Adapt navigation parameters based on environmental context.

        Returns context-specific navigation parameters.
        """
        adaptations = []

        # Default parameters
        max_velocity = 1.0
        max_acceleration = 0.5
        social_distance = 1.5
        behavior = NavigationBehavior.BALANCED

        # Context-specific adaptations
        if request.navigation_context == NavigationContext.HOSPITAL:
            max_velocity = 0.5  # Slow in hospitals
            social_distance = 2.0  # More space
            behavior = NavigationBehavior.CAUTIOUS
            adaptations.extend([
                "Reduced velocity for hospital environment",
                "Increased social distance for patient comfort",
                "Cautious behavior for safety"
            ])

        elif request.navigation_context == NavigationContext.WAREHOUSE:
            max_velocity = 1.5  # Faster in warehouses
            social_distance = 1.0  # Less social space needed
            behavior = NavigationBehavior.ASSERTIVE
            adaptations.extend([
                "Increased velocity for efficient operation",
                "Reduced social distance (less human interaction)",
                "Assertive behavior for productivity"
            ])

        elif request.navigation_context == NavigationContext.MALL:
            max_velocity = 0.7
            social_distance = 1.5
            behavior = NavigationBehavior.SOCIAL
            adaptations.extend([
                "Moderate velocity for crowded areas",
                "Standard social distance",
                "Social behavior for public comfort"
            ])

        elif request.navigation_context == NavigationContext.STREET:
            max_velocity = 1.2
            social_distance = 1.2
            behavior = NavigationBehavior.BALANCED
            adaptations.append("Balanced parameters for outdoor navigation")

        # Crowd density adaptation
        if request.crowd_density > 0.5:  # High density
            max_velocity *= 0.6
            social_distance *= 1.2
            adaptations.append(f"Reduced velocity due to high crowd density ({request.crowd_density:.2f} people/m²)")

        # Human detection adaptation
        if request.detected_humans > 5:
            behavior = NavigationBehavior.CAUTIOUS
            adaptations.append(f"Switched to cautious behavior ({request.detected_humans} humans detected)")

        reasoning = "; ".join(adaptations)

        return AdaptedNavigationParams(
            context=request.navigation_context,
            max_velocity=max_velocity,
            max_acceleration=max_acceleration,
            social_distance=social_distance,
            behavior=behavior,
            adaptations_applied=adaptations,
            reasoning=reasoning
        )

    # ========== Obstacle Management ==========

    def update_obstacles(self, robot_id: str, obstacles: List[Obstacle]):
        """Update detected obstacles for a robot."""
        self.obstacles[robot_id] = obstacles

    def get_obstacles(self, robot_id: str) -> List[Obstacle]:
        """Get current obstacles for a robot."""
        return self.obstacles.get(robot_id, [])

    # ========== Status Management ==========

    def update_status(self, status: NavigationStatus):
        """Update robot navigation status."""
        self.status[status.robot_id] = status

    def get_status(self, robot_id: str) -> Optional[NavigationStatus]:
        """Get robot navigation status."""
        return self.status.get(robot_id)


# Singleton instance
def get_navigation_service() -> AdvancedNavigationService:
    """Get AdvancedNavigationService singleton instance."""
    return AdvancedNavigationService()
