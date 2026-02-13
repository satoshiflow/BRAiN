"""
Validation Test for BRAiN Master Audit Script

Tests the audit script structure, imports, and helper functions
without requiring the backend to be running.

Author: Claude (Test Engineer)
Project: BRAIN Framework by FalkLabs / Olaf Falk
"""

import sys
import os
import pytest
import numpy as np
from datetime import datetime

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import audit components
from backend.tests.brain_master_audit import (
    BrainMasterAuditor,
    PerformanceMetrics,
    StabilityMetrics,
    BreakingPointMetrics,
    AuditReport
)


class TestAuditDataStructures:
    """Test audit data structures"""

    def test_performance_metrics_creation(self):
        """Test PerformanceMetrics dataclass"""
        metrics = PerformanceMetrics(
            test_scale=100,
            total_missions=100,
            missions_completed=95,
            missions_failed=5,
            duration_seconds=2.5,
            throughput_per_second=38.0,
            avg_latency_ms=45.2,
            p95_latency_ms=89.3,
            p99_latency_ms=125.7,
            peak_memory_mb=256.3,
            avg_memory_mb=248.1,
            memory_leak_detected=False,
            complexity_order="O(n)"
        )

        assert metrics.test_scale == 100
        assert metrics.missions_completed == 95
        assert metrics.throughput_per_second == 38.0
        assert not metrics.memory_leak_detected

    def test_stability_metrics_creation(self):
        """Test StabilityMetrics dataclass"""
        metrics = StabilityMetrics(
            agent_utilization_mean=0.75,
            agent_utilization_std=0.12,
            agent_utilization_distribution=[0.7, 0.8, 0.75, 0.72],
            completion_rate=0.95,
            failure_rate=0.03,
            timeout_rate=0.02,
            synchronicity_index=0.45,
            entropy=3.2,
            edge_of_chaos_score=0.62,
            deadlock_detected=False,
            starvation_detected=False,
            cascade_failure_detected=False
        )

        assert metrics.agent_utilization_mean == 0.75
        assert metrics.entropy == 3.2
        assert not metrics.deadlock_detected

    def test_breaking_point_metrics_creation(self):
        """Test BreakingPointMetrics dataclass"""
        metrics = BreakingPointMetrics(
            max_missions_concurrent=500,
            max_agents_concurrent=10,
            max_throughput_achieved=45.5,
            bottleneck_component="Redis Queue",
            bottleneck_location="backend/modules/mission_system/queue.py:160",
            critical_failure_mode="Queue saturation at 1000 missions",
            recovery_time_seconds=8.5
        )

        assert metrics.max_missions_concurrent == 500
        assert metrics.bottleneck_component == "Redis Queue"
        assert metrics.recovery_time_seconds == 8.5


