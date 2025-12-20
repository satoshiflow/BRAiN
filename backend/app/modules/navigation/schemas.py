"""
Advanced Navigation Schemas

Data models for social-aware navigation, dynamic obstacle avoidance,
and context-aware path planning.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class NavigationContext(str, Enum):
    """Environment context for navigation behavior adaptation."""
    HOSPITAL = "hospital"
    WAREHOUSE = "warehouse"
    OFFICE = "office"
    STREET = "street"
    MALL = "mall"
    FACTORY = "factory"
    HOME = "home"
    OUTDOOR = "outdoor"


class SocialZone(str, Enum):
    """Social distance zones (proxemics)."""
    INTIMATE = "intimate"      # 0-0.5m
    PERSONAL = "personal"      # 0.5-1.2m
    SOCIAL = "social"          # 1.2-3.6m
    PUBLIC = "public"          # 3.6m+


class ObstacleType(str, Enum):
    """Types of obstacles for navigation."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    HUMAN = "human"
    ROBOT = "robot"
    VEHICLE = "vehicle"
    UNKNOWN = "unknown"


class PathPlanningMode(str, Enum):
    """Path planning algorithms."""
    DIRECT = "direct"                    # Shortest path
    SOCIAL_AWARE = "social_aware"        # Respects social zones
    FORMATION = "formation"              # Multi-robot formation
    DYNAMIC_WINDOW = "dynamic_window"    # DWA for dynamic obstacles
    ELASTIC_BAND = "elastic_band"        # Elastic band smoothing
    RRT_STAR = "rrt_star"               # RRT* sampling-based


class NavigationBehavior(str, Enum):
    """Robot navigation behavior styles."""
    ASSERTIVE = "assertive"      # Prioritize efficiency
    CAUTIOUS = "cautious"        # Prioritize safety
    SOCIAL = "social"            # Prioritize human comfort
    BALANCED = "balanced"        # Balance all factors


class ObstacleAvoidanceStrategy(str, Enum):
    """Obstacle avoidance strategies."""
    STOP_AND_WAIT = "stop_and_wait"
    REPLAN = "replan"
    LOCAL_DEFORM = "local_deform"
    SOCIAL_FORCE = "social_force"


# ========== Core Models ==========

class Position2D(BaseModel):
    """2D position."""
    x: float
    y: float
    theta: Optional[float] = Field(None, description="Orientation in radians")


class Velocity2D(BaseModel):
    """2D velocity."""
    linear: float = Field(description="Linear velocity (m/s)")
    angular: float = Field(description="Angular velocity (rad/s)")


class Obstacle(BaseModel):
    """Dynamic or static obstacle."""
    obstacle_id: str
    obstacle_type: ObstacleType
    position: Position2D
    velocity: Optional[Velocity2D] = None
    radius: float = Field(gt=0.0, description="Obstacle radius (m)")
    uncertainty: Optional[float] = Field(None, ge=0.0, le=1.0, description="Detection confidence")

    # For human obstacles
    is_stationary: bool = False
    predicted_path: Optional[List[Position2D]] = None
    social_zone: Optional[SocialZone] = None


class NavigationGoal(BaseModel):
    """Navigation goal with constraints."""
    goal_id: str
    robot_id: str
    target_position: Position2D

    # Constraints
    max_velocity: float = Field(1.0, gt=0.0, description="Max linear velocity (m/s)")
    max_angular_velocity: float = Field(1.0, gt=0.0, description="Max angular velocity (rad/s)")
    goal_tolerance: float = Field(0.1, gt=0.0, description="Distance tolerance (m)")
    angle_tolerance: float = Field(0.1, gt=0.0, description="Angle tolerance (rad)")

    # Context
    navigation_context: NavigationContext = NavigationContext.WAREHOUSE
    behavior: NavigationBehavior = NavigationBehavior.BALANCED
    planning_mode: PathPlanningMode = PathPlanningMode.SOCIAL_AWARE

    # Social parameters
    min_human_distance: float = Field(1.5, gt=0.0, description="Minimum distance to humans (m)")
    min_robot_distance: float = Field(0.5, gt=0.0, description="Minimum distance to robots (m)")


