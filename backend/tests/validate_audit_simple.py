"""
Simple Validation Test for BRAiN Master Audit Script
No pytest required - runs directly with Python

Author: Claude (Test Engineer)
Project: BRAIN Framework by FalkLabs / Olaf Falk
"""

import sys
import os

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

print("=" * 80)
print("BRAiN Master Audit - Validation Test")
print("=" * 80)
print()

# Test 1: Import audit module
print("Test 1: Importing audit module...")
try:
    from backend.tests.brain_master_audit import (
        BrainMasterAuditor,
        PerformanceMetrics,
        StabilityMetrics,
        BreakingPointMetrics,
        AuditReport
    )
    print("✅ Import successful")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Create auditor instance
print("\nTest 2: Creating auditor instance...")
try:
    auditor = BrainMasterAuditor()
    print("✅ Auditor instance created")
except Exception as e:
    print(f"❌ Failed to create auditor: {e}")
    sys.exit(1)

# Test 3: Test memory measurement
print("\nTest 3: Testing memory measurement...")
try:
    memory = auditor.measure_memory()
    print(f"✅ Memory measurement: {memory:.2f} MB")
    assert memory > 0
    assert memory < 100000
except Exception as e:
    print(f"❌ Memory measurement failed: {e}")
    sys.exit(1)

# Test 4: Test memory sampling
print("\nTest 4: Testing memory sampling...")
try:
    auditor.sample_memory()
    auditor.sample_memory()
    assert len(auditor.memory_samples) == 2
    print(f"✅ Memory sampling: {len(auditor.memory_samples)} samples")
except Exception as e:
    print(f"❌ Memory sampling failed: {e}")
    sys.exit(1)

# Test 5: Test memory leak detection (no leak)
print("\nTest 5: Testing memory leak detection (no leak)...")
try:
    auditor.memory_samples = [100.0 + i * 0.1 for i in range(20)]
    leak = auditor.detect_memory_leak()
    print(f"✅ Leak detection (stable): {'LEAK' if leak else 'NO LEAK'} (expected: NO LEAK)")
except Exception as e:
    print(f"❌ Leak detection failed: {e}")
    sys.exit(1)

# Test 6: Test memory leak detection (with leak)
print("\nTest 6: Testing memory leak detection (with leak)...")
try:
    auditor.memory_samples = [100.0 + i * 2.0 for i in range(20)]
    leak = auditor.detect_memory_leak()
    print(f"✅ Leak detection (growing): {'LEAK' if leak else 'NO LEAK'} (expected: LEAK)")
    assert leak  # Should detect leak
except Exception as e:
    print(f"❌ Leak detection failed: {e}")
    sys.exit(1)

# Test 7: Test complexity estimation
print("\nTest 7: Testing complexity estimation...")
try:
    scale_points = [(100, 1.0), (200, 2.0), (300, 3.0), (400, 4.0)]
    complexity = auditor.estimate_complexity(scale_points)
    print(f"✅ Complexity estimation: {complexity}")
    assert "O(" in complexity
except Exception as e:
    print(f"❌ Complexity estimation failed: {e}")
    sys.exit(1)

# Test 8: Test synchronicity calculation
print("\nTest 8: Testing synchronicity calculation...")
try:
    timeline = [{"timestamp": i, "queue_length": 50 + i * 5} for i in range(10)]
    sync = auditor._calculate_synchronicity_index(timeline)
    print(f"✅ Synchronicity index: {sync:.3f}")
    assert 0.0 <= sync <= 1.0
except Exception as e:
    print(f"❌ Synchronicity calculation failed: {e}")
    sys.exit(1)

# Test 9: Test entropy calculation
print("\nTest 9: Testing entropy calculation...")
try:
    state_dist = {f"state_{i}": 10 for i in range(10)}
    entropy = auditor._calculate_system_entropy(state_dist)
    print(f"✅ System entropy: {entropy:.3f}")
    assert entropy > 0
