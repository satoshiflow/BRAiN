"""
System Health Service

Aggregates health data from all BRAiN modules and provides
comprehensive system health overview.
"""

import time
from datetime import datetime
from typing import Optional, List, Any
from loguru import logger

from app.modules.system_health.schemas import (
    SystemHealth,
    SystemHealthSummary,
    HealthStatus,
    ImmuneHealthData,
    ThreatsHealthData,
    MissionHealthData,
    AgentHealthData,
    AuditMetrics,
    BottleneckInfo,
    BottleneckSeverity,
    OptimizationRecommendation,
)

# Import sub-systems (with fallback if not available)
try:
    from app.modules.immune.core.service import ImmuneService
except ImportError:
    ImmuneService = None
    logger.warning("[SystemHealth] ImmuneService not available")

try:
    from app.modules.threats.service import ThreatsService
except ImportError:
    ThreatsService = None
    logger.warning("[SystemHealth] ThreatsService not available")

try:
    from modules.mission_system.service import MissionService
except ImportError:
    MissionService = None
    logger.warning("[SystemHealth] MissionService not available")

try:
    from app.modules.runtime_auditor.service import RuntimeAuditor
    from app.modules.runtime_auditor.schemas import RuntimeMetrics
except ImportError:
    RuntimeAuditor = None
    RuntimeMetrics = None
    logger.warning("[SystemHealth] RuntimeAuditor not available")


