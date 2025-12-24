"""
DMZ Gateway Health Metrics

Prometheus-style metrics for DMZ gateway services.
"""

import time
from typing import Dict, List, Optional
from loguru import logger
from pydantic import BaseModel


class GatewayHealthMetric(BaseModel):
    """Health metric for a single gateway."""

    service: str
    status: str  # healthy | degraded | unhealthy
    uptime_seconds: float
    last_check: float
    message_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None


class DMZMetrics(BaseModel):
    """Aggregated DMZ metrics."""

    total_gateways: int
    healthy_gateways: int
    degraded_gateways: int
    unhealthy_gateways: int
    total_messages: int
    total_errors: int
    metrics_timestamp: float


class DMZHealthMonitor:
    """
    Monitor health and metrics for all DMZ gateway services.

    Provides Prometheus-style metrics for:
    - Gateway availability
    - Message throughput
    - Error rates
    - Uptime
    """

    def __init__(self):
        self._gateway_metrics: Dict[str, GatewayHealthMetric] = {}
        self._start_time = time.time()

    async def record_message(self, service: str):
        """Record a successful message forwarding."""
        if service not in self._gateway_metrics:
            self._initialize_gateway(service)

        self._gateway_metrics[service].message_count += 1
        self._gateway_metrics[service].last_check = time.time()

    async def record_error(self, service: str, error: str):
        """Record an error for a gateway."""
        if service not in self._gateway_metrics:
            self._initialize_gateway(service)

        self._gateway_metrics[service].error_count += 1
        self._gateway_metrics[service].last_error = error
        self._gateway_metrics[service].last_check = time.time()

        # Update status based on error rate
        metrics = self._gateway_metrics[service]
        error_rate = metrics.error_count / max(metrics.message_count, 1)

        if error_rate > 0.5:
            metrics.status = "unhealthy"
        elif error_rate > 0.2:
            metrics.status = "degraded"

    async def update_gateway_status(
        self, service: str, status: str, uptime_seconds: float
    ):
        """Update gateway status from health check."""
        if service not in self._gateway_metrics:
            self._initialize_gateway(service)

        self._gateway_metrics[service].status = status
        self._gateway_metrics[service].uptime_seconds = uptime_seconds
        self._gateway_metrics[service].last_check = time.time()

    def _initialize_gateway(self, service: str):
        """Initialize metrics for a new gateway."""
        self._gateway_metrics[service] = GatewayHealthMetric(
            service=service,
            status="unknown",
            uptime_seconds=0.0,
            last_check=time.time(),
        )

    async def get_metrics(self) -> DMZMetrics:
        """Get aggregated DMZ metrics."""
        healthy = sum(
            1 for m in self._gateway_metrics.values() if m.status == "healthy"
        )
        degraded = sum(
            1 for m in self._gateway_metrics.values() if m.status == "degraded"
        )
        unhealthy = sum(
            1
            for m in self._gateway_metrics.values()
            if m.status in ["unhealthy", "unknown"]
        )

        total_messages = sum(m.message_count for m in self._gateway_metrics.values())
        total_errors = sum(m.error_count for m in self._gateway_metrics.values())

        return DMZMetrics(
            total_gateways=len(self._gateway_metrics),
            healthy_gateways=healthy,
            degraded_gateways=degraded,
            unhealthy_gateways=unhealthy,
            total_messages=total_messages,
            total_errors=total_errors,
            metrics_timestamp=time.time(),
        )

    async def get_gateway_metrics(self) -> List[GatewayHealthMetric]:
        """Get individual gateway metrics."""
        return list(self._gateway_metrics.values())

    async def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format.

        Example output:
        ```
        # HELP dmz_gateway_status Gateway health status (1=healthy, 0.5=degraded, 0=unhealthy)
        # TYPE dmz_gateway_status gauge
        dmz_gateway_status{service="telegram"} 1.0

        # HELP dmz_gateway_messages_total Total messages processed
        # TYPE dmz_gateway_messages_total counter
        dmz_gateway_messages_total{service="telegram"} 42

        # HELP dmz_gateway_errors_total Total errors encountered
        # TYPE dmz_gateway_errors_total counter
        dmz_gateway_errors_total{service="telegram"} 2
        ```
        """
        lines = []

        # Gateway status
        lines.append(
            "# HELP dmz_gateway_status Gateway health status (1=healthy, 0.5=degraded, 0=unhealthy)"
        )
        lines.append("# TYPE dmz_gateway_status gauge")
        for service, metrics in self._gateway_metrics.items():
            status_value = (
                1.0
                if metrics.status == "healthy"
                else 0.5 if metrics.status == "degraded" else 0.0
            )
            lines.append(f'dmz_gateway_status{{service="{service}"}} {status_value}')

        lines.append("")

        # Message counts
        lines.append("# HELP dmz_gateway_messages_total Total messages processed")
        lines.append("# TYPE dmz_gateway_messages_total counter")
        for service, metrics in self._gateway_metrics.items():
            lines.append(
                f'dmz_gateway_messages_total{{service="{service}"}} {metrics.message_count}'
            )

        lines.append("")

        # Error counts
        lines.append("# HELP dmz_gateway_errors_total Total errors encountered")
        lines.append("# TYPE dmz_gateway_errors_total counter")
        for service, metrics in self._gateway_metrics.items():
            lines.append(
                f'dmz_gateway_errors_total{{service="{service}"}} {metrics.error_count}'
            )

        lines.append("")

        # Uptime
        lines.append("# HELP dmz_gateway_uptime_seconds Gateway uptime in seconds")
        lines.append("# TYPE dmz_gateway_uptime_seconds gauge")
        for service, metrics in self._gateway_metrics.items():
            lines.append(
                f'dmz_gateway_uptime_seconds{{service="{service}"}} {metrics.uptime_seconds}'
            )

        return "\n".join(lines)


# Singleton
_monitor: Optional[DMZHealthMonitor] = None


def get_dmz_health_monitor() -> DMZHealthMonitor:
    """Get singleton DMZ health monitor."""
    global _monitor
    if _monitor is None:
        _monitor = DMZHealthMonitor()
    return _monitor