class TestAuditHelperFunctions:
    """Test audit helper functions"""

    def test_memory_measurement(self):
        """Test memory measurement"""
        auditor = BrainMasterAuditor()
        memory = auditor.measure_memory()

        assert isinstance(memory, float)
        assert memory > 0  # Should have some memory usage
        assert memory < 100000  # Sanity check: < 100GB

    def test_memory_sampling(self):
        """Test memory sampling"""
        auditor = BrainMasterAuditor()

        auditor.sample_memory()
        auditor.sample_memory()
        auditor.sample_memory()

        assert len(auditor.memory_samples) == 3
        assert all(isinstance(m, float) for m in auditor.memory_samples)

    def test_memory_leak_detection_no_leak(self):
        """Test memory leak detection with stable memory"""
        auditor = BrainMasterAuditor()

        # Simulate stable memory (no leak)
        auditor.memory_samples = [100.0 + i * 0.1 for i in range(20)]

        leak_detected = auditor.detect_memory_leak()

        # Should not detect leak with minimal slope
        assert not leak_detected

    def test_memory_leak_detection_with_leak(self):
        """Test memory leak detection with growing memory"""
        auditor = BrainMasterAuditor()

        # Simulate memory leak (significant upward trend)
        auditor.memory_samples = [100.0 + i * 2.0 for i in range(20)]

        leak_detected = auditor.detect_memory_leak()

        # Should detect leak with significant slope
        assert leak_detected

    def test_complexity_estimation(self):
        """Test algorithmic complexity estimation"""
        auditor = BrainMasterAuditor()

        # Linear complexity: O(n)
        scale_points = [(100, 1.0), (200, 2.0), (300, 3.0), (400, 4.0)]
        complexity = auditor.estimate_complexity(scale_points)

        assert "O(n)" in complexity or "O(log n)" in complexity

    def test_complexity_estimation_quadratic(self):
        """Test quadratic complexity estimation"""
        auditor = BrainMasterAuditor()

        # Quadratic complexity: O(n²)
        scale_points = [(10, 1.0), (20, 4.0), (30, 9.0), (40, 16.0)]
        complexity = auditor.estimate_complexity(scale_points)

        assert "O(n²)" in complexity

    def test_synchronicity_calculation(self):
        """Test synchronicity index calculation"""
        auditor = BrainMasterAuditor()

        # Healthy: varied queue lengths
        timeline_healthy = [
            {"timestamp": i, "queue_length": 50 + i * 5} for i in range(10)
        ]
        sync_healthy = auditor._calculate_synchronicity_index(timeline_healthy)

        # Pathological: constant queue length
        timeline_pathological = [
            {"timestamp": i, "queue_length": 100} for i in range(10)
        ]
        sync_pathological = auditor._calculate_synchronicity_index(timeline_pathological)

        # Healthy should have lower synchronicity than pathological
        assert sync_healthy < sync_pathological
        assert 0.0 <= sync_healthy <= 1.0
        assert 0.0 <= sync_pathological <= 1.0

    def test_entropy_calculation(self):
        """Test system entropy calculation"""
        auditor = BrainMasterAuditor()

        # High entropy: uniform distribution
        state_dist_high = {f"state_{i}": 10 for i in range(10)}
        entropy_high = auditor._calculate_system_entropy(state_dist_high)

        # Low entropy: concentrated distribution
        state_dist_low = {"state_0": 90, "state_1": 10}
        entropy_low = auditor._calculate_system_entropy(state_dist_low)

        # High entropy distribution should have higher entropy
        assert entropy_high > entropy_low
        assert entropy_high > 0
        assert entropy_low > 0

    def test_edge_of_chaos_calculation(self):
        """Test edge of chaos score calculation"""
        auditor = BrainMasterAuditor()

        # Optimal: balanced entropy and variance
        score_optimal = auditor._calculate_edge_of_chaos_score(entropy=3.0, utilization_std=0.25)

        # Too ordered: low entropy and variance
        score_ordered = auditor._calculate_edge_of_chaos_score(entropy=0.5, utilization_std=0.05)

        # Too chaotic: high entropy and variance
        score_chaotic = auditor._calculate_edge_of_chaos_score(entropy=4.5, utilization_std=0.45)

        assert 0.0 <= score_optimal <= 1.0
        assert 0.0 <= score_ordered <= 1.0
        assert 0.0 <= score_chaotic <= 1.0

        # Optimal should be in middle range
        assert 0.4 <= score_optimal <= 0.8

    def test_deadlock_detection_positive(self):
        """Test deadlock detection with deadlock"""
        auditor = BrainMasterAuditor()

        # Simulated deadlock: constant non-zero queue length
        timeline = [
            {"timestamp": i, "queue_length": 100} for i in range(15)
        ]

        deadlock = auditor._detect_deadlock(timeline)

        assert deadlock

    def test_deadlock_detection_negative(self):
        """Test deadlock detection without deadlock"""
        auditor = BrainMasterAuditor()

        # Simulated healthy: varying queue length
        timeline = [
            {"timestamp": i, "queue_length": 50 + i * 5} for i in range(15)
        ]

        deadlock = auditor._detect_deadlock(timeline)

        assert not deadlock

    def test_starvation_detection_positive(self):
        """Test starvation detection with starvation"""
        auditor = BrainMasterAuditor()

        # Simulated starvation: mostly zero utilization
        utilization = [0.0] * 15 + [0.1] * 5

        starvation = auditor._detect_starvation(utilization)

        assert starvation

    def test_starvation_detection_negative(self):
        """Test starvation detection without starvation"""
        auditor = BrainMasterAuditor()

        # Simulated healthy: good utilization
        utilization = [0.6, 0.7, 0.8, 0.65, 0.75, 0.7, 0.8, 0.6, 0.75, 0.7]

        starvation = auditor._detect_starvation(utilization)

        assert not starvation

    def test_cascade_failure_detection_positive(self):
        """Test cascade failure detection with cascade"""
        auditor = BrainMasterAuditor()

        # Simulated cascade: 5 failures within 0.5 seconds
        failure_timeline = [1.0, 1.1, 1.2, 1.3, 1.4]

        cascade = auditor._detect_cascade_failure(failure_timeline)

        assert cascade

    def test_cascade_failure_detection_negative(self):
        """Test cascade failure detection without cascade"""
        auditor = BrainMasterAuditor()

        # Simulated normal: failures spread out
        failure_timeline = [1.0, 5.0, 10.0, 15.0, 20.0]

        cascade = auditor._detect_cascade_failure(failure_timeline)

        assert not cascade


