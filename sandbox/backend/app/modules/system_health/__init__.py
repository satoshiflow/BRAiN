"""
System Health Module

Aggregates health data from all BRAiN modules:
- Immune System
- Threats
- Metrics
- Mission Queue
- Agent Status
- Runtime Audit Metrics

Provides comprehensive system health overview for monitoring and diagnostics.
"""

from app.modules.system_health.service import SystemHealthService
from app.modules.system_health.schemas import (
    SystemHealth,
    HealthStatus,
    BottleneckInfo,
    OptimizationRecommendation,
)

__all__ = [
    "SystemHealthService",
    "SystemHealth",
    "HealthStatus",
    "BottleneckInfo",
    "OptimizationRecommendation",
]
