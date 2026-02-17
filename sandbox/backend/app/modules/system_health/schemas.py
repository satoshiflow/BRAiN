"""
System Health Schemas

Data models for comprehensive system health monitoring.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class HealthStatus(str, Enum):
    """Overall system health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class BottleneckSeverity(str, Enum):
    """Severity of identified bottleneck"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# SUB-COMPONENTS
# =============================================================================

class BottleneckInfo(BaseModel):
    """Information about a system bottleneck"""
    component: str = Field(..., description="Component causing bottleneck")
    location: str = Field(..., description="File/module location")
    severity: BottleneckSeverity
    metric_value: Optional[float] = Field(None, description="Metric value (latency, memory, etc.)")
    metric_unit: Optional[str] = Field(None, description="Unit of metric")
    description: str = Field(..., description="Human-readable description")
    recommendation: str = Field(..., description="Optimization recommendation")


class OptimizationRecommendation(BaseModel):
    """Optimization recommendation"""
    priority: str = Field(..., description="Priority: CRITICAL, HIGH, MEDIUM, LOW")
    category: str = Field(..., description="Category: performance, memory, stability, etc.")
    title: str = Field(..., description="Short title")
    description: str = Field(..., description="Detailed description")
    impact: Optional[str] = Field(None, description="Expected impact")
    effort: Optional[str] = Field(None, description="Implementation effort")


class ImmuneHealthData(BaseModel):
    """Immune system health data"""
    active_issues: int = 0
    critical_issues: int = 0
    last_event_timestamp: Optional[float] = None
    event_rate_per_minute: Optional[float] = None


class ThreatsHealthData(BaseModel):
    """Threats system health data"""
    total_threats: int = 0
    active_threats: int = 0
    critical_threats: int = 0
    mitigated_threats: int = 0
    last_threat_timestamp: Optional[float] = None


class MissionHealthData(BaseModel):
    """Mission system health data"""
    queue_depth: int = 0
    running_missions: int = 0
    pending_missions: int = 0
    completed_today: int = 0
    failed_today: int = 0
    avg_latency_ms: Optional[float] = None
    throughput_per_second: Optional[float] = None


class AgentHealthData(BaseModel):
    """Agent system health data"""
    total_agents: int = 0
    active_agents: int = 0
    idle_agents: int = 0
    avg_utilization: Optional[float] = None


class AuditMetrics(BaseModel):
    """Runtime audit metrics from Runtime Auditor"""
    edge_of_chaos_score: Optional[float] = Field(
        None,
        description="Edge-of-chaos score (optimal: 0.5-0.7)",
        ge=0.0,
        le=1.0
    )
    memory_leak_detected: bool = False
    deadlock_detected: bool = False
    starvation_detected: bool = False
    cascade_failure_detected: bool = False

    # Performance metrics
    avg_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None
    p99_latency_ms: Optional[float] = None
    throughput_per_second: Optional[float] = None

    # Resource metrics
    memory_usage_mb: Optional[float] = None
    memory_trend: Optional[str] = Field(None, description="stable, increasing, decreasing")
    cpu_usage_percent: Optional[float] = None


# =============================================================================
# MAIN SYSTEM HEALTH
# =============================================================================

class SystemHealth(BaseModel):
    """Comprehensive system health overview"""

    # Overall status
    overall_status: HealthStatus = HealthStatus.UNKNOWN
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: Optional[float] = None

    # Sub-system health
    immune_health: Optional[ImmuneHealthData] = None
    threats_health: Optional[ThreatsHealthData] = None
    mission_health: Optional[MissionHealthData] = None
    agent_health: Optional[AgentHealthData] = None

    # Audit metrics (from Runtime Auditor)
    audit_metrics: Optional[AuditMetrics] = None

    # Bottlenecks
    bottlenecks: List[BottleneckInfo] = Field(default_factory=list)

    # Recommendations
    recommendations: List[OptimizationRecommendation] = Field(default_factory=list)

    # Additional metrics
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SystemHealthSummary(BaseModel):
    """Lightweight system health summary for quick checks"""
    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    critical_issues_count: int = 0
    edge_of_chaos_score: Optional[float] = None
    message: Optional[str] = None