class TestAuditReportGeneration:
    """Test audit report generation"""

    def test_report_structure(self):
        """Test audit report structure"""
        report = AuditReport(
            timestamp=datetime.now().isoformat(),
            brain_version="0.5.0",
            test_environment={"cpu_count": 8},
            phase_a_results=[],
            phase_b_results=StabilityMetrics(
                agent_utilization_mean=0.75,
                agent_utilization_std=0.12,
                agent_utilization_distribution=[],
                completion_rate=0.95,
                failure_rate=0.03,
                timeout_rate=0.02,
                synchronicity_index=0.45,
                entropy=3.2,
                edge_of_chaos_score=0.62,
                deadlock_detected=False,
                starvation_detected=False,
                cascade_failure_detected=False
            ),
            phase_c_results=BreakingPointMetrics(
                max_missions_concurrent=500,
                max_agents_concurrent=10,
                max_throughput_achieved=45.5,
                bottleneck_component="Redis",
                bottleneck_location="queue.py",
                critical_failure_mode="Saturation",
                recovery_time_seconds=8.5
            ),
            optimization_recommendations=["Test recommendation"],
            critical_bottlenecks=[]
        )

        assert report.brain_version == "0.5.0"
        assert report.phase_b_results.entropy == 3.2
        assert report.phase_c_results.max_throughput_achieved == 45.5

    def test_markdown_report_generation(self):
        """Test markdown report generation"""
        auditor = BrainMasterAuditor()

        # Create minimal report
        report = AuditReport(
            timestamp=datetime.now().isoformat(),
            brain_version="0.5.0",
            test_environment={"cpu_count": 8},
            phase_a_results=[
                PerformanceMetrics(
                    test_scale=100,
                    total_missions=100,
                    missions_completed=95,
                    missions_failed=5,
                    duration_seconds=2.5,
                    throughput_per_second=38.0,
                    avg_latency_ms=45.2,
                    p95_latency_ms=89.3,
                    p99_latency_ms=125.7,
                    peak_memory_mb=256.3,
                    avg_memory_mb=248.1,
                    memory_leak_detected=False,
                    complexity_order="O(n)"
                )
            ],
            phase_b_results=StabilityMetrics(
                agent_utilization_mean=0.75,
                agent_utilization_std=0.12,
                agent_utilization_distribution=[],
                completion_rate=0.95,
                failure_rate=0.03,
                timeout_rate=0.02,
                synchronicity_index=0.45,
                entropy=3.2,
                edge_of_chaos_score=0.62,
                deadlock_detected=False,
                starvation_detected=False,
                cascade_failure_detected=False
            ),
            phase_c_results=BreakingPointMetrics(
                max_missions_concurrent=500,
                max_agents_concurrent=10,
                max_throughput_achieved=45.5,
                bottleneck_component="Redis",
                bottleneck_location="queue.py",
                critical_failure_mode="Saturation",
                recovery_time_seconds=8.5
            ),
            optimization_recommendations=["Test recommendation"],
            critical_bottlenecks=[]
        )

        # Generate markdown report to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            output_path = f.name

        try:
            auditor.save_report_markdown(report, output_path)

            # Verify file was created and contains expected content
            with open(output_path, 'r') as f:
                content = f.read()

            assert "# BRAIN Master Audit Report" in content
            assert "Phase A: Performance Stress Test" in content
            assert "Phase B: Dynamic Stability Analysis" in content
            assert "Phase C: Breaking Point Definition" in content
            assert "0.5.0" in content
            assert "O(n)" in content

        finally:
            # Clean up temp file
            if os.path.exists(output_path):
                os.remove(output_path)


class TestAuditLogging:
    """Test audit logging functionality"""

    def test_logging_functionality(self):
        """Test that logging works without errors"""
        auditor = BrainMasterAuditor()

        # Should not raise exceptions
        auditor.log("Test message")
        auditor.log("Warning message", "WARNING")
        auditor.log("Error message", "ERROR")


def test_import_successful():
    """Test that all imports are successful"""
    from backend.tests.brain_master_audit import (
        BrainMasterAuditor,
        PerformanceMetrics,
        StabilityMetrics,
        BreakingPointMetrics,
        AuditReport,
        main
    )

    assert BrainMasterAuditor is not None
    assert callable(main)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s"])
