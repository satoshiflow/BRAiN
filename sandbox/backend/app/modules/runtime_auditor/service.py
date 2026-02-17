"""
Runtime Auditor Service

Lightweight runtime monitoring based on BRAiN Master Audit Tool.

Provides:
- Continuous metric collection (no stress tests)
- Real-time anomaly detection
- Edge-of-Chaos score calculation
- Integration with Immune System
"""

import time
import asyncio
import statistics
from datetime import datetime, timedelta
from typing import List, Optional, Deque
from collections import deque
from loguru import logger

# Import psutil for resource monitoring
try:
    import psutil
except ImportError:
    psutil = None
    logger.warning("[RuntimeAuditor] psutil not available - resource metrics disabled")

# Import numpy for statistical analysis
try:
    import numpy as np
    from scipy import stats as scipy_stats
except ImportError:
    np = None
    scipy_stats = None
    logger.warning("[RuntimeAuditor] numpy/scipy not available - advanced analysis disabled")

from app.modules.runtime_auditor.schemas import (
    RuntimeMetrics,
    PerformanceMetrics,
    ResourceMetrics,
    QueueMetrics,
    EdgeOfChaosMetrics,
    AnomalyDetection,
    RuntimeAuditorStatus,
)

# Import for Immune System integration (Phase 2 end)
try:
    from app.modules.immune.core.service import ImmuneService
    from app.modules.immune.schemas import ImmuneEvent, ImmuneSeverity, ImmuneType
except ImportError:
    ImmuneService = None
    logger.warning("[RuntimeAuditor] ImmuneService not available")


