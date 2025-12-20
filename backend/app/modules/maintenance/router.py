"""
Predictive Maintenance API Router

REST API endpoints for health monitoring, anomaly detection, failure prediction,
and maintenance scheduling.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from .schemas import (
    HealthMetrics,
    AnomalyDetection,
    AnomalySeverity,
    FailurePrediction,
    MaintenanceSchedule,
    MaintenanceStatus,
    ComponentType,
    MaintenanceAnalyticsResponse,
)
from .service import get_maintenance_service


router = APIRouter(prefix="/api/maintenance", tags=["maintenance"])


# ========== Health Monitoring Endpoints ==========

@router.post("/health-metrics", response_model=HealthMetrics)
async def record_health_metrics(metrics: HealthMetrics):
    """
    Record health metrics for a component.

    Automatically triggers anomaly detection and baseline updates.
    """
    service = get_maintenance_service()
    return service.record_health_metrics(metrics)


@router.get("/health-metrics", response_model=List[HealthMetrics])
async def get_health_metrics(
    component_id: Optional[str] = Query(None, description="Filter by component ID"),
    robot_id: Optional[str] = Query(None, description="Filter by robot ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results")
):
    """
    Get health metrics history.

    Supports filtering by component_id or robot_id.
    """
    service = get_maintenance_service()
    return service.get_health_metrics(
        component_id=component_id,
        robot_id=robot_id,
        limit=limit
    )


# ========== Anomaly Detection Endpoints ==========

@router.get("/anomalies", response_model=List[AnomalyDetection])
async def get_anomalies(
    robot_id: Optional[str] = Query(None, description="Filter by robot ID"),
    severity: Optional[AnomalySeverity] = Query(None, description="Filter by severity"),
    acknowledged: Optional[bool] = Query(None, description="Filter by acknowledgement status")
):
    """
    Get detected anomalies.

    Supports filtering by robot_id, severity, and acknowledgement status.
    """
    service = get_maintenance_service()
    return service.get_anomalies(
        robot_id=robot_id,
        severity=severity,
        acknowledged=acknowledged
    )


@router.post("/anomalies/{anomaly_id}/acknowledge", response_model=AnomalyDetection)
async def acknowledge_anomaly(anomaly_id: str):
    """
    Acknowledge an anomaly.

    Marks the anomaly as reviewed by maintenance team.
    """
    service = get_maintenance_service()
    anomaly = service.acknowledge_anomaly(anomaly_id)

    if not anomaly:
        raise HTTPException(status_code=404, detail=f"Anomaly {anomaly_id} not found")

    return anomaly


# ========== Failure Prediction Endpoints ==========

@router.post("/predictions/{component_id}", response_model=Optional[FailurePrediction])
async def predict_component_failure(component_id: str):
    """
    Predict failure for a specific component.

    Analyzes health metrics trends to predict potential failures.
    Returns None if insufficient data or no failure predicted.
    """
    service = get_maintenance_service()
    prediction = service.predict_failure(component_id)

    return prediction


@router.get("/predictions", response_model=List[FailurePrediction])
async def get_failure_predictions(
    robot_id: Optional[str] = Query(None, description="Filter by robot ID"),
    min_probability: float = Query(0.0, ge=0.0, le=1.0, description="Minimum failure probability")
):
    """
    Get failure predictions.

    Returns predictions sorted by failure probability (highest first).
    """
    service = get_maintenance_service()
    return service.get_predictions(
        robot_id=robot_id,
        min_probability=min_probability
    )


# ========== Maintenance Scheduling Endpoints ==========

@router.post("/schedules", response_model=MaintenanceSchedule)
async def schedule_maintenance(schedule: MaintenanceSchedule):
    """
    Schedule a maintenance task.

    Creates a new maintenance schedule for a robot or component.
    """
    service = get_maintenance_service()
    return service.schedule_maintenance(schedule)


@router.get("/schedules", response_model=List[MaintenanceSchedule])
async def get_maintenance_schedules(
    robot_id: Optional[str] = Query(None, description="Filter by robot ID"),
    status: Optional[MaintenanceStatus] = Query(None, description="Filter by status")
):
    """
    Get maintenance schedules.

    Returns schedules sorted by scheduled time.
    Automatically marks overdue tasks.
    """
    service = get_maintenance_service()
    return service.get_maintenance_schedules(
        robot_id=robot_id,
        status=status
    )


@router.put("/schedules/{schedule_id}/status", response_model=MaintenanceSchedule)
async def update_maintenance_status(
    schedule_id: str,
    status: MaintenanceStatus,
    completion_notes: Optional[str] = None
):
    """
    Update maintenance task status.

    Use to mark tasks as in_progress, completed, or cancelled.
    """
    service = get_maintenance_service()
    schedule = service.update_maintenance_status(
        schedule_id=schedule_id,
        status=status,
        completion_notes=completion_notes
    )

    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    return schedule


# ========== Analytics Endpoints ==========

@router.get("/analytics", response_model=MaintenanceAnalyticsResponse)
async def get_maintenance_analytics(
    robot_ids: Optional[List[str]] = Query(None, description="Filter by robot IDs"),
    component_types: Optional[List[ComponentType]] = Query(None, description="Filter by component types")
):
    """
    Get maintenance analytics.

    Provides fleet-wide health summaries, anomaly counts, predictions,
    and maintenance task statistics.
    """
    service = get_maintenance_service()
    return service.get_analytics(
        robot_ids=robot_ids,
        component_types=component_types
    )


@router.get("/info")
async def get_maintenance_info():
    """
    Get predictive maintenance module information.
    """
    service = get_maintenance_service()

    return {
        "module": "Predictive Maintenance",
        "version": "1.0.0",
        "description": "Health monitoring, anomaly detection, failure prediction, and intelligent maintenance scheduling",
        "features": [
            "Real-time health monitoring",
            "Anomaly detection (threshold & statistical)",
            "Failure prediction using trend analysis",
            "Intelligent maintenance scheduling",
            "Fleet-wide analytics"
        ],
        "endpoints": {
            "health_metrics": "/api/maintenance/health-metrics",
            "anomalies": "/api/maintenance/anomalies",
            "predictions": "/api/maintenance/predictions",
            "schedules": "/api/maintenance/schedules",
            "analytics": "/api/maintenance/analytics"
        },
        "statistics": {
            "total_components_monitored": len(service.health_metrics),
            "active_anomalies": len([a for a in service.anomalies.values() if not a.acknowledged]),
            "pending_predictions": len(service.predictions),
            "scheduled_tasks": len([s for s in service.schedules.values() if s.status == MaintenanceStatus.SCHEDULED])
        }
    }
