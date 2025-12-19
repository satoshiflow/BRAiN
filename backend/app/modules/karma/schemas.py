from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================================
# BASE METRICS (General Agent Metrics)
# ============================================================================

class KarmaMetrics(BaseModel):
    """General agent performance metrics."""
    success_rate: float = Field(ge=0.0, le=1.0, description="Success rate (0.0-1.0)")
    avg_latency_ms: float = Field(ge=0.0, description="Average latency in milliseconds")
    policy_violations: int = Field(ge=0, description="Number of policy violations")
    user_rating_avg: float = Field(ge=0.0, le=5.0, description="User rating (0-5)")
    credit_consumption_per_task: float = Field(ge=0.0, description="Credits consumed per task")


class KarmaScore(BaseModel):
    """Agent karma score with metrics."""
    agent_id: str
    score: float = Field(ge=0.0, le=100.0, description="Karma score (0-100)")
    computed_at: datetime
    details: KarmaMetrics


# ============================================================================
# RYR-SPECIFIC METRICS (Robot Your Robot Integration)
# ============================================================================

class FleetMetrics(BaseModel):
    """Fleet coordination and collaboration metrics for RYR robots."""

    # Coordination
    task_distribution_efficiency: float = Field(
        ge=0.0, le=1.0,
        description="How efficiently tasks are distributed across fleet (0.0-1.0)"
    )
    collision_avoidance_rate: float = Field(
        ge=0.0, le=1.0,
        description="Successful collision avoidances (0.0-1.0)"
    )
    communication_latency_ms: float = Field(
        ge=0.0,
        description="Average inter-robot communication latency in ms"
    )

    # Collaboration
    cooperative_tasks_completed: int = Field(
        ge=0,
        description="Number of tasks completed cooperatively"
    )
    resource_sharing_efficiency: float = Field(
        ge=0.0, le=1.0,
        description="How efficiently resources are shared (0.0-1.0)"
    )

    # Fleet Health
    active_robots_count: int = Field(ge=0, description="Number of active robots in fleet")
    idle_time_percentage: float = Field(
        ge=0.0, le=1.0,
        description="Percentage of time robots are idle (0.0-1.0)"
    )


class SafetyMetrics(BaseModel):
    """Safety and compliance metrics for RYR robots."""

    # Safety Incidents
    safety_incidents_count: int = Field(ge=0, description="Number of safety incidents")
    near_miss_count: int = Field(ge=0, description="Number of near-miss events")
    emergency_stops_count: int = Field(ge=0, description="Number of emergency stops")

    # Compliance
    safety_zone_violations: int = Field(ge=0, description="Safety zone boundary violations")
    speed_limit_violations: int = Field(ge=0, description="Speed limit violations")
    obstacle_detection_rate: float = Field(
        ge=0.0, le=1.0,
        description="Successful obstacle detections (0.0-1.0)"
    )

    # Environmental Awareness
    human_proximity_alerts: int = Field(ge=0, description="Alerts for human proximity")
    battery_critical_events: int = Field(ge=0, description="Critical battery level events")
    sensor_failure_count: int = Field(ge=0, description="Sensor failure occurrences")

    # Recovery
    recovery_success_rate: float = Field(
        ge=0.0, le=1.0,
        description="Successful recovery from errors (0.0-1.0)"
    )


class NavigationMetrics(BaseModel):
    """Navigation and path planning metrics for RYR robots."""

    # Path Planning
    path_planning_success_rate: float = Field(
        ge=0.0, le=1.0,
        description="Successful path planning attempts (0.0-1.0)"
    )
    path_deviation_avg_m: float = Field(
        ge=0.0,
        description="Average path deviation in meters"
    )
    replanning_frequency: float = Field(
        ge=0.0,
        description="Path replanning frequency (per hour)"
    )

    # Navigation Efficiency
    goal_reach_accuracy_m: float = Field(
        ge=0.0,
        description="Average distance from goal on arrival (meters)"
    )
    navigation_time_efficiency: float = Field(
        ge=0.0, le=1.0,
        description="Actual time vs. optimal time ratio (0.0-1.0)"
    )
    stuck_recovery_time_avg_s: float = Field(
        ge=0.0,
        description="Average time to recover from stuck state (seconds)"
    )

    # Localization
    localization_accuracy_m: float = Field(
        ge=0.0,
        description="Average localization accuracy in meters"
    )
    map_coverage_percentage: float = Field(
        ge=0.0, le=1.0,
        description="Percentage of environment mapped (0.0-1.0)"
    )


class RYRKarmaMetrics(BaseModel):
    """Combined RYR-specific karma metrics."""
    fleet: FleetMetrics
    safety: SafetyMetrics
    navigation: NavigationMetrics


class RYRKarmaScore(BaseModel):
    """RYR-specific karma score with detailed breakdown."""
    agent_id: str
    robot_id: Optional[str] = None
    fleet_id: Optional[str] = None

    # Overall Scores
    overall_score: float = Field(ge=0.0, le=100.0, description="Overall karma score (0-100)")
    fleet_score: float = Field(ge=0.0, le=100.0, description="Fleet coordination score (0-100)")
    safety_score: float = Field(ge=0.0, le=100.0, description="Safety compliance score (0-100)")
    navigation_score: float = Field(ge=0.0, le=100.0, description="Navigation performance score (0-100)")

    # Metadata
    computed_at: datetime
    metrics: RYRKarmaMetrics

    # Warnings/Alerts
    critical_warnings: list[str] = Field(default_factory=list, description="Critical safety warnings")
    recommendations: list[str] = Field(default_factory=list, description="Performance improvement recommendations")