class PathSegment(BaseModel):
    """Segment of a planned path."""
    position: Position2D
    velocity: Velocity2D
    timestamp: float
    curvature: Optional[float] = None


class PlannedPath(BaseModel):
    """Complete planned path."""
    path_id: str
    goal_id: str
    robot_id: str
    segments: List[PathSegment]
    total_distance: float = Field(ge=0.0)
    estimated_duration: float = Field(gt=0.0, description="Estimated duration (seconds)")
    social_cost: Optional[float] = Field(None, description="Social discomfort cost")
    safety_score: float = Field(ge=0.0, le=1.0, description="Path safety score")


class NavigationStatus(BaseModel):
    """Current navigation status."""
    robot_id: str
    goal_id: Optional[str] = None
    is_navigating: bool = False
    current_position: Position2D
    current_velocity: Velocity2D
    distance_to_goal: Optional[float] = None
    eta_seconds: Optional[float] = None
    obstacles_detected: int = 0
    replanning_count: int = 0
    last_update: float


class SocialNavigationParams(BaseModel):
    """Parameters for social-aware navigation."""
    # Personal space
    intimate_zone_radius: float = Field(0.5, gt=0.0, description="Intimate zone (m)")
    personal_zone_radius: float = Field(1.2, gt=0.0, description="Personal zone (m)")
    social_zone_radius: float = Field(3.6, gt=0.0, description="Social zone (m)")

    # Behavior weights
    efficiency_weight: float = Field(0.3, ge=0.0, le=1.0)
    safety_weight: float = Field(0.4, ge=0.0, le=1.0)
    comfort_weight: float = Field(0.3, ge=0.0, le=1.0)

    # Approach behavior
    approach_angle_deg: float = Field(45.0, description="Preferred approach angle to humans")
    passing_side_preference: str = Field("right", description="Preferred passing side")

    # Crowd handling
    max_crowd_density: float = Field(0.5, description="Max people per m²")
    crowd_avoidance_margin: float = Field(0.5, description="Extra margin in crowds (m)")


class FormationNavigationRequest(BaseModel):
    """Request for formation-based navigation."""
    formation_id: str
    robot_ids: List[str]
    leader_id: str
    target_position: Position2D
    formation_type: str = Field(description="Formation type (line, wedge, column, etc.)")
    inter_robot_distance: float = Field(1.0, gt=0.0, description="Distance between robots (m)")
    maintain_orientation: bool = True


class DynamicObstacleAvoidanceRequest(BaseModel):
    """Request for dynamic obstacle avoidance."""
    robot_id: str
    current_position: Position2D
    current_velocity: Velocity2D
    goal_position: Position2D
    detected_obstacles: List[Obstacle]
    avoidance_strategy: ObstacleAvoidanceStrategy = ObstacleAvoidanceStrategy.SOCIAL_FORCE
    prediction_horizon_s: float = Field(3.0, gt=0.0, description="Prediction time horizon")


class AvoidanceManeuver(BaseModel):
    """Computed avoidance maneuver."""
    maneuver_id: str
    robot_id: str
    recommended_velocity: Velocity2D
    duration_s: float
    safety_margin: float = Field(ge=0.0, description="Closest approach distance (m)")
    collision_risk: float = Field(ge=0.0, le=1.0, description="Collision risk score")
    maneuver_type: str  # "stop", "slow", "swerve_left", "swerve_right", "accelerate"


class ContextAdaptationRequest(BaseModel):
    """Request to adapt navigation to context."""
    robot_id: str
    navigation_context: NavigationContext
    detected_humans: int = 0
    crowd_density: float = Field(0.0, ge=0.0, description="People per m²")
    noise_level_db: Optional[float] = None
    lighting_level_lux: Optional[float] = None


class AdaptedNavigationParams(BaseModel):
    """Context-adapted navigation parameters."""
    context: NavigationContext
    max_velocity: float
    max_acceleration: float
    social_distance: float
    behavior: NavigationBehavior
    adaptations_applied: List[str] = Field(default_factory=list)
    reasoning: str = Field(description="Explanation of adaptations")
