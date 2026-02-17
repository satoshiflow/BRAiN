"""
Monitoring Router (Sprint 7)

API endpoints for operational monitoring and metrics.
"""

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse
from typing import Dict, Any
from loguru import logger

from app.modules.monitoring.metrics import get_metrics_collector

router = APIRouter(prefix="/metrics", tags=["monitoring"])


@router.get("", response_class=PlainTextResponse)
async def get_prometheus_metrics() -> str:
    """
    Get Prometheus-compatible metrics.

    **Prometheus Scrape Endpoint**

    This endpoint exposes operational metrics in Prometheus text format.
    Designed to be scraped every 30-60 seconds.

    **Metrics Exposed:**
    - `brain_mode_current`: Current operation mode (0=online, 1=offline, 2=sovereign, 3=quarantine)
    - `brain_mode_switch_total`: Total mode switches (counter)
    - `brain_override_active`: Active override flag (0=inactive, 1=active)
    - `brain_quarantine_total`: Total bundles quarantined (counter)
    - `brain_executor_failures_total`: Total executor hard failures (counter)
    - `brain_last_success_timestamp`: Last successful operation (unix timestamp)

    **Prometheus Configuration:**
    ```yaml
    scrape_configs:
      - job_name: 'brain'
        scrape_interval: 30s
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/metrics'
    ```

    **Security:**
    - No secrets exposed
    - No payload data
    - No bundle content
    - Read-only endpoint

    Returns:
        Prometheus text format metrics
    """
    try:
        collector = get_metrics_collector()
        metrics_text = collector.export_prometheus()

        logger.debug("Metrics endpoint called - returning Prometheus format")

        return metrics_text

    except Exception as e:
        # Fail-safe: return error metric
        logger.error(f"Metrics endpoint failed: {e}")
        return f"# ERROR: Metrics endpoint failed: {e}\n"


@router.get("/summary")
async def get_metrics_summary() -> Dict[str, Any]:
    """
    Get human-readable metrics summary.

    **Human-Readable Metrics**

    Returns metrics in JSON format for human consumption.
    Not intended for Prometheus scraping.

    Returns:
        Metrics summary dictionary with:
        - current_mode: Current operation mode
        - mode_switches_total: Total mode switches
        - override_active: Override status
        - quarantine_total: Total quarantines
        - executor_failures_total: Total executor failures
        - last_success_timestamp: Unix timestamp
        - last_success_iso: ISO 8601 timestamp
        - uptime_seconds: Collector uptime
    """
    try:
        collector = get_metrics_collector()
        summary = collector.get_summary()

        return {
            "success": True,
            "metrics": summary,
        }

    except Exception as e:
        logger.error(f"Metrics summary failed: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@router.get("/health")
async def metrics_health_check() -> Dict[str, Any]:
    """
    Check metrics collector health.

    **Health Check**

    Verify that the metrics collector is operational.
    Returns 200 if healthy, 500 if unhealthy.

    Returns:
        Health status dictionary
    """
    try:
        collector = get_metrics_collector()
        is_healthy = collector.health_check()

        if is_healthy:
            return {
                "healthy": True,
                "message": "Metrics collector operational",
            }
        else:
            return {
                "healthy": False,
                "message": "Metrics collector unhealthy",
            }

    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        return {
            "healthy": False,
            "error": str(e),
        }
