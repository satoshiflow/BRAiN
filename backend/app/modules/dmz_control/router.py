"""
DMZ Control API Router

Endpoints for managing DMZ gateway services.
"""

from fastapi import APIRouter, HTTPException
from loguru import logger

from backend.app.modules.dmz_control.service import get_dmz_control_service
from backend.app.modules.dmz_control.schemas import (
    DMZStatus,
    DMZControlResponse,
)
from backend.app.modules.dmz_control.monitoring import (
    get_dmz_health_monitor,
    DMZMetrics,
    GatewayHealthMetric,
)
from typing import List
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/dmz", tags=["dmz"])


@router.get("/status", response_model=DMZStatus)
async def get_dmz_status():
    """
    Get DMZ gateway status.

    Returns current status of all DMZ containers.

    **Security**: Admin/Owner only (TODO: implement auth check)
    """
    service = get_dmz_control_service()

    try:
        status = await service.get_status()
        return status

    except Exception as e:
        logger.error(f"Failed to get DMZ status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get DMZ status: {str(e)}"
        )


@router.post("/start", response_model=DMZControlResponse)
async def start_dmz():
    """
    Start DMZ gateway services.

    Starts all DMZ containers defined in docker-compose.dmz.yml.

    **Security**: Admin/Owner only (TODO: implement auth check)

    **Note**: DMZ cannot be started in Sovereign Mode.
    """
    service = get_dmz_control_service()

    try:
        # TODO: Check if in Sovereign Mode - if yes, reject
        # from backend.app.modules.sovereign_mode import get_sovereign_service
        # sovereign = get_sovereign_service()
        # if sovereign.config.current_mode == OperationMode.SOVEREIGN:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="Cannot start DMZ while in Sovereign Mode"
        #     )

        success = await service.start_dmz()

        if success:
            status = await service.get_status()
            return DMZControlResponse(
                success=True,
                message="DMZ gateway started successfully",
                status=status,
            )
        else:
            return DMZControlResponse(
                success=False, message="Failed to start DMZ gateway"
            )

    except Exception as e:
        logger.error(f"Failed to start DMZ: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start DMZ: {str(e)}"
        )


@router.post("/stop", response_model=DMZControlResponse)
async def stop_dmz():
    """
    Stop DMZ gateway services.

    Stops all DMZ containers.

    **Security**: Admin/Owner only (TODO: implement auth check)
    """
    service = get_dmz_control_service()

    try:
        success = await service.stop_dmz()

        if success:
            status = await service.get_status()
            return DMZControlResponse(
                success=True,
                message="DMZ gateway stopped successfully",
                status=status,
            )
        else:
            return DMZControlResponse(
                success=False, message="Failed to stop DMZ gateway"
            )

    except Exception as e:
        logger.error(f"Failed to stop DMZ: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to stop DMZ: {str(e)}"
        )


# ============================================================================
# MONITORING & METRICS ENDPOINTS
# ============================================================================


@router.get("/metrics", response_model=DMZMetrics)
async def get_dmz_metrics():
    """
    Get aggregated DMZ gateway metrics.

    Returns summary metrics for all DMZ services:
    - Total gateway count
    - Health status distribution
    - Total message throughput
    - Total error count

    **Use Case**: Dashboard overview, alerting
    """
    monitor = get_dmz_health_monitor()

    try:
        metrics = await monitor.get_metrics()
        return metrics

    except Exception as e:
        logger.error(f"Failed to get DMZ metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get DMZ metrics: {str(e)}"
        )


@router.get("/metrics/gateways", response_model=List[GatewayHealthMetric])
async def get_gateway_metrics():
    """
    Get individual gateway health metrics.

    Returns detailed metrics for each DMZ gateway service:
    - Service name
    - Health status
    - Uptime
    - Message count
    - Error count
    - Last error message

    **Use Case**: Detailed monitoring, troubleshooting
    """
    monitor = get_dmz_health_monitor()

    try:
        metrics = await monitor.get_gateway_metrics()
        return metrics

    except Exception as e:
        logger.error(f"Failed to get gateway metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get gateway metrics: {str(e)}"
        )


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """
    Get metrics in Prometheus format.

    Returns metrics in Prometheus exposition format for scraping.

    **Metrics exposed**:
    - `dmz_gateway_status`: Gateway health (1=healthy, 0.5=degraded, 0=unhealthy)
    - `dmz_gateway_messages_total`: Total messages processed
    - `dmz_gateway_errors_total`: Total errors
    - `dmz_gateway_uptime_seconds`: Gateway uptime

    **Use Case**: Prometheus/Grafana integration

    **Example**:
    ```
    # HELP dmz_gateway_status Gateway health status
    # TYPE dmz_gateway_status gauge
    dmz_gateway_status{service="telegram"} 1.0
    dmz_gateway_status{service="whatsapp"} 0.5
    ```
    """
    monitor = get_dmz_health_monitor()

    try:
        metrics = await monitor.get_prometheus_metrics()
        return metrics

    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get Prometheus metrics: {str(e)}"
        )