class RuntimeAuditor:
    """
    Lightweight runtime auditor for continuous monitoring.

    Based on: backend/tests/brain_master_audit.py
    Adapted for: Production runtime without stress tests

    Key Differences from Master Audit Tool:
    - No stress testing or load generation
    - Continuous passive monitoring
    - Real-time anomaly detection
    - Integration with Immune System
    - Lower overhead
    """

    def __init__(
        self,
        collection_interval: float = 60.0,
        memory_sample_window: int = 60,
        latency_sample_window: int = 100,
        immune_service: Optional[ImmuneService] = None,
    ):
        """
        Initialize Runtime Auditor

        Args:
            collection_interval: Seconds between metric collections (default: 60)
            memory_sample_window: Number of memory samples to keep (default: 60)
            latency_sample_window: Number of latency samples to keep (default: 100)
            immune_service: Optional ImmuneService for event publishing
        """
        self.collection_interval = collection_interval
        self.start_time = time.time()

        # Sample windows
        self.memory_samples: Deque[float] = deque(maxlen=memory_sample_window)
        self.latency_samples: Deque[float] = deque(maxlen=latency_sample_window)
        self.queue_depth_samples: Deque[int] = deque(maxlen=60)

        # Process handle for resource monitoring
        self.process = psutil.Process() if psutil else None

        # Immune System integration
        self.immune_service = immune_service

        # Status tracking
        self.last_collection: Optional[datetime] = None
        self.samples_collected = 0
        self.anomalies_detected = 0

        # Background task
        self.running = False
        self.task: Optional[asyncio.Task] = None

        logger.info(
            f"[RuntimeAuditor] Initialized with {collection_interval}s collection interval"
        )

    # =========================================================================
    # LIFECYCLE MANAGEMENT
    # =========================================================================

    async def start(self):
        """Start background metric collection"""
        if self.running:
            logger.warning("[RuntimeAuditor] Already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._collection_loop())
        logger.info("[RuntimeAuditor] Background collection started")

    async def stop(self):
        """Stop background metric collection"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("[RuntimeAuditor] Background collection stopped")

    async def _collection_loop(self):
        """Background collection loop"""
        while self.running:
            try:
                await self._collect_metrics()
                self.samples_collected += 1
                self.last_collection = datetime.utcnow()

                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[RuntimeAuditor] Collection error: {e}", exc_info=True)
                await asyncio.sleep(self.collection_interval)

    # =========================================================================
    # METRIC COLLECTION
    # =========================================================================

    async def _collect_metrics(self):
        """Collect metrics from various sources"""
        logger.debug("[RuntimeAuditor] Collecting metrics...")

        # Sample memory
        if self.process:
            memory_mb = self._get_memory_usage_mb()
            self.memory_samples.append(memory_mb)

        # TODO: Collect latency samples from API endpoints
        # TODO: Collect queue depth from mission system
        # For now, these will be populated when integrated

    def sample_latency(self, latency_ms: float):
        """
        Record a latency sample.

        This should be called by API endpoints to track request latency.

        Args:
            latency_ms: Request latency in milliseconds
        """
        self.latency_samples.append(latency_ms)

    def sample_queue_depth(self, depth: int):
        """
        Record a queue depth sample.

        This should be called by mission system to track queue depth.

        Args:
            depth: Current queue depth
        """
        self.queue_depth_samples.append(depth)

    # =========================================================================
    # CURRENT METRICS
    # =========================================================================

    async def get_current_metrics(self) -> RuntimeMetrics:
        """
        Get current runtime metrics.

        Returns:
            RuntimeMetrics with all current data
        """
        uptime = time.time() - self.start_time

        # Performance metrics
        performance = self._get_performance_metrics()

        # Resource metrics
        resources = self._get_resource_metrics()

        # Queue metrics
        queue = self._get_queue_metrics()

        # Edge-of-Chaos metrics
        edge_of_chaos = self._get_edge_of_chaos_metrics()

        # Detect anomalies
        anomalies = self._detect_anomalies(performance, resources, queue)

        # Update anomaly count
        self.anomalies_detected += len(anomalies)

        # Publish critical anomalies to Immune System
        await self._publish_critical_anomalies(anomalies)

        # Set flags
        memory_leak = any(a.type == "memory_leak" for a in anomalies)
        deadlock = any(a.type == "deadlock" for a in anomalies)
        starvation = any(a.type == "starvation" for a in anomalies)
        cascade_failure = any(a.type == "cascade_failure" for a in anomalies)

        return RuntimeMetrics(
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime,
            performance=performance,
            resources=resources,
            queue=queue,
            edge_of_chaos=edge_of_chaos,
            anomalies=anomalies,
            memory_leak_detected=memory_leak,
            deadlock_detected=deadlock,
            starvation_detected=starvation,
            cascade_failure_detected=cascade_failure,
            metadata={
                "samples_collected": self.samples_collected,
                "collection_interval": self.collection_interval,
            }
        )

    # =========================================================================
    # SUB-METRIC CALCULATIONS
    # =========================================================================

    def _get_performance_metrics(self) -> PerformanceMetrics:
        """Calculate performance metrics from latency samples"""
        if not self.latency_samples:
            return PerformanceMetrics()

        samples = list(self.latency_samples)
        sorted_samples = sorted(samples)

        avg_latency = statistics.mean(samples)
        p95_latency = sorted_samples[int(len(sorted_samples) * 0.95)] if sorted_samples else None
        p99_latency = sorted_samples[int(len(sorted_samples) * 0.99)] if sorted_samples else None

        # Estimate throughput (samples per second)
        # This is approximate - real throughput would need timestamp tracking
        throughput = len(samples) / self.collection_interval if self.collection_interval > 0 else None

        return PerformanceMetrics(
            avg_latency_ms=avg_latency,
            p95_latency_ms=p95_latency,
            p99_latency_ms=p99_latency,
            throughput_per_second=throughput,
            samples_count=len(samples),
        )

    def _get_resource_metrics(self) -> ResourceMetrics:
        """Calculate resource metrics"""
        if not self.process:
            return ResourceMetrics()

        memory_mb = self._get_memory_usage_mb()

        # Memory trend analysis
        memory_trend = "stable"
        memory_growth_rate = None

        if len(self.memory_samples) >= 10 and np is not None and scipy_stats is not None:
            x = np.arange(len(self.memory_samples))
            y = np.array(list(self.memory_samples))

            slope, _, r_value, p_value, _ = scipy_stats.linregress(x, y)

            # Determine trend
            if abs(slope) < 0.1:  # < 0.1 MB/sample
                memory_trend = "stable"
            elif slope > 0.1:
                memory_trend = "increasing"
            else:
                memory_trend = "decreasing"

            # Growth rate in MB/min
            memory_growth_rate = slope * (60.0 / self.collection_interval)

        # CPU usage
        try:
            cpu_percent = self.process.cpu_percent(interval=0.1)
        except:
            cpu_percent = None

        return ResourceMetrics(
            memory_usage_mb=memory_mb,
            memory_trend=memory_trend,
            memory_growth_rate_mb_per_min=memory_growth_rate,
            cpu_usage_percent=cpu_percent,
        )

    def _get_queue_metrics(self) -> QueueMetrics:
        """Calculate queue metrics"""
        if not self.queue_depth_samples:
            return QueueMetrics()

        samples = list(self.queue_depth_samples)
        avg_depth = statistics.mean(samples)
        max_depth = max(samples)
        current_depth = samples[-1] if samples else 0

        # Queue trend
        queue_trend = "stable"
        if len(samples) >= 5:
            recent_avg = statistics.mean(samples[-5:])
            older_avg = statistics.mean(samples[:5])

            if recent_avg > older_avg * 1.5:
                queue_trend = "growing"
            elif recent_avg < older_avg * 0.7:
                queue_trend = "shrinking"

        return QueueMetrics(
            queue_depth=current_depth,
            queue_depth_trend=queue_trend,
            avg_queue_depth=avg_depth,
            max_queue_depth=max_depth,
        )

    def _get_edge_of_chaos_metrics(self) -> EdgeOfChaosMetrics:
        """
        Calculate Edge-of-Chaos metrics.

        Optimal range: 0.5 - 0.7
        """
        if len(self.queue_depth_samples) < 10:
            return EdgeOfChaosMetrics()

        # Calculate entropy of queue depth states
        entropy = self._calculate_entropy(list(self.queue_depth_samples))

        # Calculate synchronicity (low variance = high synchronicity = bad)
        if len(self.queue_depth_samples) > 1:
            variance = statistics.variance(self.queue_depth_samples)
            mean_depth = statistics.mean(self.queue_depth_samples)
            cv = (variance ** 0.5) / mean_depth if mean_depth > 0 else 0
            synchronicity = 1.0 / (1.0 + cv)
        else:
            synchronicity = None

        # Calculate edge-of-chaos score
        # Combines entropy and variance
        if entropy is not None:
            normalized_entropy = min(entropy / 5.0, 1.0)  # Assume max entropy ~5 bits
            normalized_variance = min(synchronicity, 1.0) if synchronicity else 0.5
            score = (normalized_entropy + (1.0 - normalized_variance)) / 2.0
        else:
            score = None

        # Assessment
        assessment = None
        if score is not None:
            if score < 0.3:
                assessment = "too_ordered"
            elif score > 0.8:
                assessment = "too_chaotic"
            else:
                assessment = "optimal"

        return EdgeOfChaosMetrics(
            score=score,
            entropy=entropy,
            synchronicity_index=synchronicity,
            agent_utilization_variance=None,  # TODO: Calculate from agent metrics
            assessment=assessment,
        )

    # =========================================================================
    # ANOMALY DETECTION
    # =========================================================================

    def _detect_anomalies(
        self,
        performance: PerformanceMetrics,
        resources: ResourceMetrics,
        queue: QueueMetrics,
    ) -> List[AnomalyDetection]:
        """
        Detect anomalies based on current metrics.

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Memory leak detection
        if self._detect_memory_leak():
            anomalies.append(AnomalyDetection(
                type="memory_leak",
                severity="critical",
                description="Memory leak detected via trend analysis",
                metric_value=resources.memory_growth_rate_mb_per_min,
                threshold=0.5,  # MB/min
                recommendation="Profile memory usage with memory_profiler, check for object retention",
            ))

        # Latency spike detection
        if performance.p95_latency_ms and performance.p95_latency_ms > 1000:
            severity = "high" if performance.p95_latency_ms > 2000 else "medium"
            anomalies.append(AnomalyDetection(
                type="latency_spike",
                severity=severity,
                description=f"P95 latency ({performance.p95_latency_ms:.0f}ms) exceeds threshold",
                metric_value=performance.p95_latency_ms,
                threshold=1000.0,
                recommendation="Check database queries, optimize slow endpoints, consider caching",
            ))

        # Queue saturation detection
        if queue.queue_depth > 500:
            severity = "high" if queue.queue_depth > 1000 else "medium"
            anomalies.append(AnomalyDetection(
                type="queue_saturation",
                severity=severity,
                description=f"Mission queue depth ({queue.queue_depth}) is high",
                metric_value=float(queue.queue_depth),
                threshold=500.0,
                recommendation="Increase worker capacity, implement backpressure, or optimize mission execution",
            ))

        # Deadlock detection (queue not moving)
        if self._detect_deadlock():
            anomalies.append(AnomalyDetection(
                type="deadlock",
                severity="critical",
                description="Potential deadlock detected - queue not moving",
                recommendation="Review locking mechanisms, add timeout guards, restart affected workers",
            ))

        return anomalies

    def _detect_memory_leak(self) -> bool:
        """
        Detect memory leak using linear regression on memory samples.

        Returns:
            True if memory leak detected
        """
        if len(self.memory_samples) < 10 or not np or not scipy_stats:
            return False

        x = np.arange(len(self.memory_samples))
        y = np.array(list(self.memory_samples))

        slope, _, r_value, p_value, _ = scipy_stats.linregress(x, y)

        # Memory leak criteria:
        # 1. Significant positive slope (> 0.5 MB per sample)
        # 2. High correlation (r² > 0.8)
        # 3. Statistically significant (p < 0.05)
        leak_detected = (slope > 0.5) and (r_value**2 > 0.8) and (p_value < 0.05)

        return leak_detected

    def _detect_deadlock(self) -> bool:
        """
        Detect deadlock: queue depth unchanged for extended period.

        Returns:
            True if deadlock suspected
        """
        if len(self.queue_depth_samples) < 10:
            return False

        # Check last 10 samples for identical non-zero queue depth
        recent = list(self.queue_depth_samples)[-10:]
        unique_values = set(recent)

        # Deadlock if all same and non-zero
        if len(unique_values) == 1 and list(unique_values)[0] > 0:
            return True

        return False

    # =========================================================================
    # IMMUNE SYSTEM INTEGRATION
    # =========================================================================

    async def _publish_critical_anomalies(self, anomalies: List[AnomalyDetection]):
        """
        Publish critical anomalies to Immune System.

        Args:
            anomalies: List of detected anomalies
        """
        if not self.immune_service:
            return

        for anomaly in anomalies:
            if anomaly.severity in ["critical", "high"]:
                try:
                    # Map severity
                    severity_map = {
                        "critical": ImmuneSeverity.CRITICAL,
                        "high": ImmuneSeverity.WARNING,
                        "medium": ImmuneSeverity.INFO,
                        "low": ImmuneSeverity.INFO,
                    }

                    # Map type
                    type_map = {
                        "memory_leak": ImmuneType.RESOURCE_EXHAUSTION,
                        "deadlock": ImmuneType.AGENT_FAILURE,
                        "cascade_failure": ImmuneType.AGENT_FAILURE,
                        "latency_spike": ImmuneType.PERFORMANCE_DEGRADATION,
                        "queue_saturation": ImmuneType.PERFORMANCE_DEGRADATION,
                    }

                    event = ImmuneEvent(
                        severity=severity_map.get(anomaly.severity, ImmuneSeverity.INFO),
                        type=type_map.get(anomaly.type, ImmuneType.UNKNOWN),
                        message=anomaly.description,
                        module="runtime_auditor",
                        meta={
                            "anomaly_type": anomaly.type,
                            "metric_value": anomaly.metric_value,
                            "threshold": anomaly.threshold,
                            "recommendation": anomaly.recommendation,
                        }
                    )

                    await self.immune_service.publish_event(event)

                    logger.info(
                        f"[RuntimeAuditor] Published {anomaly.severity} anomaly to Immune System: {anomaly.type}"
                    )

                except Exception as e:
                    logger.error(f"[RuntimeAuditor] Failed to publish to Immune System: {e}")

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        if not self.process:
            return 0.0

        mem_info = self.process.memory_info()
        return mem_info.rss / 1024 / 1024  # Convert to MB

    def _calculate_entropy(self, samples: List[int]) -> Optional[float]:
        """
        Calculate Shannon entropy of samples.

        Args:
            samples: List of integer samples

        Returns:
            Entropy in bits, or None if insufficient data
        """
        if not samples or not np:
            return None

        # Create histogram
        unique, counts = np.unique(samples, return_counts=True)
        total = len(samples)

        if total == 0:
            return None

        # Calculate probabilities
        probabilities = counts / total

        # Shannon entropy
        entropy = -np.sum(probabilities * np.log2(probabilities + 1e-10))

        return float(entropy)

    # =========================================================================
    # STATUS
    # =========================================================================

    def get_status(self) -> RuntimeAuditorStatus:
        """Get auditor status"""
        return RuntimeAuditorStatus(
            running=self.running,
            last_collection_timestamp=self.last_collection,
            collection_interval_seconds=self.collection_interval,
            samples_collected=self.samples_collected,
            anomalies_detected=self.anomalies_detected,
        )
