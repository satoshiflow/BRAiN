"""
Predictive Maintenance Service

Business logic for health monitoring, anomaly detection, failure prediction,
and maintenance scheduling.
"""

from typing import Dict, List, Optional
import time
from collections import defaultdict
import math

from .schemas import (
    HealthMetrics,
    AnomalyDetection,
    AnomalySeverity,
    AnomalyType,
    FailurePrediction,
    MaintenanceSchedule,
    MaintenanceStatus,
    MaintenanceType,
    ComponentType,
    ComponentHealthSummary,
    MaintenanceAnalyticsResponse,
)


class PredictiveMaintenanceService:
    """
    Service for predictive maintenance operations.

    Provides health monitoring, anomaly detection, failure prediction,
    and intelligent maintenance scheduling for robot fleets.
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

        # In-memory storage (production: use database)
        self.health_metrics: Dict[str, List[HealthMetrics]] = defaultdict(list)  # component_id -> metrics
        self.anomalies: Dict[str, AnomalyDetection] = {}  # anomaly_id -> anomaly
        self.predictions: Dict[str, FailurePrediction] = {}  # prediction_id -> prediction
        self.schedules: Dict[str, MaintenanceSchedule] = {}  # schedule_id -> schedule

        # Baselines for anomaly detection (component_id -> metric -> baseline)
        self.baselines: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Thresholds for anomaly detection
        self.thresholds = {
            "temperature_max_c": 80.0,
            "vibration_max": 10.0,
            "health_score_min": 60.0,
            "deviation_threshold_percent": 20.0,
        }

        self._initialized = True

    # ========== Health Monitoring ==========

    def record_health_metrics(self, metrics: HealthMetrics) -> HealthMetrics:
        """
        Record health metrics for a component.

        Automatically triggers anomaly detection and updates baselines.
        """
        # Store metrics
        self.health_metrics[metrics.component_id].append(metrics)

        # Keep only last 1000 readings per component
        if len(self.health_metrics[metrics.component_id]) > 1000:
            self.health_metrics[metrics.component_id] = \
                self.health_metrics[metrics.component_id][-1000:]

        # Update baseline if healthy
        if metrics.health_score >= self.thresholds["health_score_min"]:
            self._update_baseline(metrics)

        # Check for anomalies
        self._detect_anomalies(metrics)

        return metrics

    def get_health_metrics(
        self,
        component_id: Optional[str] = None,
        robot_id: Optional[str] = None,
        limit: int = 100
    ) -> List[HealthMetrics]:
        """Get health metrics history."""
        if component_id:
            return self.health_metrics[component_id][-limit:]

        # Filter by robot_id
        if robot_id:
            all_metrics = []
            for metrics_list in self.health_metrics.values():
                all_metrics.extend([m for m in metrics_list if m.robot_id == robot_id])
            return sorted(all_metrics, key=lambda m: m.timestamp, reverse=True)[:limit]

        # Return all (latest first)
        all_metrics = []
        for metrics_list in self.health_metrics.values():
            all_metrics.extend(metrics_list)
        return sorted(all_metrics, key=lambda m: m.timestamp, reverse=True)[:limit]

    def _update_baseline(self, metrics: HealthMetrics):
        """Update baseline values for anomaly detection (exponential moving average)."""
        alpha = 0.1  # Smoothing factor

        component_baseline = self.baselines[metrics.component_id]

        if metrics.temperature_c is not None:
            old_val = component_baseline.get("temperature_c", metrics.temperature_c)
            component_baseline["temperature_c"] = alpha * metrics.temperature_c + (1 - alpha) * old_val

        if metrics.vibration_level is not None:
            old_val = component_baseline.get("vibration_level", metrics.vibration_level)
            component_baseline["vibration_level"] = alpha * metrics.vibration_level + (1 - alpha) * old_val

        if metrics.power_consumption_w is not None:
            old_val = component_baseline.get("power_consumption_w", metrics.power_consumption_w)
            component_baseline["power_consumption_w"] = alpha * metrics.power_consumption_w + (1 - alpha) * old_val

    # ========== Anomaly Detection ==========

    def _detect_anomalies(self, metrics: HealthMetrics):
        """
        Detect anomalies in health metrics.

        Uses threshold-based and statistical deviation methods.
        """
        anomalies_detected = []

        # Temperature anomaly
        if metrics.temperature_c and metrics.temperature_c > self.thresholds["temperature_max_c"]:
            anomaly = AnomalyDetection(
                anomaly_id=f"anomaly_{metrics.component_id}_{int(time.time())}",
                robot_id=metrics.robot_id,
                component_id=metrics.component_id,
                component_type=metrics.component_type,
                anomaly_type=AnomalyType.TEMPERATURE_SPIKE,
                severity=self._calculate_severity(
                    metrics.temperature_c,
                    self.thresholds["temperature_max_c"]
                ),
                detected_at=metrics.timestamp,
                anomaly_score=min(metrics.temperature_c / self.thresholds["temperature_max_c"], 1.0),
                current_value=metrics.temperature_c,
                baseline_value=self.thresholds["temperature_max_c"],
                description=f"Temperature {metrics.temperature_c}°C exceeds threshold {self.thresholds['temperature_max_c']}°C",
                recommended_action="Check cooling system and reduce load",
            )
            anomalies_detected.append(anomaly)

        # Vibration anomaly
        if metrics.vibration_level and metrics.vibration_level > self.thresholds["vibration_max"]:
            anomaly = AnomalyDetection(
                anomaly_id=f"anomaly_{metrics.component_id}_{int(time.time())}_vib",
                robot_id=metrics.robot_id,
                component_id=metrics.component_id,
                component_type=metrics.component_type,
                anomaly_type=AnomalyType.VIBRATION_ANOMALY,
                severity=self._calculate_severity(
                    metrics.vibration_level,
                    self.thresholds["vibration_max"]
                ),
                detected_at=metrics.timestamp,
                anomaly_score=min(metrics.vibration_level / self.thresholds["vibration_max"], 1.0),
                current_value=metrics.vibration_level,
                baseline_value=self.thresholds["vibration_max"],
                description=f"Vibration level {metrics.vibration_level} exceeds threshold {self.thresholds['vibration_max']}",
                recommended_action="Inspect mechanical components and alignment",
            )
            anomalies_detected.append(anomaly)

        # Statistical deviation anomaly
        baseline = self.baselines.get(metrics.component_id, {})
        if baseline:
            for metric_name, current_value in [
                ("temperature_c", metrics.temperature_c),
                ("power_consumption_w", metrics.power_consumption_w),
            ]:
                if current_value is None:
                    continue

                baseline_value = baseline.get(metric_name)
                if baseline_value is None or baseline_value == 0:
                    continue

                deviation_pct = abs((current_value - baseline_value) / baseline_value) * 100

                if deviation_pct > self.thresholds["deviation_threshold_percent"]:
                    anomaly = AnomalyDetection(
                        anomaly_id=f"anomaly_{metrics.component_id}_{int(time.time())}_{metric_name}",
                        robot_id=metrics.robot_id,
                        component_id=metrics.component_id,
                        component_type=metrics.component_type,
                        anomaly_type=AnomalyType.PERFORMANCE_DEGRADATION,
                        severity=AnomalySeverity.MEDIUM,
                        detected_at=metrics.timestamp,
                        anomaly_score=min(deviation_pct / 100, 1.0),
                        current_value=current_value,
                        baseline_value=baseline_value,
                        deviation_percentage=deviation_pct,
                        description=f"{metric_name} deviated {deviation_pct:.1f}% from baseline",
                        recommended_action="Monitor closely and schedule inspection",
                    )
                    anomalies_detected.append(anomaly)

        # Store detected anomalies
        for anomaly in anomalies_detected:
            self.anomalies[anomaly.anomaly_id] = anomaly

    def _calculate_severity(self, value: float, threshold: float) -> AnomalySeverity:
        """Calculate anomaly severity based on threshold exceedance."""
        ratio = value / threshold
        if ratio >= 1.5:
            return AnomalySeverity.CRITICAL
        elif ratio >= 1.3:
            return AnomalySeverity.HIGH
        elif ratio >= 1.1:
            return AnomalySeverity.MEDIUM
        else:
            return AnomalySeverity.LOW

    def get_anomalies(
        self,
        robot_id: Optional[str] = None,
        severity: Optional[AnomalySeverity] = None,
        acknowledged: Optional[bool] = None
    ) -> List[AnomalyDetection]:
        """Get detected anomalies with optional filtering."""
        anomalies = list(self.anomalies.values())

        if robot_id:
            anomalies = [a for a in anomalies if a.robot_id == robot_id]
        if severity:
            anomalies = [a for a in anomalies if a.severity == severity]
        if acknowledged is not None:
            anomalies = [a for a in anomalies if a.acknowledged == acknowledged]

        return sorted(anomalies, key=lambda a: a.detected_at, reverse=True)

    def acknowledge_anomaly(self, anomaly_id: str) -> Optional[AnomalyDetection]:
        """Acknowledge an anomaly."""
        anomaly = self.anomalies.get(anomaly_id)
        if anomaly:
            anomaly.acknowledged = True
        return anomaly

    # ========== Failure Prediction ==========

    def predict_failure(self, component_id: str) -> Optional[FailurePrediction]:
        """
        Predict component failure using health metrics trends.

        Uses simple trend analysis (production: use ML models like LSTM, survival analysis).
        """
        metrics_history = self.health_metrics.get(component_id, [])
        if len(metrics_history) < 10:
            return None  # Not enough data

        # Analyze health score trend
        recent_metrics = metrics_history[-20:]
        health_scores = [m.health_score for m in recent_metrics]

        # Calculate trend (linear regression slope)
        n = len(health_scores)
        x = list(range(n))
        x_mean = sum(x) / n
        y_mean = sum(health_scores) / n

        numerator = sum((x[i] - x_mean) * (health_scores[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator

        # If declining trend, predict failure
        if slope < -0.5:  # Health declining
            current_health = health_scores[-1]
            failure_threshold = 20.0  # Health score below which component is considered failed

            if current_health <= failure_threshold:
                time_to_failure_hours = 0.0
                failure_probability = 1.0
            else:
                # Estimate time to failure
                health_decline_per_hour = abs(slope) * 0.1  # Rough estimate
                time_to_failure_hours = (current_health - failure_threshold) / health_decline_per_hour
                failure_probability = min(0.3 + (100 - current_health) / 100, 0.95)

            latest_metric = recent_metrics[-1]
            prediction = FailurePrediction(
                prediction_id=f"pred_{component_id}_{int(time.time())}",
                robot_id=latest_metric.robot_id,
                component_id=component_id,
                component_type=latest_metric.component_type,
                failure_probability=failure_probability,
                predicted_failure_time=time.time() + (time_to_failure_hours * 3600),
                time_to_failure_hours=time_to_failure_hours,
                confidence_score=0.75,  # Mock confidence
                root_cause="Declining health trend detected",
                contributing_factors=["Continuous degradation", "High operating hours"],
                recommended_actions=[
                    "Schedule immediate inspection",
                    "Prepare replacement parts",
                    "Monitor closely"
                ],
                estimated_downtime_hours=2.0,
            )

            self.predictions[prediction.prediction_id] = prediction
            return prediction

        return None

    def get_predictions(
        self,
        robot_id: Optional[str] = None,
        min_probability: float = 0.0
    ) -> List[FailurePrediction]:
        """Get failure predictions."""
        predictions = list(self.predictions.values())

        if robot_id:
            predictions = [p for p in predictions if p.robot_id == robot_id]

        predictions = [p for p in predictions if p.failure_probability >= min_probability]

        return sorted(predictions, key=lambda p: p.failure_probability, reverse=True)

    # ========== Maintenance Scheduling ==========

    def schedule_maintenance(self, schedule: MaintenanceSchedule) -> MaintenanceSchedule:
        """Schedule a maintenance task."""
        self.schedules[schedule.schedule_id] = schedule
        return schedule

    def get_maintenance_schedules(
        self,
        robot_id: Optional[str] = None,
        status: Optional[MaintenanceStatus] = None
    ) -> List[MaintenanceSchedule]:
        """Get maintenance schedules."""
        schedules = list(self.schedules.values())

        if robot_id:
            schedules = [s for s in schedules if s.robot_id == robot_id]
        if status:
            schedules = [s for s in schedules if s.status == status]

        # Check for overdue
        current_time = time.time()
        for schedule in schedules:
            if (schedule.status == MaintenanceStatus.SCHEDULED and
                schedule.scheduled_time < current_time):
                schedule.status = MaintenanceStatus.OVERDUE

        return sorted(schedules, key=lambda s: s.scheduled_time)

    def update_maintenance_status(
        self,
        schedule_id: str,
        status: MaintenanceStatus,
        completion_notes: Optional[str] = None
    ) -> Optional[MaintenanceSchedule]:
        """Update maintenance task status."""
        schedule = self.schedules.get(schedule_id)
        if not schedule:
            return None

        schedule.status = status

        if status == MaintenanceStatus.COMPLETED:
            schedule.completed_at = time.time()
            if schedule.completion_notes is None:
                schedule.completion_notes = completion_notes

        return schedule

    # ========== Analytics ==========

    def get_analytics(
        self,
        robot_ids: Optional[List[str]] = None,
        component_types: Optional[List[ComponentType]] = None
    ) -> MaintenanceAnalyticsResponse:
        """Get maintenance analytics."""
        # Collect all latest metrics
        all_latest_metrics = []
        for component_id, metrics_list in self.health_metrics.items():
            if metrics_list:
                latest = metrics_list[-1]
                if robot_ids and latest.robot_id not in robot_ids:
                    continue
                if component_types and latest.component_type not in component_types:
                    continue
                all_latest_metrics.append(latest)

        # Calculate component summaries
        summaries: Dict[ComponentType, ComponentHealthSummary] = {}
        for metric in all_latest_metrics:
            if metric.component_type not in summaries:
                summaries[metric.component_type] = ComponentHealthSummary(
                    component_type=metric.component_type,
                    total_components=0,
                    healthy_components=0,
                    degraded_components=0,
                    critical_components=0,
                    average_health_score=0.0,
                )

            summary = summaries[metric.component_type]
            summary.total_components += 1

            if metric.health_score >= 80:
                summary.healthy_components += 1
            elif metric.health_score >= 60:
                summary.degraded_components += 1
            else:
                summary.critical_components += 1

        # Calculate averages
        for summary in summaries.values():
            component_metrics = [m for m in all_latest_metrics if m.component_type == summary.component_type]
            summary.average_health_score = sum(m.health_score for m in component_metrics) / len(component_metrics)

            operating_hours = [m.operating_hours for m in component_metrics if m.operating_hours is not None]
            if operating_hours:
                summary.average_operating_hours = sum(operating_hours) / len(operating_hours)

        # Calculate fleet-wide metrics
        total_robots = len(set(m.robot_id for m in all_latest_metrics))
        total_components = len(all_latest_metrics)
        average_fleet_health = sum(m.health_score for m in all_latest_metrics) / max(total_components, 1)

        # Count active issues
        active_anomalies = len([a for a in self.anomalies.values() if not a.acknowledged])
        pending_predictions = len(self.predictions)

        # Count maintenance tasks
        schedules = self.get_maintenance_schedules()
        scheduled_count = len([s for s in schedules if s.status == MaintenanceStatus.SCHEDULED])
        overdue_count = len([s for s in schedules if s.status == MaintenanceStatus.OVERDUE])

        # Mock uptime (production: calculate from actual downtime data)
        uptime_percentage = max(95.0 - (active_anomalies * 2) - (overdue_count * 5), 80.0)

        return MaintenanceAnalyticsResponse(
            total_robots=total_robots,
            total_components=total_components,
            health_summaries=list(summaries.values()),
            active_anomalies=active_anomalies,
            pending_predictions=pending_predictions,
            scheduled_maintenance_count=scheduled_count,
            overdue_maintenance_count=overdue_count,
            average_fleet_health=average_fleet_health,
            uptime_percentage=uptime_percentage,
        )


# Singleton instance
def get_maintenance_service() -> PredictiveMaintenanceService:
    """Get PredictiveMaintenanceService singleton instance."""
    return PredictiveMaintenanceService()
