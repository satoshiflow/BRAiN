"""
NeuroRail Telemetry Module.

Provides metrics collection and monitoring:
- Prometheus metrics export
- Real-time snapshots
- Historical data aggregation
"""

from backend.app.modules.neurorail.telemetry.schemas import (
    ExecutionMetrics,
    AggregatedMetrics,
    RealtimeSnapshot,
    MetricEvent,
)
from backend.app.modules.neurorail.telemetry.service import (
    TelemetryService,
    get_telemetry_service,
)
from backend.app.modules.neurorail.telemetry.router import router

__all__ = [
    # Schemas
    "ExecutionMetrics",
    "AggregatedMetrics",
    "RealtimeSnapshot",
    "MetricEvent",
    # Service
    "TelemetryService",
    "get_telemetry_service",
    # Router
    "router",
]
