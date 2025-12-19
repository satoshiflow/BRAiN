from datetime import datetime
from typing import Optional

from app.modules.karma.schemas import (
    KarmaMetrics,
    KarmaScore,
    RYRKarmaMetrics,
    RYRKarmaScore,
    FleetMetrics,
    SafetyMetrics,
    NavigationMetrics,
)
from app.modules.dna.core.service import DNAService


class KarmaService:
    """
    KARMA/BCQL Service for general agent performance scoring.
    Integrates with DNAService to persist karma scores.
    """

    def __init__(self, dna_service: DNAService) -> None:
        self._dna = dna_service

    def compute_score(self, agent_id: str, metrics: KarmaMetrics) -> KarmaScore:
        """
        Compute general agent karma score based on performance metrics.

        Scoring formula:
        - Success rate: 40 points max
        - Latency: 5 points max (better latency = higher score)
        - Policy violations: -10 points each
        - User rating: 8 points per star above neutral (3.0)
        - Credit consumption: -2 points per credit

        Total: 0-100 points
        """
        score = 0.0

        # Success rate (0-40 points)
        score += metrics.success_rate * 40.0

        # Latency (0-5 points, best if < 5s)
        score += max(0.0, 5.0 - (metrics.avg_latency_ms / 1000.0)) * 5.0

        # Policy violations (-10 per violation)
        score -= metrics.policy_violations * 10.0

        # User rating (neutral = 3.0, range: 0-5)
        score += (metrics.user_rating_avg - 3.0) * 8.0

        # Credit consumption (-2 per credit)
        score -= metrics.credit_consumption_per_task * 2.0

        # Clamp to 0-100
        score = max(0.0, min(100.0, score))

        # Update DNA
        self._dna.update_karma(agent_id, score)

        return KarmaScore(
            agent_id=agent_id,
            score=score,
            computed_at=datetime.utcnow(),
            details=metrics,
        )