class SystemHealthService:
    """
    Central health orchestration service.

    Aggregates health data from:
    - Immune System
    - Threats System
    - Mission Queue
    - Agent System
    - Runtime Auditor (Phase 2)

    Provides:
    - Comprehensive health overview
    - Bottleneck detection
    - Optimization recommendations
    """

    def __init__(self):
        self.start_time = time.time()

        # Initialize sub-services (singleton pattern)
        self.immune_service = ImmuneService() if ImmuneService else None
        # Note: Other services will be injected via dependency injection
        # For now, we use direct imports where possible

    # =========================================================================
    # MAIN HEALTH CHECK
    # =========================================================================

    async def get_comprehensive_health(
        self,
        runtime_auditor: Optional[Any] = None,  # Will be injected in Phase 2
    ) -> SystemHealth:
        """
        Get comprehensive system health overview.

        Args:
            runtime_auditor: Optional RuntimeAuditor instance for audit metrics

        Returns:
            SystemHealth with all aggregated data
        """
        logger.debug("[SystemHealth] Gathering comprehensive health data...")

        # Collect health data from all sub-systems
        immune_health = await self._get_immune_health()
        threats_health = await self._get_threats_health()
        mission_health = await self._get_mission_health()
        agent_health = await self._get_agent_health()
        audit_metrics = await self._get_audit_metrics(runtime_auditor)

        # Determine overall status
        overall_status = self._determine_overall_status(
            immune_health,
            threats_health,
            mission_health,
            audit_metrics,
        )

        # Identify bottlenecks
        bottlenecks = await self._identify_bottlenecks(
            mission_health,
            audit_metrics,
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            overall_status,
            bottlenecks,
            audit_metrics,
        )

        # Calculate uptime
        uptime = time.time() - self.start_time

        health = SystemHealth(
            overall_status=overall_status,
            timestamp=datetime.utcnow(),
            uptime_seconds=uptime,
            immune_health=immune_health,
            threats_health=threats_health,
            mission_health=mission_health,
            agent_health=agent_health,
            audit_metrics=audit_metrics,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
            metadata={
                "version": "0.5.0",
                "environment": "development",  # TODO: from config
            }
        )

        logger.info(
            f"[SystemHealth] Overall status: {overall_status.value} | "
            f"Bottlenecks: {len(bottlenecks)} | "
            f"Recommendations: {len(recommendations)}"
        )

        return health

    async def get_health_summary(self) -> SystemHealthSummary:
        """
        Get lightweight health summary for quick checks.

        Returns:
            SystemHealthSummary with minimal data
        """
        health = await self.get_comprehensive_health()

        # Count critical issues
        critical_count = 0
        if health.immune_health:
            critical_count += health.immune_health.critical_issues
        if health.threats_health:
            critical_count += health.threats_health.critical_threats
        critical_count += len([b for b in health.bottlenecks if b.severity == BottleneckSeverity.CRITICAL])

        return SystemHealthSummary(
            status=health.overall_status,
            timestamp=health.timestamp,
            critical_issues_count=critical_count,
            edge_of_chaos_score=health.audit_metrics.edge_of_chaos_score if health.audit_metrics else None,
            message=self._get_status_message(health.overall_status, critical_count),
        )

    # =========================================================================
    # SUB-SYSTEM HEALTH COLLECTORS
    # =========================================================================

    async def _get_immune_health(self) -> Optional[ImmuneHealthData]:
        """Get health data from Immune System"""
        if not self.immune_service:
            return None

        try:
            summary = self.immune_service.health_summary(minutes=60)
            recent_events = self.immune_service.get_recent_events(minutes=5)

            last_event_ts = None
            if summary.last_events:
                last_event_ts = summary.last_events[-1].created_at.timestamp()

            event_rate = len(recent_events) / 5.0  # events per minute over last 5 min

            return ImmuneHealthData(
                active_issues=summary.active_issues,
                critical_issues=summary.critical_issues,
                last_event_timestamp=last_event_ts,
                event_rate_per_minute=event_rate,
            )
        except Exception as e:
            logger.error(f"[SystemHealth] Failed to get immune health: {e}")
            return None

    async def _get_threats_health(self) -> Optional[ThreatsHealthData]:
        """Get health data from Threats System"""
        # TODO: Implement when ThreatsService API is available
        # For now, return mock data
        return ThreatsHealthData(
            total_threats=0,
            active_threats=0,
            critical_threats=0,
            mitigated_threats=0,
        )

    async def _get_mission_health(self) -> Optional[MissionHealthData]:
        """Get health data from Mission System"""
        try:
            from modules.missions.queue import MissionQueue
            from app.core.config import get_settings

            settings = get_settings()
            queue = MissionQueue(redis_url=settings.REDIS_URL)
            metrics = await queue.get_health_metrics()

            return MissionHealthData(**metrics)
        except Exception as e:
            logger.error(f"Failed to get mission health: {e}")
            # Return None to indicate health check failed
            return None

    async def _get_agent_health(self) -> Optional[AgentHealthData]:
        """Get health data from Agent System"""
        try:
            # Use hardcoded agent list from agents.py as a basic count
            # TODO: Implement proper agent registry with runtime state tracking
            from app.api.routes.agents import AGENTS

            total = len(AGENTS)

            # Runtime state tracking not yet implemented
            # This would require tracking which agents are actively executing missions
            return AgentHealthData(
                total_agents=total,
                active_agents=0,  # Requires runtime state tracking
                idle_agents=0,    # Requires runtime state tracking
            )
        except Exception as e:
            logger.error(f"Failed to get agent health: {e}")
            return None

    async def _get_audit_metrics(
        self,
        runtime_auditor: Optional["RuntimeAuditor"] = None,
    ) -> Optional[AuditMetrics]:
        """
        Get audit metrics from Runtime Auditor.

        Args:
            runtime_auditor: RuntimeAuditor instance

        Returns:
            AuditMetrics or None if not available
        """
        if not runtime_auditor:
            # Return placeholder if no runtime auditor
            return AuditMetrics(
                edge_of_chaos_score=None,
                memory_leak_detected=False,
                deadlock_detected=False,
                starvation_detected=False,
                cascade_failure_detected=False,
            )

        # Get real metrics from RuntimeAuditor
        try:
            runtime_metrics = await runtime_auditor.get_current_metrics()

            # Convert RuntimeMetrics to AuditMetrics
            return AuditMetrics(
                edge_of_chaos_score=runtime_metrics.edge_of_chaos.score,
                memory_leak_detected=runtime_metrics.memory_leak_detected,
                deadlock_detected=runtime_metrics.deadlock_detected,
                starvation_detected=runtime_metrics.starvation_detected,
                cascade_failure_detected=runtime_metrics.cascade_failure_detected,
                avg_latency_ms=runtime_metrics.performance.avg_latency_ms,
                p95_latency_ms=runtime_metrics.performance.p95_latency_ms,
                p99_latency_ms=runtime_metrics.performance.p99_latency_ms,
                throughput_per_second=runtime_metrics.performance.throughput_per_second,
                memory_usage_mb=runtime_metrics.resources.memory_usage_mb,
                memory_trend=runtime_metrics.resources.memory_trend,
                cpu_usage_percent=runtime_metrics.resources.cpu_usage_percent,
            )
        except Exception as e:
            logger.error(f"[SystemHealth] Failed to get audit metrics: {e}")
            return None

    # =========================================================================
    # STATUS DETERMINATION
    # =========================================================================

    def _determine_overall_status(
        self,
        immune_health: Optional[ImmuneHealthData],
        threats_health: Optional[ThreatsHealthData],
        mission_health: Optional[MissionHealthData],
        audit_metrics: Optional[AuditMetrics],
    ) -> HealthStatus:
        """
        Determine overall system health status based on sub-system health.

        Logic:
        - CRITICAL: Any critical issues detected
        - DEGRADED: High resource usage, warnings, or sub-optimal metrics
        - HEALTHY: All systems nominal
        - UNKNOWN: Insufficient data
        """
        # Check for critical issues
        if immune_health and immune_health.critical_issues > 0:
            return HealthStatus.CRITICAL

        if threats_health and threats_health.critical_threats > 0:
            return HealthStatus.CRITICAL

        if audit_metrics:
            if audit_metrics.memory_leak_detected or audit_metrics.deadlock_detected:
                return HealthStatus.CRITICAL

            # Check edge-of-chaos score
            if audit_metrics.edge_of_chaos_score is not None:
                score = audit_metrics.edge_of_chaos_score
                if score < 0.3 or score > 0.8:
                    return HealthStatus.DEGRADED

            # Check for warnings
            if audit_metrics.starvation_detected or audit_metrics.cascade_failure_detected:
                return HealthStatus.DEGRADED

        # Check mission queue depth
        if mission_health and mission_health.queue_depth > 1000:
            return HealthStatus.DEGRADED

        # All checks passed
        return HealthStatus.HEALTHY

    # =========================================================================
    # BOTTLENECK DETECTION
    # =========================================================================

    async def _identify_bottlenecks(
        self,
        mission_health: Optional[MissionHealthData],
        audit_metrics: Optional[AuditMetrics],
    ) -> List[BottleneckInfo]:
        """
        Identify system bottlenecks based on health data.

        Returns:
            List of BottleneckInfo
        """
        bottlenecks = []

        # Check latency
        if audit_metrics and audit_metrics.p95_latency_ms is not None:
            if audit_metrics.p95_latency_ms > 1000:  # > 1 second
                bottlenecks.append(BottleneckInfo(
                    component="Mission API",
                    location="backend/api/routes/missions.py",
                    severity=BottleneckSeverity.HIGH if audit_metrics.p95_latency_ms > 2000 else BottleneckSeverity.MEDIUM,
                    metric_value=audit_metrics.p95_latency_ms,
                    metric_unit="ms",
                    description=f"P95 latency is {audit_metrics.p95_latency_ms:.0f}ms (threshold: 1000ms)",
                    recommendation="Consider adding caching, optimizing database queries, or implementing request batching",
                ))

        # Check memory usage
        if audit_metrics and audit_metrics.memory_usage_mb is not None:
            if audit_metrics.memory_usage_mb > 1000:  # > 1GB
                bottlenecks.append(BottleneckInfo(
                    component="Memory Usage",
                    location="System-wide",
                    severity=BottleneckSeverity.HIGH if audit_metrics.memory_usage_mb > 2000 else BottleneckSeverity.MEDIUM,
                    metric_value=audit_metrics.memory_usage_mb,
                    metric_unit="MB",
                    description=f"Memory usage is {audit_metrics.memory_usage_mb:.0f}MB",
                    recommendation="Profile memory usage with memory_profiler, check for memory leaks, consider increasing resources",
                ))

        # Check queue depth
        if mission_health and mission_health.queue_depth > 500:
            bottlenecks.append(BottleneckInfo(
                component="Mission Queue",
                location="backend/modules/mission_system/queue.py",
                severity=BottleneckSeverity.MEDIUM,
                metric_value=mission_health.queue_depth,
                metric_unit="missions",
                description=f"Mission queue depth is {mission_health.queue_depth} missions",
                recommendation="Increase worker capacity, optimize mission execution, or implement backpressure",
            ))

        return bottlenecks

    # =========================================================================
    # RECOMMENDATIONS
    # =========================================================================

    def _generate_recommendations(
        self,
        overall_status: HealthStatus,
        bottlenecks: List[BottleneckInfo],
        audit_metrics: Optional[AuditMetrics],
    ) -> List[OptimizationRecommendation]:
        """
        Generate optimization recommendations based on health data.

        Returns:
            List of OptimizationRecommendation
        """
        recommendations = []

        # Critical status recommendations
        if overall_status == HealthStatus.CRITICAL:
            recommendations.append(OptimizationRecommendation(
                priority="CRITICAL",
                category="stability",
                title="System in Critical State",
                description="Immediate attention required. Review immune system events and bottlenecks.",
                impact="System stability at risk",
                effort="Immediate",
            ))

        # Edge-of-chaos recommendations
        if audit_metrics and audit_metrics.edge_of_chaos_score is not None:
            score = audit_metrics.edge_of_chaos_score
            if score < 0.3:
                recommendations.append(OptimizationRecommendation(
                    priority="MEDIUM",
                    category="performance",
                    title="System Too Ordered",
                    description=f"Edge-of-chaos score ({score:.2f}) is below optimal range (0.5-0.7). System may lack adaptability.",
                    impact="Reduced system flexibility",
                    effort="Medium - Review agent concurrency settings",
                ))
            elif score > 0.8:
                recommendations.append(OptimizationRecommendation(
                    priority="HIGH",
                    category="stability",
                    title="System Too Chaotic",
                    description=f"Edge-of-chaos score ({score:.2f}) is above optimal range (0.5-0.7). System may lack stability.",
                    impact="Reduced system stability",
                    effort="Medium - Implement backpressure and rate limiting",
                ))

        # Bottleneck-specific recommendations
        for bottleneck in bottlenecks:
            if bottleneck.severity in [BottleneckSeverity.HIGH, BottleneckSeverity.CRITICAL]:
                recommendations.append(OptimizationRecommendation(
                    priority="HIGH" if bottleneck.severity == BottleneckSeverity.HIGH else "CRITICAL",
                    category="performance",
                    title=f"Bottleneck: {bottleneck.component}",
                    description=bottleneck.description,
                    impact=bottleneck.recommendation,
                    effort="Variable",
                ))

        # General recommendations (always)
        if not recommendations:
            recommendations.append(OptimizationRecommendation(
                priority="LOW",
                category="monitoring",
                title="Enable Continuous Monitoring",
                description="Consider enabling distributed tracing (OpenTelemetry) for detailed performance insights.",
                impact="Better observability and faster issue detection",
                effort="Medium - Requires instrumentation",
            ))

        return recommendations

    # =========================================================================
    # UTILITIES
    # =========================================================================

    def _get_status_message(self, status: HealthStatus, critical_count: int) -> str:
        """Generate status message"""
        messages = {
            HealthStatus.HEALTHY: "All systems operational",
            HealthStatus.DEGRADED: f"System degraded - {critical_count} issues detected",
            HealthStatus.CRITICAL: f"Critical issues detected - immediate attention required",
            HealthStatus.UNKNOWN: "System health unknown - insufficient data",
        }
        return messages.get(status, "Status unknown")
