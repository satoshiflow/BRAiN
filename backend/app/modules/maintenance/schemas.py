"""
Predictive Maintenance Schemas

Data models for health monitoring, anomaly detection, failure prediction,
and maintenance scheduling.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime


class ComponentType(str, Enum):
    """Robot component types for monitoring."""
    MOTOR = "motor"
    BATTERY = "battery"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    CONTROLLER = "controller"
    DRIVE_SYSTEM = "drive_system"
    MANIPULATOR = "manipulator"
    COMMUNICATION = "communication"


class AnomalyType(str, Enum):
    """Types of detected anomalies."""
    TEMPERATURE_SPIKE = "temperature_spike"
    VIBRATION_ANOMALY = "vibration_anomaly"
    POWER_FLUCTUATION = "power_fluctuation"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    SENSOR_DRIFT = "sensor_drift"
    COMMUNICATION_LOSS = "communication_loss"
    UNEXPECTED_BEHAVIOR = "unexpected_behavior"


class AnomalySeverity(str, Enum):
    """Severity levels for anomalies."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MaintenanceType(str, Enum):
    """Types of maintenance actions."""
    INSPECTION = "inspection"
    LUBRICATION = "lubrication"
    CALIBRATION = "calibration"
    COMPONENT_REPLACEMENT = "component_replacement"
    SOFTWARE_UPDATE = "software_update"
    CLEANING = "cleaning"
    PREVENTIVE = "preventive"
    CORRECTIVE = "corrective"


class MaintenanceStatus(str, Enum):
    """Status of maintenance tasks."""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    OVERDUE = "overdue"


class HealthMetrics(BaseModel):
    """Component health metrics."""
    component_id: str
    component_type: ComponentType
    robot_id: str
    timestamp: float

    # Core metrics
    health_score: float = Field(ge=0.0, le=100.0, description="Overall health score (0-100)")
    temperature_c: Optional[float] = None
    vibration_level: Optional[float] = None
    power_consumption_w: Optional[float] = None
    operating_hours: Optional[float] = None
    cycle_count: Optional[int] = None

    # Additional metrics
    error_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    response_time_ms: Optional[float] = None
    custom_metrics: Dict[str, float] = Field(default_factory=dict)


class AnomalyDetection(BaseModel):
    """Detected anomaly information."""
    anomaly_id: str
    robot_id: str
    component_id: str
    component_type: ComponentType
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    detected_at: float

    # Detection details
    anomaly_score: float = Field(ge=0.0, le=1.0, description="Anomaly confidence score")
    baseline_value: Optional[float] = None
    current_value: Optional[float] = None
    deviation_percentage: Optional[float] = None

    # Context
    description: str
    recommended_action: Optional[str] = None
    acknowledged: bool = False


class FailurePrediction(BaseModel):
    """Predicted component failure."""
    prediction_id: str
    robot_id: str
    component_id: str
    component_type: ComponentType

    # Prediction details
    failure_probability: float = Field(ge=0.0, le=1.0, description="Probability of failure")
    predicted_failure_time: Optional[float] = None  # Unix timestamp
    time_to_failure_hours: Optional[float] = Field(None, ge=0.0)
    confidence_score: float = Field(ge=0.0, le=1.0)

    # Root cause
    root_cause: Optional[str] = None
    contributing_factors: List[str] = Field(default_factory=list)

    # Recommendations
    recommended_actions: List[str] = Field(default_factory=list)
    estimated_downtime_hours: Optional[float] = None


class MaintenanceSchedule(BaseModel):
    """Scheduled maintenance task."""
    schedule_id: str
    robot_id: str
    component_id: Optional[str] = None
    component_type: Optional[ComponentType] = None

    # Schedule details
    maintenance_type: MaintenanceType
    status: MaintenanceStatus
    scheduled_time: float  # Unix timestamp
    estimated_duration_hours: float = Field(gt=0.0)

    # Task details
    description: str
    priority: int = Field(ge=1, le=5, description="Priority 1-5 (5=highest)")
    required_parts: List[str] = Field(default_factory=list)
    required_tools: List[str] = Field(default_factory=list)
    technician_notes: Optional[str] = None

    # Completion
    completed_at: Optional[float] = None
    actual_duration_hours: Optional[float] = None
    completion_notes: Optional[str] = None


class ComponentHealthSummary(BaseModel):
    """Summary of component health across fleet."""
    component_type: ComponentType
    total_components: int
    healthy_components: int = Field(ge=0)
    degraded_components: int = Field(ge=0)
    critical_components: int = Field(ge=0)
    average_health_score: float = Field(ge=0.0, le=100.0)
    average_operating_hours: Optional[float] = None


class MaintenanceAnalyticsRequest(BaseModel):
    """Request for maintenance analytics."""
    robot_ids: Optional[List[str]] = None
    component_types: Optional[List[ComponentType]] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    include_predictions: bool = True
    include_anomalies: bool = True


class MaintenanceAnalyticsResponse(BaseModel):
    """Maintenance analytics results."""
    total_robots: int
    total_components: int
    health_summaries: List[ComponentHealthSummary]
    active_anomalies: int
    pending_predictions: int
    scheduled_maintenance_count: int
    overdue_maintenance_count: int
    average_fleet_health: float = Field(ge=0.0, le=100.0)
    uptime_percentage: float = Field(ge=0.0, le=100.0)