class RYRKarmaService:
    """
    RYR-specific KARMA service for robot fleet performance scoring.
    Computes multi-dimensional scores for fleet coordination, safety, and navigation.
    """

    def __init__(self, dna_service: DNAService) -> None:
        self._dna = dna_service

    def compute_fleet_score(self, metrics: FleetMetrics) -> float:
        """
        Compute fleet coordination score (0-100).

        Weights:
        - Task distribution efficiency: 25 points
        - Collision avoidance: 25 points
        - Communication latency: 15 points (better = higher)
        - Cooperative tasks: 15 points
        - Resource sharing: 15 points
        - Idle time penalty: -5 points
        """
        score = 0.0

        # Task distribution (0-25)
        score += metrics.task_distribution_efficiency * 25.0

        # Collision avoidance (0-25)
        score += metrics.collision_avoidance_rate * 25.0

        # Communication latency (0-15, best if < 100ms)
        latency_score = max(0.0, 1.0 - (metrics.communication_latency_ms / 500.0))
        score += latency_score * 15.0

        # Cooperative tasks (0-15, normalized by active robots)
        if metrics.active_robots_count > 0:
            coop_efficiency = min(1.0, metrics.cooperative_tasks_completed / (metrics.active_robots_count * 10))
            score += coop_efficiency * 15.0

        # Resource sharing (0-15)
        score += metrics.resource_sharing_efficiency * 15.0

        # Idle time penalty (-5)
        score -= metrics.idle_time_percentage * 5.0

        return max(0.0, min(100.0, score))

    def compute_safety_score(self, metrics: SafetyMetrics) -> float:
        """
        Compute safety compliance score (0-100).

        Critical safety incidents heavily penalized.
        Weights:
        - Base score: 100
        - Safety incidents: -15 each
        - Near misses: -5 each
        - Emergency stops: -3 each
        - Zone violations: -8 each
        - Speed violations: -5 each
        - Obstacle detection rate: +20 points
        - Human proximity alerts: -2 each
        - Battery critical events: -4 each
        - Sensor failures: -6 each
        - Recovery rate: +10 points
        """
        score = 100.0

        # Penalties for safety issues
        score -= metrics.safety_incidents_count * 15.0
        score -= metrics.near_miss_count * 5.0
        score -= metrics.emergency_stops_count * 3.0
        score -= metrics.safety_zone_violations * 8.0
        score -= metrics.speed_limit_violations * 5.0
        score -= metrics.human_proximity_alerts * 2.0
        score -= metrics.battery_critical_events * 4.0
        score -= metrics.sensor_failure_count * 6.0

        # Bonuses for good performance
        score += metrics.obstacle_detection_rate * 20.0
        score += metrics.recovery_success_rate * 10.0

        return max(0.0, min(100.0, score))

    def compute_navigation_score(self, metrics: NavigationMetrics) -> float:
        """
        Compute navigation performance score (0-100).

        Weights:
        - Path planning success: 20 points
        - Path deviation: 15 points (lower = better)
        - Replanning frequency: 10 points (lower = better)
        - Goal accuracy: 15 points (lower = better)
        - Time efficiency: 20 points
        - Stuck recovery: 10 points (faster = better)
        - Localization accuracy: 5 points (lower = better)
        - Map coverage: 5 points
        """
        score = 0.0

        # Path planning success (0-20)
        score += metrics.path_planning_success_rate * 20.0

        # Path deviation (0-15, best if < 0.5m)
        deviation_score = max(0.0, 1.0 - (metrics.path_deviation_avg_m / 2.0))
        score += deviation_score * 15.0

        # Replanning frequency (0-10, best if < 1 per hour)
        replanning_score = max(0.0, 1.0 - (metrics.replanning_frequency / 5.0))
        score += replanning_score * 10.0

        # Goal reach accuracy (0-15, best if < 0.2m)
        goal_score = max(0.0, 1.0 - (metrics.goal_reach_accuracy_m / 1.0))
        score += goal_score * 15.0

        # Navigation time efficiency (0-20)
        score += metrics.navigation_time_efficiency * 20.0

        # Stuck recovery (0-10, best if < 5s)
        recovery_score = max(0.0, 1.0 - (metrics.stuck_recovery_time_avg_s / 30.0))
        score += recovery_score * 10.0

        # Localization accuracy (0-5, best if < 0.1m)
        localization_score = max(0.0, 1.0 - (metrics.localization_accuracy_m / 0.5))
        score += localization_score * 5.0

        # Map coverage (0-5)
        score += metrics.map_coverage_percentage * 5.0

        return max(0.0, min(100.0, score))

    def compute_ryr_score(
        self,
        agent_id: str,
        metrics: RYRKarmaMetrics,
        robot_id: Optional[str] = None,
        fleet_id: Optional[str] = None,
    ) -> RYRKarmaScore:
        """
        Compute comprehensive RYR karma score with multi-dimensional analysis.

        Returns detailed score breakdown with critical warnings and recommendations.
        """
        # Compute individual dimension scores
        fleet_score = self.compute_fleet_score(metrics.fleet)
        safety_score = self.compute_safety_score(metrics.safety)
        navigation_score = self.compute_navigation_score(metrics.navigation)

        # Compute overall score (weighted average)
        # Safety is most important (40%), followed by fleet (35%) and navigation (25%)
        overall_score = (
            safety_score * 0.40 +
            fleet_score * 0.35 +
            navigation_score * 0.25
        )

        # Generate critical warnings
        warnings = []
        if metrics.safety.safety_incidents_count > 0:
            warnings.append(f"⚠️ CRITICAL: {metrics.safety.safety_incidents_count} safety incident(s) detected")
        if metrics.safety.emergency_stops_count > 5:
            warnings.append(f"⚠️ HIGH: {metrics.safety.emergency_stops_count} emergency stops - investigate cause")
        if metrics.safety.battery_critical_events > 0:
            warnings.append(f"⚠️ Battery critical events: {metrics.safety.battery_critical_events}")
        if metrics.fleet.collision_avoidance_rate < 0.95:
            warnings.append(f"⚠️ Low collision avoidance rate: {metrics.fleet.collision_avoidance_rate:.1%}")
        if safety_score < 70.0:
            warnings.append("⛔ CRITICAL: Safety score below acceptable threshold (70)")

        # Generate recommendations
        recommendations = []
        if metrics.fleet.idle_time_percentage > 0.3:
            recommendations.append("Optimize task distribution to reduce idle time")
        if metrics.navigation.replanning_frequency > 3.0:
            recommendations.append("High replanning frequency - review path planning algorithms")
        if metrics.navigation.stuck_recovery_time_avg_s > 10.0:
            recommendations.append("Improve stuck recovery mechanisms (avg recovery time too high)")
        if metrics.fleet.communication_latency_ms > 200.0:
            recommendations.append("Communication latency high - check network infrastructure")
        if metrics.navigation.localization_accuracy_m > 0.2:
            recommendations.append("Improve localization accuracy (current: {:.2f}m)".format(metrics.navigation.localization_accuracy_m))

        # Update DNA with overall score
        self._dna.update_karma(agent_id, overall_score)

        return RYRKarmaScore(
            agent_id=agent_id,
            robot_id=robot_id,
            fleet_id=fleet_id,
            overall_score=overall_score,
            fleet_score=fleet_score,
            safety_score=safety_score,
            navigation_score=navigation_score,
            computed_at=datetime.utcnow(),
            metrics=metrics,
            critical_warnings=warnings,
            recommendations=recommendations,
        )
