"""Evolution Analyzer - System growth recommendations and trend analysis.

Implements Myzel-Hybrid-Charta principles:
- Passive observation (no forced evolution)
- Data-driven recommendations
- Human approval for structural changes
- Cooperation-based growth
- ML-based trend prediction (Phase 10)
"""

import logging
import math
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field

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

    # Phase 10: ML-based predictions
    predicted_value: Optional[float] = None  # Predicted next value
    confidence_interval: Optional[Tuple[float, float]] = None  # (lower, upper)
    anomaly_detected: bool = False


@dataclass
class TrendHistory:
    """Historical trend data for ML-based prediction (Phase 10)."""

    metric_name: str
    timestamps: List[datetime] = field(default_factory=list)
    values: List[float] = field(default_factory=list)
    max_history_size: int = 100  # Keep last 100 data points

    def add_data_point(self, timestamp: datetime, value: float):
        """Add data point to history."""
        self.timestamps.append(timestamp)
        self.values.append(value)

        # Trim if exceeds max size (keep most recent)
        if len(self.values) > self.max_history_size:
            self.timestamps = self.timestamps[-self.max_history_size:]
            self.values = self.values[-self.max_history_size:]


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
    - ML-based trend prediction (Phase 10)
    """

    # Trend analysis thresholds
    SIGNIFICANT_CHANGE_THRESHOLD = 0.15  # 15% change is significant
    TREND_LOOKBACK_HOURS = 24.0  # Analyze last 24 hours

    # Recommendation thresholds
    HIGH_UTILIZATION_THRESHOLD = 0.85  # 85% utilization -> consider adding capacity
    LOW_UTILIZATION_THRESHOLD = 0.30   # 30% utilization -> consider reducing capacity
    POOR_PERFORMANCE_THRESHOLD = 0.60  # Below 60% average score

    # Phase 10: ML prediction parameters
    ANOMALY_THRESHOLD_STDDEV = 2.0  # 2 standard deviations for anomaly detection
    PREDICTION_CONFIDENCE = 0.95  # 95% confidence interval

    def __init__(self, enable_ml_prediction: bool = True):
        self.trend_history: List[SystemTrend] = []
        self.recommendations: List[GrowthRecommendation] = []
        self.recommendation_counter = 0

        # Phase 10: Historical data for ML-based prediction
        self.enable_ml_prediction = enable_ml_prediction
        self.metric_histories: Dict[str, TrendHistory] = {}

        logger.info(f"[EvolutionAnalyzer] Initialized (ML prediction: {enable_ml_prediction})")

    def _calculate_statistics(self, values: List[float]) -> Tuple[float, float]:
        """Calculate mean and standard deviation.

        Args:
            values: List of numerical values

        Returns:
            (mean, std_dev) tuple
        """
        if not values:
            return 0.0, 0.0

        n = len(values)
        mean = sum(values) / n

        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)

        return mean, std_dev

    def _simple_linear_regression(self, x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
        """Simple linear regression: y = mx + b.

        Args:
            x_values: Independent variable (e.g., time indices)
            y_values: Dependent variable (e.g., metric values)

        Returns:
            (slope, intercept) tuple
        """
        if not x_values or not y_values or len(x_values) != len(y_values):
            return 0.0, 0.0

        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x_squared = sum(x ** 2 for x in x_values)

        # Avoid division by zero
        denominator = (n * sum_x_squared - sum_x ** 2)
        if abs(denominator) < 1e-10:
            return 0.0, sum_y / n if n > 0 else 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n

        return slope, intercept

    def _exponential_moving_average(self, values: List[float], alpha: float = 0.3) -> List[float]:
        """Calculate exponential moving average.

        Args:
            values: Time series data
            alpha: Smoothing factor (0.0-1.0), higher = more weight on recent values

        Returns:
            EMA values
        """
        if not values:
            return []

        ema = [values[0]]  # Initialize with first value

        for i in range(1, len(values)):
            ema_value = alpha * values[i] + (1 - alpha) * ema[-1]
            ema.append(ema_value)

        return ema

    def _detect_anomaly(self, value: float, history: List[float]) -> bool:
        """Detect if value is anomaly using statistical method.

        Args:
            value: Value to check
            history: Historical values for comparison

        Returns:
            True if anomaly detected
        """
        if len(history) < 3:
            return False  # Not enough data

        mean, std_dev = self._calculate_statistics(history)

        if std_dev < 1e-10:
            return False  # No variation

        # Z-score: number of standard deviations from mean
        z_score = abs(value - mean) / std_dev

        return z_score > self.ANOMALY_THRESHOLD_STDDEV

    def _predict_next_value(
        self,
        metric_name: str,
        current_value: float,
    ) -> Tuple[Optional[float], Optional[Tuple[float, float]], bool]:
        """Predict next value using ML-based forecasting (Phase 10).

        Uses simple linear regression on historical data.

        Args:
            metric_name: Metric identifier
            current_value: Current metric value

        Returns:
            (predicted_value, confidence_interval, anomaly_detected) tuple
        """
        if not self.enable_ml_prediction:
            return None, None, False

        # Get or create history
        if metric_name not in self.metric_histories:
            self.metric_histories[metric_name] = TrendHistory(metric_name=metric_name)

        history = self.metric_histories[metric_name]

        # Add current data point
        history.add_data_point(datetime.now(timezone.utc), current_value)

        # Need at least 3 data points for prediction
        if len(history.values) < 3:
            return None, None, False

        # Detect anomaly in current value
        anomaly_detected = self._detect_anomaly(current_value, history.values[:-1])

        # Use linear regression for prediction
        x_values = list(range(len(history.values)))  # Time indices
        y_values = history.values

        slope, intercept = self._simple_linear_regression(x_values, y_values)

        # Predict next value (next time index)
        next_x = len(x_values)
        predicted_value = slope * next_x + intercept

        # Calculate confidence interval using standard error
        # Simplified: mean absolute deviation * confidence factor
        residuals = [abs(y - (slope * x + intercept)) for x, y in zip(x_values, y_values)]
        mean_abs_error = sum(residuals) / len(residuals) if residuals else 0.0

        # 95% confidence interval approximation
        confidence_factor = 1.96  # For 95% confidence
        margin = mean_abs_error * confidence_factor

        confidence_interval = (
            max(0.0, predicted_value - margin),  # Lower bound (non-negative)
            predicted_value + margin,             # Upper bound
        )

        logger.debug(
            f"[EvolutionAnalyzer] ML prediction for {metric_name}: "
            f"predicted={predicted_value:.2f}, "
            f"CI=({confidence_interval[0]:.2f}, {confidence_interval[1]:.2f}), "
            f"anomaly={anomaly_detected}"
        )

        return predicted_value, confidence_interval, anomaly_detected

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
            current_value = ledger_stats.get("total_credits_allocated", 0.0)
            previous_value = current_value * 0.9  # Simulated historical data

            # Phase 10: ML-based prediction
            predicted_value, confidence_interval, anomaly_detected = self._predict_next_value(
                "credit_allocation_rate",
                current_value,
            )

            trend = SystemTrend(
                metric_name="credit_allocation_rate",
                time_period_hours=self.TREND_LOOKBACK_HOURS,
                current_value=current_value,
                previous_value=previous_value,
                change_percentage=10.0,  # Simulated
                direction=TrendDirection.IMPROVING,
                is_significant=False,
                # Phase 10: ML predictions
                predicted_value=predicted_value,
                confidence_interval=confidence_interval,
                anomaly_detected=anomaly_detected,
            )
            trends.append(trend)

        # Credit consumption trend
        if "total_credits_consumed" in ledger_stats:
            current = ledger_stats.get("total_credits_consumed", 0.0)
            previous = current * 0.95  # Simulated historical data
            change = ((current - previous) / previous * 100) if previous > 0 else 0.0

            # Phase 10: ML-based prediction
            predicted_value, confidence_interval, anomaly_detected = self._predict_next_value(
                "credit_consumption_rate",
                current,
            )

            trend = SystemTrend(
                metric_name="credit_consumption_rate",
                time_period_hours=self.TREND_LOOKBACK_HOURS,
                current_value=current,
                previous_value=previous,
                change_percentage=change,
                direction=TrendDirection.IMPROVING if change > 0 else TrendDirection.STABLE,
                is_significant=abs(change) > self.SIGNIFICANT_CHANGE_THRESHOLD * 100,
                # Phase 10: ML predictions
                predicted_value=predicted_value,
                confidence_interval=confidence_interval,
                anomaly_detected=anomaly_detected,
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

            # Phase 10: ML-based prediction
            predicted_value, confidence_interval, anomaly_detected = self._predict_next_value(
                "edge_of_chaos_score",
                eoc_score,
            )

            trend = SystemTrend(
                metric_name="edge_of_chaos_score",
                time_period_hours=self.TREND_LOOKBACK_HOURS,
                current_value=eoc_score,
                previous_value=optimal_center,  # Simulated
                change_percentage=(eoc_score - optimal_center) / optimal_center * 100,
                direction=direction,
                is_significant=distance_from_optimal > 0.15,
                # Phase 10: ML predictions
                predicted_value=predicted_value,
                confidence_interval=confidence_interval,
                anomaly_detected=anomaly_detected,
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
