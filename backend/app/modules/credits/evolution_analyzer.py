"""Evolution Analyzer - System growth recommendations and trend analysis.

Implements Myzel-Hybrid-Charta principles:
- Passive observation (no forced evolution)
- Data-driven recommendations
- Human approval for structural changes
- Cooperation-based growth
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class TrendDirection(str, Enum):
    """Trend direction."""

    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"
    UNKNOWN = "unknown"


class GrowthRecommendationType(str, Enum):
    """Growth recommendation types."""

    ADD_AGENT = "add_agent"                    # System needs more capacity
    REMOVE_AGENT = "remove_agent"              # Overcapacity detected
    SKILL_DEVELOPMENT = "skill_development"    # Agent needs training
    WORKLOAD_REDISTRIBUTION = "workload_redistribution"  # Balance workload
    COLLABORATION_IMPROVEMENT = "collaboration_improvement"  # Improve teamwork
    CREDIT_ADJUSTMENT = "credit_adjustment"    # Adjust credit allocations
    NONE = "none"                              # No action needed


@dataclass
class SystemTrend:
    """System trend analysis."""

    metric_name: str
    time_period_hours: float
    current_value: float
    previous_value: float
    change_percentage: float
    direction: TrendDirection
    is_significant: bool  # Is the change statistically significant?


@dataclass
class GrowthRecommendation:
    """Growth recommendation."""

    recommendation_id: str
    recommendation_type: GrowthRecommendationType
    priority: int  # 1-10
    title: str
    description: str
    reasoning: str
    expected_impact: str
    requires_human_approval: bool
    conditions: List[str]  # Conditions that must be met
    risks: List[str]  # Potential risks
    created_at: datetime


class EvolutionAnalyzer:
    """Analyzes system evolution and provides growth recommendations.

    Myzel-Hybrid Principles:
    - Passive observation (trend analysis, not forced changes)
    - Human oversight for structural decisions
    - Cooperation-based recommendations
    - Fail-closed (conservative recommendations)
    """

    # Trend analysis thresholds
    SIGNIFICANT_CHANGE_THRESHOLD = 0.15  # 15% change is significant
    TREND_LOOKBACK_HOURS = 24.0  # Analyze last 24 hours

    # Recommendation thresholds
    HIGH_UTILIZATION_THRESHOLD = 0.85  # 85% utilization -> consider adding capacity
    LOW_UTILIZATION_THRESHOLD = 0.30   # 30% utilization -> consider reducing capacity
    POOR_PERFORMANCE_THRESHOLD = 0.60  # Below 60% average score

    def __init__(self):
        self.trend_history: List[SystemTrend] = []
        self.recommendations: List[GrowthRecommendation] = []
        self.recommendation_counter = 0

        logger.info("[EvolutionAnalyzer] Initialized")

    async def analyze_system_evolution(
        self,
        system_metrics: Dict,
        ledger_stats: Dict,
        agent_stats: List[Dict],
    ) -> Dict:
        """Analyze system evolution and generate recommendations.

        Args:
            system_metrics: Current system metrics (from RuntimeAuditor/SystemHealth)
            ledger_stats: Credit ledger statistics
            agent_stats: List of agent statistics (from MissionRatingSystem)

        Returns:
            Analysis result with trends and recommendations
        """
        analysis = {
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "trends": [],
            "recommendations": [],
            "overall_health": "unknown",
        }

        # Analyze trends
        trends = await self._analyze_trends(system_metrics, ledger_stats)
        analysis["trends"] = trends
        self.trend_history.extend(trends)

        # Generate recommendations based on trends and agent stats
        recommendations = await self._generate_recommendations(
            trends=trends,
            system_metrics=system_metrics,
            agent_stats=agent_stats,
        )
        analysis["recommendations"] = recommendations
        self.recommendations.extend(recommendations)

        # Determine overall health
        analysis["overall_health"] = self._determine_overall_health(trends)

        logger.info(
            f"[EvolutionAnalyzer] Analysis complete: {len(trends)} trends, "
            f"{len(recommendations)} recommendations, health={analysis['overall_health']}"
        )

        return analysis

    async def _analyze_trends(
        self,
        system_metrics: Dict,
        ledger_stats: Dict,
    ) -> List[SystemTrend]:
        """Analyze system trends.

        Args:
            system_metrics: Current system metrics
            ledger_stats: Credit ledger statistics

        Returns:
            List of identified trends
        """
        trends = []

        # Credit allocation trend
        if "total_credits_allocated" in ledger_stats:
            # TODO: Compare with historical data (requires persistence)
            # For now, we'll create a placeholder trend
            trend = SystemTrend(
                metric_name="credit_allocation_rate",
                time_period_hours=self.TREND_LOOKBACK_HOURS,
                current_value=ledger_stats.get("total_credits_allocated", 0.0),
                previous_value=ledger_stats.get("total_credits_allocated", 0.0) * 0.9,  # Simulated
                change_percentage=10.0,  # Simulated
                direction=TrendDirection.IMPROVING,
                is_significant=False,
            )
            trends.append(trend)

        # Credit consumption trend
        if "total_credits_consumed" in ledger_stats:
            current = ledger_stats.get("total_credits_consumed", 0.0)
            previous = current * 0.95  # Simulated historical data
            change = ((current - previous) / previous * 100) if previous > 0 else 0.0

            trend = SystemTrend(
                metric_name="credit_consumption_rate",
                time_period_hours=self.TREND_LOOKBACK_HOURS,
                current_value=current,
                previous_value=previous,
                change_percentage=change,
                direction=TrendDirection.IMPROVING if change > 0 else TrendDirection.STABLE,
                is_significant=abs(change) > self.SIGNIFICANT_CHANGE_THRESHOLD * 100,
            )
            trends.append(trend)

        # Edge-of-Chaos trend (if available in system_metrics)
        if "edge_of_chaos_score" in system_metrics:
            eoc_score = system_metrics["edge_of_chaos_score"]
            # Determine direction based on distance from optimal (0.5-0.7)
            optimal_center = 0.6
            distance_from_optimal = abs(eoc_score - optimal_center)

            if distance_from_optimal < 0.1:
                direction = TrendDirection.STABLE
            elif eoc_score < optimal_center:
                direction = TrendDirection.DECLINING  # Too ordered
            else:
                direction = TrendDirection.IMPROVING  # Moving toward chaos (activity)

            trend = SystemTrend(
                metric_name="edge_of_chaos_score",
                time_period_hours=self.TREND_LOOKBACK_HOURS,
                current_value=eoc_score,
                previous_value=optimal_center,  # Simulated
                change_percentage=(eoc_score - optimal_center) / optimal_center * 100,
                direction=direction,
                is_significant=distance_from_optimal > 0.15,
            )
            trends.append(trend)

        return trends

    async def _generate_recommendations(
        self,
        trends: List[SystemTrend],
        system_metrics: Dict,
        agent_stats: List[Dict],
    ) -> List[GrowthRecommendation]:
        """Generate growth recommendations.

        Args:
            trends: System trends
            system_metrics: Current system metrics
            agent_stats: Agent statistics

        Returns:
            List of recommendations
        """
        recommendations = []

        # Check agent utilization
        if agent_stats:
            avg_utilization = self._calculate_average_utilization(agent_stats)

            if avg_utilization > self.HIGH_UTILIZATION_THRESHOLD:
                # High utilization → consider adding capacity
                rec = self._create_recommendation(
                    recommendation_type=GrowthRecommendationType.ADD_AGENT,
                    priority=8,
                    title="High agent utilization detected",
                    description=f"Average agent utilization is {avg_utilization * 100:.1f}%",
                    reasoning=(
                        f"Agent utilization ({avg_utilization * 100:.1f}%) exceeds threshold "
                        f"({self.HIGH_UTILIZATION_THRESHOLD * 100:.1f}%). Consider adding agents to improve responsiveness."
                    ),
                    expected_impact="Reduced mission queue depth, faster mission execution",
                    requires_human_approval=True,
                    conditions=[
                        "Sustained high utilization for at least 1 hour",
                        "Mission queue depth > 10",
                        "No recent agent additions (last 24h)",
                    ],
                    risks=[
                        "Increased resource consumption",
                        "Potential coordination overhead",
                    ],
                )
                recommendations.append(rec)

            elif avg_utilization < self.LOW_UTILIZATION_THRESHOLD:
                # Low utilization → consider reducing capacity
                rec = self._create_recommendation(
                    recommendation_type=GrowthRecommendationType.REMOVE_AGENT,
                    priority=5,
                    title="Low agent utilization detected",
                    description=f"Average agent utilization is {avg_utilization * 100:.1f}%",
                    reasoning=(
                        f"Agent utilization ({avg_utilization * 100:.1f}%) below threshold "
                        f"({self.LOW_UTILIZATION_THRESHOLD * 100:.1f}%). Consider reducing agent count to improve efficiency."
                    ),
                    expected_impact="Reduced resource consumption, improved cost efficiency",
                    requires_human_approval=True,
                    conditions=[
                        "Sustained low utilization for at least 4 hours",
                        "Mission queue depth < 3",
                        "At least 3 agents currently active",
                    ],
                    risks=[
                        "Reduced capacity for workload spikes",
                        "Potential mission delays",
                    ],
                )
                recommendations.append(rec)

        # Check agent performance
        if agent_stats:
            poor_performers = [
                agent for agent in agent_stats
                if agent.get("average_score", 1.0) < self.POOR_PERFORMANCE_THRESHOLD
            ]

            if poor_performers:
                for agent in poor_performers:
                    rec = self._create_recommendation(
                        recommendation_type=GrowthRecommendationType.SKILL_DEVELOPMENT,
                        priority=7,
                        title=f"Agent {agent['agent_id']} needs skill development",
                        description=f"Average performance score: {agent.get('average_score', 0.0) * 100:.1f}%",
                        reasoning=(
                            f"Agent {agent['agent_id']} has average score "
                            f"{agent.get('average_score', 0.0) * 100:.1f}% below threshold "
                            f"({self.POOR_PERFORMANCE_THRESHOLD * 100:.1f}%). "
                            f"Consider skill development or task reassignment."
                        ),
                        expected_impact="Improved mission success rate, better resource utilization",
                        requires_human_approval=False,
                        conditions=[
                            "At least 5 completed missions",
                            "Consistent poor performance over 3+ missions",
                        ],
                        risks=[
                            "Training time reduces short-term capacity",
                        ],
                    )
                    recommendations.append(rec)

        # Check Edge-of-Chaos trends
        eoc_trends = [t for t in trends if t.metric_name == "edge_of_chaos_score"]
        if eoc_trends:
            eoc_trend = eoc_trends[0]

            if eoc_trend.current_value < 0.5 and eoc_trend.direction == TrendDirection.DECLINING:
                rec = self._create_recommendation(
                    recommendation_type=GrowthRecommendationType.WORKLOAD_REDISTRIBUTION,
                    priority=6,
                    title="System too ordered - increase activity",
                    description=f"Edge-of-Chaos score: {eoc_trend.current_value:.3f} (optimal: 0.5-0.7)",
                    reasoning=(
                        "System is too ordered (rigid). Consider redistributing workload "
                        "to increase agent activity and improve system dynamics."
                    ),
                    expected_impact="Improved system responsiveness, better Edge-of-Chaos balance",
                    requires_human_approval=False,
                    conditions=[
                        "Edge-of-Chaos score < 0.5 for at least 30 minutes",
                        "No critical system issues",
                    ],
                    risks=[
                        "Temporary increase in resource consumption",
                    ],
                )
                recommendations.append(rec)

        return recommendations

    def _calculate_average_utilization(self, agent_stats: List[Dict]) -> float:
        """Calculate average agent utilization.

        Args:
            agent_stats: List of agent statistics

        Returns:
            Average utilization (0.0-1.0)
        """
        if not agent_stats:
            return 0.0

        # Utilization proxy: success_rate * (completed_missions / total_missions)
        utilizations = []
        for agent in agent_stats:
            total = agent.get("total_missions", 0)
            completed = agent.get("completed_missions", 0)
            success_rate = agent.get("success_rate", 0.0)

            if total > 0:
                utilization = (completed / total) * success_rate
                utilizations.append(utilization)

        return sum(utilizations) / len(utilizations) if utilizations else 0.0

    def _create_recommendation(
        self,
        recommendation_type: GrowthRecommendationType,
        priority: int,
        title: str,
        description: str,
        reasoning: str,
        expected_impact: str,
        requires_human_approval: bool,
        conditions: List[str],
        risks: List[str],
    ) -> GrowthRecommendation:
        """Create growth recommendation.

        Args:
            recommendation_type: Type of recommendation
            priority: Priority (1-10)
            title: Recommendation title
            description: Short description
            reasoning: Detailed reasoning
            expected_impact: Expected impact
            requires_human_approval: Requires human approval flag
            conditions: Conditions that must be met
            risks: Potential risks

        Returns:
            GrowthRecommendation instance
        """
        self.recommendation_counter += 1
        recommendation_id = f"REC_{self.recommendation_counter:06d}"

        return GrowthRecommendation(
            recommendation_id=recommendation_id,
            recommendation_type=recommendation_type,
            priority=priority,
            title=title,
            description=description,
            reasoning=reasoning,
            expected_impact=expected_impact,
            requires_human_approval=requires_human_approval,
            conditions=conditions,
            risks=risks,
            created_at=datetime.now(timezone.utc),
        )

    def _determine_overall_health(self, trends: List[SystemTrend]) -> str:
        """Determine overall system health based on trends.

        Args:
            trends: System trends

        Returns:
            Health status string
        """
        if not trends:
            return "unknown"

        improving_count = len([t for t in trends if t.direction == TrendDirection.IMPROVING])
        declining_count = len([t for t in trends if t.direction == TrendDirection.DECLINING])

        if improving_count > declining_count:
            return "healthy"
        elif declining_count > improving_count:
            return "degraded"
        else:
            return "stable"

    def get_recent_recommendations(
        self,
        limit: int = 10,
        requires_approval_only: bool = False,
    ) -> List[GrowthRecommendation]:
        """Get recent recommendations.

        Args:
            limit: Maximum number of recommendations
            requires_approval_only: Only return recommendations requiring human approval

        Returns:
            List of recommendations (newest first)
        """
        recs = self.recommendations

        if requires_approval_only:
            recs = [r for r in recs if r.requires_human_approval]

        return list(reversed(recs[-limit:]))


# Global evolution analyzer instance
_evolution_analyzer: Optional[EvolutionAnalyzer] = None


def get_evolution_analyzer() -> EvolutionAnalyzer:
    """Get global evolution analyzer instance.

    Returns:
        EvolutionAnalyzer instance
    """
    global _evolution_analyzer
    if _evolution_analyzer is None:
        _evolution_analyzer = EvolutionAnalyzer()
    return _evolution_analyzer
