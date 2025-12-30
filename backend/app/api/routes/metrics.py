"""
Metrics API Endpoints

Exposes Prometheus metrics for monitoring and Grafana dashboards.
"""

from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format for scraping.
    Compatible with Prometheus, Grafana, and other monitoring tools.

    Metrics include:
    - Supervisor operations (requests, approvals, denials)
    - HITL queue and approvals
    - Policy evaluations
    - Agent operations (code generation, deployments, compliance checks)
    - Authentication (logins, sessions, token refreshes)
    - Mission system (queue size, execution times)

    Example Prometheus scrape config:
    ```yaml
    scrape_configs:
      - job_name: 'brain'
        static_configs:
          - targets: ['localhost:8000']
        metrics_path: '/metrics'
    ```
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
