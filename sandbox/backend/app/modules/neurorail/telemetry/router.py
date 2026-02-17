"""
NeuroRail Telemetry API Router.

Provides REST endpoints for:
- Getting execution metrics
- Real-time system snapshot
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import Optional

from app.modules.neurorail.telemetry.service import (
    TelemetryService,
    get_telemetry_service,
)
from app.modules.neurorail.telemetry.schemas import (
    ExecutionMetrics,
    RealtimeSnapshot,
)

router = APIRouter(prefix="/api/neurorail/v1/telemetry", tags=["NeuroRail Telemetry"])


# ============================================================================
# Metrics Endpoints
# ============================================================================

@router.get("/metrics/{entity_id}", response_model=ExecutionMetrics)
async def get_execution_metrics(
    entity_id: str,
    service: TelemetryService = Depends(get_telemetry_service)
) -> ExecutionMetrics:
    """
    Get execution metrics for an entity.

    Args:
        entity_id: Entity identifier (attempt_id, job_id, or mission_id)

    Returns:
        Execution metrics

    Raises:
        404: Metrics not found
    """
    metrics = await service.get_execution_metrics(entity_id)

    if not metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Metrics for {entity_id} not found"
        )

    return metrics


@router.get("/snapshot", response_model=RealtimeSnapshot)
async def get_realtime_snapshot(
    service: TelemetryService = Depends(get_telemetry_service)
) -> RealtimeSnapshot:
    """
    Get real-time system snapshot.

    Returns:
        Current snapshot of system state

    Raises:
        404: Snapshot not available
    """
    snapshot = await service.get_snapshot()

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Snapshot not available"
        )

    return snapshot


# Note: Metrics recording is done via service, not exposed as API endpoints
# (only internal modules can write metrics)
