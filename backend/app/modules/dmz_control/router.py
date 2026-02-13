"""
DMZ Control API Router - SECURED

Endpoints for managing DMZ gateway services.
All endpoints require ADMIN role.
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import PlainTextResponse
from loguru import logger
from typing import List

from app.modules.dmz_control.service import get_dmz_control_service
from app.modules.dmz_control.schemas import (
    DMZStatus,
    DMZControlResponse,
)
from app.modules.dmz_control.monitoring import (
    get_dmz_health_monitor,
    DMZMetrics,
    GatewayHealthMetric,
)
from app.core.auth_deps import (
    require_role,
    SystemRole,
    Principal,
)
from app.core.security import UserRole

router = APIRouter(prefix="/api/dmz", tags=["dmz"])


def _audit_log(
    action: str,
    principal: Principal,
    details: dict = None,
):
    """Log DMZ operations for audit trail"""
    audit_entry = {
        "action": action,
        "principal_id": principal.principal_id,
        "principal_type": principal.principal_type.value,
        "tenant_id": principal.tenant_id,
        "details": details or {},
    }
    logger.info(f"[AUDIT] DMZ operation: {audit_entry}")


@router.get(
    "/status",
    response_model=DMZStatus,
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def get_dmz_status(principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))):
    """
    Get DMZ gateway status.

    Returns current status of all DMZ containers.

    **Security**: Admin only
    """
    service = get_dmz_control_service()

    try:
        status = await service.get_status()
        _audit_log("dmz_status_view", principal, {"status": status.running if hasattr(status, 'running') else None})
        return status

    except Exception as e:
        logger.error(f"Failed to get DMZ status: {e}")
        _audit_log("dmz_status_failed", principal, {"error": str(e)})
        raise HTTPException(
            status_code=500, detail=f"Failed to get DMZ status: {str(e)}"
        )


@router.post(
    "/start",
    response_model=DMZControlResponse,
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def start_dmz(principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))):
    """
    Start DMZ gateway services.

    Starts all DMZ containers defined in docker-compose.dmz.yml.

    **Security**: Admin only

    **Note**: DMZ cannot be started in Sovereign Mode.
    """
    service = get_dmz_control_service()

    try:
        # TODO: Check if in Sovereign Mode - if yes, reject
        # from app.modules.sovereign_mode import get_sovereign_service
        # sovereign = get_sovereign_service()
        # if sovereign.config.current_mode == OperationMode.SOVEREIGN:
        #     raise HTTPException(
        #         status_code=403,
        #         detail="Cannot start DMZ while in Sovereign Mode"
        #     )

        success = await service.start_dmz()

        if success:
            status = await service.get_status()
            _audit_log("dmz_start", principal, {"success": True})
            return DMZControlResponse(
                success=True,
                message="DMZ gateway started successfully",
                status=status,
            )
        else:
            _audit_log("dmz_start", principal, {"success": False})
            return DMZControlResponse(
                success=False, message="Failed to start DMZ gateway"
            )

    except Exception as e:
        logger.error(f"Failed to start DMZ: {e}")
        _audit_log("dmz_start_failed", principal, {"error": str(e)})
        raise HTTPException(
            status_code=500, detail=f"Failed to start DMZ: {str(e)}"
        )


@router.post(
    "/stop",
    response_model=DMZControlResponse,
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def stop_dmz(principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))):
    """
    Stop DMZ gateway services.

    Stops all DMZ containers.

    **Security**: Admin only
    """
    service = get_dmz_control_service()

    try:
        success = await service.stop_dmz()

        if success:
            status = await service.get_status()
            _audit_log("dmz_stop", principal, {"success": True})
            return DMZControlResponse(
                success=True,
                message="DMZ gateway stopped successfully",
                status=status,
            )
        else:
            _audit_log("dmz_stop", principal, {"success": False})
            return DMZControlResponse(
                success=False, message="Failed to stop DMZ gateway"
            )

    except Exception as e:
        logger.error(f"Failed to stop DMZ: {e}")
        _audit_log("dmz_stop_failed", principal, {"error": str(e)})
        raise HTTPException(
            status_code=500, detail=f"Failed to stop DMZ: {str(e)}"
        )


# ============================================================================
# MONITORING & METRICS ENDPOINTS
# ============================================================================


@router.get(
    "/metrics",
    response_model=DMZMetrics,
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def get_dmz_metrics(principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))):
    """
    Get aggregated DMZ gateway metrics.

    Returns summary metrics for all DMZ services:
    - Total gateway count
    - Health status distribution
    - Total message throughput
    - Total error count

    **Use Case**: Dashboard overview, alerting
    **Security**: Admin only
    """
    monitor = get_dmz_health_monitor()

    try:
        metrics = await monitor.get_metrics()
        _audit_log("dmz_metrics_view", principal, {"gateway_count": metrics.total_gateways if hasattr(metrics, 'total_gateways') else None})
        return metrics

    except Exception as e:
        logger.error(f"Failed to get DMZ metrics: {e}")
        _audit_log("dmz_metrics_failed", principal, {"error": str(e)})
        raise HTTPException(
            status_code=500, detail=f"Failed to get DMZ metrics: {str(e)}"
        )


@router.get(
    "/metrics/gateways",
    response_model=List[GatewayHealthMetric],
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def get_gateway_metrics(principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))):
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
    **Security**: Admin only
    """
    monitor = get_dmz_health_monitor()

    try:
        metrics = await monitor.get_gateway_metrics()
        _audit_log("dmz_gateway_metrics_view", principal, {"count": len(metrics)})
        return metrics

    except Exception as e:
        logger.error(f"Failed to get gateway metrics: {e}")
        _audit_log("dmz_gateway_metrics_failed", principal, {"error": str(e)})
        raise HTTPException(
            status_code=500, detail=f"Failed to get gateway metrics: {str(e)}"
        )


@router.get(
    "/metrics/prometheus",
    response_class=PlainTextResponse,
    dependencies=[Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))],
)
async def get_prometheus_metrics(principal: Principal = Depends(require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN))):
    """
    Get metrics in Prometheus format.

    Returns metrics in Prometheus exposition format for scraping.

    **Metrics exposed**:
    - `dmz_gateway_status`: Gateway health (1=healthy, 0.5=degraded, 0=unhealthy)
    - `dmz_gateway_messages_total`: Total messages processed
    - `dmz_gateway_errors_total`: Total errors
    - `dmz_gateway_uptime_seconds`: Gateway uptime

    **Use Case**: Prometheus/Grafana integration
    **Security**: Admin only

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
        _audit_log("dmz_prometheus_metrics_view", principal)
        return metrics

    except Exception as e:
        logger.error(f"Failed to get Prometheus metrics: {e}")
        _audit_log("dmz_prometheus_metrics_failed", principal, {"error": str(e)})
        raise HTTPException(
            status_code=500, detail=f"Failed to get Prometheus metrics: {str(e)}"
        )