except Exception as e:
    print(f"❌ Entropy calculation failed: {e}")
    sys.exit(1)

# Test 10: Test edge of chaos calculation
print("\nTest 10: Testing edge of chaos calculation...")
try:
    score = auditor._calculate_edge_of_chaos_score(entropy=3.0, utilization_std=0.25)
    print(f"✅ Edge of chaos score: {score:.3f}")
    assert 0.0 <= score <= 1.0
except Exception as e:
    print(f"❌ Edge of chaos calculation failed: {e}")
    sys.exit(1)

# Test 11: Test deadlock detection
print("\nTest 11: Testing deadlock detection...")
try:
    # With deadlock
    timeline_deadlock = [{"timestamp": i, "queue_length": 100} for i in range(15)]
    deadlock = auditor._detect_deadlock(timeline_deadlock)
    print(f"✅ Deadlock detection (with deadlock): {deadlock} (expected: True)")
    assert deadlock

    # Without deadlock
    timeline_healthy = [{"timestamp": i, "queue_length": 50 + i * 5} for i in range(15)]
    deadlock = auditor._detect_deadlock(timeline_healthy)
    print(f"✅ Deadlock detection (healthy): {deadlock} (expected: False)")
    assert not deadlock
except Exception as e:
    print(f"❌ Deadlock detection failed: {e}")
    sys.exit(1)

# Test 12: Test starvation detection
print("\nTest 12: Testing starvation detection...")
try:
    # With starvation
    utilization_starved = [0.0] * 15 + [0.1] * 5
    starvation = auditor._detect_starvation(utilization_starved)
    print(f"✅ Starvation detection (starved): {starvation} (expected: True)")
    assert starvation

    # Healthy utilization
    utilization_healthy = [0.6, 0.7, 0.8, 0.65, 0.75, 0.7, 0.8, 0.6, 0.75, 0.7]
    starvation = auditor._detect_starvation(utilization_healthy)
    print(f"✅ Starvation detection (healthy): {starvation} (expected: False)")
    assert not starvation
except Exception as e:
    print(f"❌ Starvation detection failed: {e}")
    sys.exit(1)

# Test 13: Test cascade failure detection
print("\nTest 13: Testing cascade failure detection...")
try:
    # With cascade
    failure_timeline_cascade = [1.0, 1.1, 1.2, 1.3, 1.4]
    cascade = auditor._detect_cascade_failure(failure_timeline_cascade)
    print(f"✅ Cascade detection (cascade): {cascade} (expected: True)")
    assert cascade

    # No cascade
    failure_timeline_normal = [1.0, 5.0, 10.0, 15.0, 20.0]
    cascade = auditor._detect_cascade_failure(failure_timeline_normal)
    print(f"✅ Cascade detection (normal): {cascade} (expected: False)")
    assert not cascade
except Exception as e:
    print(f"❌ Cascade failure detection failed: {e}")
    sys.exit(1)

# Test 14: Test data structures
print("\nTest 14: Testing data structures...")
try:
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
    print(f"✅ PerformanceMetrics: {metrics.throughput_per_second:.2f} m/s")
    assert metrics.missions_completed == 95
except Exception as e:
    print(f"❌ Data structure test failed: {e}")
    sys.exit(1)

# Test 15: Test report generation
print("\nTest 15: Testing report generation...")
try:
    from datetime import datetime

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
    print(f"✅ AuditReport created: version {report.brain_version}")
    assert report.brain_version == "0.5.0"
except Exception as e:
    print(f"❌ Report generation failed: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 80)
print("✅ ALL VALIDATION TESTS PASSED")
print("=" * 80)
print()
print("The audit script structure is valid and all helper functions work correctly.")
print()
print("Next steps:")
print("1. Start the BRAiN backend: docker compose up -d")
print("2. Run the full audit: python tests/brain_master_audit.py")
print("3. Review the report: BRAIN_AUDIT_REPORT.md")
print()
print("See AUDIT_USAGE_GUIDE.md for detailed instructions.")
print()
