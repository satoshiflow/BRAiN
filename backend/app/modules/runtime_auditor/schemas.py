"""
Runtime Auditor Schemas

Data models for runtime audit metrics and anomaly detection.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# =============================================================================
# RUNTIME METRICS
# =============================================================================

class PerformanceMetrics(BaseModel):
    """Real-time performance metrics"""
    avg_latency_ms: Optional[float] = Field(None, description="Average latency in milliseconds")
    p95_latency_ms: Optional[float] = Field(None, description="P95 latency in milliseconds")
    p99_latency_ms: Optional[float] = Field(None, description="P99 latency in milliseconds")
    throughput_per_second: Optional[float] = Field(None, description="Operations per second")
    samples_count: int = Field(0, description="Number of samples")


class ResourceMetrics(BaseModel):
    """System resource metrics"""
    memory_usage_mb: Optional[float] = Field(None, description="Current memory usage in MB")
    memory_trend: Optional[str] = Field(None, description="Memory trend: stable, increasing, decreasing")
    memory_growth_rate_mb_per_min: Optional[float] = Field(None, description="Memory growth rate")
    cpu_usage_percent: Optional[float] = Field(None, description="CPU usage percentage")
    disk_usage_percent: Optional[float] = Field(None, description="Disk usage percentage")


class QueueMetrics(BaseModel):
    """Mission queue metrics"""
    queue_depth: int = Field(0, description="Current queue depth")
    queue_depth_trend: Optional[str] = Field(None, description="Queue trend: stable, growing, shrinking")
    avg_queue_depth: Optional[float] = Field(None, description="Average queue depth")
    max_queue_depth: int = Field(0, description="Maximum queue depth observed")


class EdgeOfChaosMetrics(BaseModel):
    """
    Edge-of-Chaos metrics

    Optimal range: 0.5 - 0.7
    - Below 0.3: Too ordered (rigid, low adaptability)
    - Above 0.8: Too chaotic (unstable)
    """
    score: Optional[float] = Field(
        None,
        description="Edge-of-chaos score (0.0 - 1.0)",
        ge=0.0,
        le=1.0
    )
    entropy: Optional[float] = Field(None, description="Shannon entropy of system states")
    synchronicity_index: Optional[float] = Field(
        None,
        description="Synchronicity index (0=desynchronized, 1=pathological)",
        ge=0.0,
        le=1.0
    )
    agent_utilization_variance: Optional[float] = Field(None, description="Variance in agent utilization")
    assessment: Optional[str] = Field(None, description="Assessment: optimal, too_ordered, too_chaotic")


# =============================================================================
# ANOMALY DETECTION
# =============================================================================

class AnomalyType(str):
    """Types of detectable anomalies"""
    MEMORY_LEAK = "memory_leak"
    DEADLOCK = "deadlock"
    STARVATION = "starvation"
    CASCADE_FAILURE = "cascade_failure"
    LATENCY_SPIKE = "latency_spike"
    QUEUE_SATURATION = "queue_saturation"


class AnomalyDetection(BaseModel):
    """Detected anomaly"""
    type: str = Field(..., description="Anomaly type")
    severity: str = Field(..., description="Severity: low, medium, high, critical")
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    description: str = Field(..., description="Human-readable description")
    metric_value: Optional[float] = Field(None, description="Related metric value")
    threshold: Optional[float] = Field(None, description="Threshold that was exceeded")
    recommendation: Optional[str] = Field(None, description="Remediation recommendation")


# =============================================================================
# MAIN RUNTIME METRICS
# =============================================================================

class RuntimeMetrics(BaseModel):
    """
    Complete runtime audit metrics

    Used by SystemHealthService to provide AuditMetrics
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    uptime_seconds: float = Field(0.0, description="System uptime")

    # Performance
    performance: PerformanceMetrics = Field(default_factory=PerformanceMetrics)

    # Resources
    resources: ResourceMetrics = Field(default_factory=ResourceMetrics)

    # Queue
    queue: QueueMetrics = Field(default_factory=QueueMetrics)

    # Edge-of-Chaos
    edge_of_chaos: EdgeOfChaosMetrics = Field(default_factory=EdgeOfChaosMetrics)

    # Anomalies
    anomalies: List[AnomalyDetection] = Field(default_factory=list)

    # Flags
    memory_leak_detected: bool = False
    deadlock_detected: bool = False
    starvation_detected: bool = False
    cascade_failure_detected: bool = False

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeAuditorStatus(BaseModel):
    """Runtime auditor status"""
    running: bool = True
    last_collection_timestamp: Optional[datetime] = None
    collection_interval_seconds: float = 60.0
    samples_collected: int = 0
    anomalies_detected: int = 0
