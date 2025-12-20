"""
Prometheus Metrics Endpoint

Exposes Prometheus metrics at /metrics endpoint for scraping.

Endpoint:
    GET /metrics - Prometheus metrics in exposition format

Usage:
    # Prometheus scrape config (prometheus.yml)
    scrape_configs:
      - job_name: 'brain-backend'
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/metrics'
        scrape_interval: 15s
"""

from fastapi import APIRouter, Response
from app.core.metrics import get_metrics, get_metrics_content_type, MetricsCollector
import time

router = APIRouter(tags=["metrics"])

# Track application start time for uptime metric
_start_time = time.time()


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns all registered metrics in Prometheus exposition format.
    This endpoint is automatically scraped by Prometheus.

    Returns:
        Response: Metrics in Prometheus format

    Example metrics output:
        # HELP brain_http_requests_total Total HTTP requests
        # TYPE brain_http_requests_total counter
        brain_http_requests_total{method="GET",endpoint="/api/health",status="200"} 42.0

        # HELP brain_http_request_duration_seconds HTTP request latency
        # TYPE brain_http_request_duration_seconds histogram
        brain_http_request_duration_seconds_bucket{le="0.005",method="GET",endpoint="/api/health"} 35.0
        brain_http_request_duration_seconds_bucket{le="0.01",method="GET",endpoint="/api/health"} 40.0
        ...
    """
    # Update uptime metric before generating metrics
    uptime = time.time() - _start_time
    MetricsCollector.update_uptime(uptime)

    # Update database pool metrics (if available)
    try:
        from app.core.db import get_pool_status
        pool_status = await get_pool_status()
        MetricsCollector.update_db_pool_metrics(
            pool_size=pool_status["pool_size"],
            checked_out=pool_status["checked_out"],
            overflow=pool_status["overflow"]
        )
    except Exception:
        # Database pool status not available (e.g., during startup)
        pass

    # Update Redis status (if available)
    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()
        MetricsCollector.update_redis_status(connected=True)
    except Exception:
        MetricsCollector.update_redis_status(connected=False)

    # Update health check statuses
    try:
        from app.core.db import check_db_health
        db_healthy = await check_db_health()
        MetricsCollector.update_health_status("database", db_healthy)
    except Exception:
        MetricsCollector.update_health_status("database", False)

    try:
        from app.core.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()
        MetricsCollector.update_health_status("redis", True)
    except Exception:
        MetricsCollector.update_health_status("redis", False)

    # Generate and return metrics
    metrics_output = get_metrics()

    return Response(
        content=metrics_output,
        media_type=get_metrics_content_type()
    )
