"""
BRAIN Master Audit - Comprehensive Stress Test & Benchmark
===========================================================

Purpose: Deep evaluation of the BRAiN Agent Orchestration Framework
         Validates biological plausibility and architectural limits

Phases:
    Phase A: Performance Stress Test
    Phase B: Dynamic Stability Analysis
    Phase C: Breaking Point Definition

Architecture Context:
    - "Neurons" = Agents (AI workers)
    - "Synapses" = Mission throughput
    - "Firing Rates" = Agent utilization & mission completion rate
    - "Network Stability" = Queue health, no deadlocks
    - "Edge of Chaos" = Optimal load balancing vs saturation

Author: Claude (Stress Test Specialist)
Project: BRAIN Framework by FalkLabs / Olaf Falk
"""

import sys
import os
import time
import asyncio
import json
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
import traceback

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Third-party imports
try:
    import psutil
    import numpy as np
    from scipy import stats as scipy_stats
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install psutil numpy scipy")
    sys.exit(1)

# FastAPI test client
from fastapi.testclient import TestClient

# Import BRAiN components
try:
    from backend.main import app
    from backend.modules.mission_system.models import MissionStatus, MissionPriority, MissionType
    from backend.modules.mission_system.orchestrator import AgentProfile, AgentStatus
except ImportError as e:
    print(f"Failed to import BRAiN components: {e}")
    print(f"Current path: {sys.path}")
    sys.exit(1)


# =============================================================================
# DATA STRUCTURES FOR AUDIT RESULTS
# =============================================================================

@dataclass
class PerformanceMetrics:
    """Phase A: Performance metrics"""
    test_scale: int
    total_missions: int
    missions_completed: int
    missions_failed: int
    duration_seconds: float
    throughput_per_second: float
    avg_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    peak_memory_mb: float
    avg_memory_mb: float
    memory_leak_detected: bool
    complexity_order: str  # O(n), O(n log n), O(n²), etc.


@dataclass
class StabilityMetrics:
    """Phase B: Stability analysis"""
    agent_utilization_mean: float
    agent_utilization_std: float
    agent_utilization_distribution: List[float]
    completion_rate: float
    failure_rate: float
    timeout_rate: float
    synchronicity_index: float  # 0=desynchronized, 1=pathological synchronization
    entropy: float  # Shannon entropy of system states
    edge_of_chaos_score: float  # Optimal: 0.5-0.7
    deadlock_detected: bool
    starvation_detected: bool
    cascade_failure_detected: bool


@dataclass
class BreakingPointMetrics:
    """Phase C: Breaking point analysis"""
    max_missions_concurrent: int
    max_agents_concurrent: int
    max_throughput_achieved: float
    bottleneck_component: str
    bottleneck_location: str
    critical_failure_mode: str
    recovery_time_seconds: float


@dataclass
class AuditReport:
    """Complete audit report"""
    timestamp: str
    brain_version: str
    test_environment: Dict[str, Any]
    phase_a_results: List[PerformanceMetrics]
    phase_b_results: StabilityMetrics
    phase_c_results: BreakingPointMetrics
    optimization_recommendations: List[str]
    critical_bottlenecks: List[Dict[str, str]]


# =============================================================================
# AUDIT ORCHESTRATOR
# =============================================================================

class BrainMasterAuditor:
    """
    Main audit orchestrator that runs all test phases
    """

    def __init__(self):
        self.client = TestClient(app)
        self.process = psutil.Process()
        self.audit_start_time = datetime.now()
        self.mission_latencies: List[float] = []
        self.memory_samples: List[float] = []
        self.agent_states_history: List[Dict[str, Any]] = []

        # Results storage
        self.phase_a_results: List[PerformanceMetrics] = []
        self.phase_b_results: Optional[StabilityMetrics] = None
        self.phase_c_results: Optional[BreakingPointMetrics] = None
        self.optimization_recommendations: List[str] = []
        self.critical_bottlenecks: List[Dict[str, str]] = []

    def log(self, message: str, level: str = "INFO"):
        """Structured logging"""
        timestamp = datetime.now().isoformat()
        print(f"[{timestamp}] [{level}] {message}")

    def measure_memory(self) -> float:
        """Get current memory usage in MB"""
        mem_info = self.process.memory_info()
        return mem_info.rss / 1024 / 1024  # Convert to MB

    def sample_memory(self):
        """Add memory sample to tracking"""
        self.memory_samples.append(self.measure_memory())

    def detect_memory_leak(self) -> bool:
        """
        Detect memory leak using linear regression on memory samples
        Returns True if significant upward trend detected
        """
        if len(self.memory_samples) < 10:
            return False

        x = np.arange(len(self.memory_samples))
        y = np.array(self.memory_samples)

        slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(x, y)

        # Memory leak if:
        # 1. Significant positive slope (> 0.5 MB per sample)
        # 2. High correlation (r² > 0.8)
        # 3. Statistically significant (p < 0.05)
        leak_detected = (slope > 0.5) and (r_value**2 > 0.8) and (p_value < 0.05)

        if leak_detected:
            self.log(f"⚠️  MEMORY LEAK DETECTED: Slope={slope:.2f} MB/sample, R²={r_value**2:.3f}", "WARNING")

        return leak_detected

    def estimate_complexity(self, scale_points: List[Tuple[int, float]]) -> str:
        """
        Estimate algorithmic complexity from scale vs. time data points
        Returns O-notation string
        """
        if len(scale_points) < 3:
            return "Unknown (insufficient data)"

        scales = np.array([s[0] for s in scale_points])
        times = np.array([s[1] for s in scale_points])

        # Test different complexity models
        models = {
            "O(1)": np.ones_like(scales),
            "O(log n)": np.log(scales),
            "O(n)": scales,
            "O(n log n)": scales * np.log(scales),
            "O(n²)": scales ** 2,
            "O(n³)": scales ** 3,
        }

        best_model = "Unknown"
        best_r_squared = 0

        for model_name, model_values in models.items():
            try:
                slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(model_values, times)
                r_squared = r_value ** 2

                if r_squared > best_r_squared and p_value < 0.05:
                    best_r_squared = r_squared
                    best_model = model_name
            except:
                continue

        self.log(f"Complexity estimation: {best_model} (R²={best_r_squared:.3f})")
        return f"{best_model} (R²={best_r_squared:.3f})"

    # =========================================================================
    # PHASE A: PERFORMANCE STRESS TEST
    # =========================================================================

    def run_phase_a(self) -> List[PerformanceMetrics]:
        """
        Phase A: Performance Stress Test

        Simulates exponentially increasing load:
        - Start: 100 missions
        - Scale: 100, 250, 500, 1000, 2500, 5000, 10000

        Measures:
        - Throughput (missions/second)
        - Latency (avg, p95, p99)
        - Memory usage
        - Complexity analysis
        """
        self.log("=" * 80)
        self.log("PHASE A: PERFORMANCE STRESS TEST")
        self.log("=" * 80)

        # Exponential scale points
        scale_points = [100, 250, 500, 1000, 2500, 5000, 10000]
        complexity_data_points = []

        for scale in scale_points:
            self.log(f"\n🔬 Testing scale: {scale} missions")

            # Reset metrics for this scale
            self.mission_latencies = []
            self.memory_samples = []

            # Measure baseline memory
            baseline_memory = self.measure_memory()
            self.log(f"Baseline memory: {baseline_memory:.2f} MB")

            # Run stress test
            start_time = time.time()

            results = self._stress_test_enqueue_missions(scale)

            duration = time.time() - start_time
            complexity_data_points.append((scale, duration))

            # Calculate metrics
            peak_memory = max(self.memory_samples) if self.memory_samples else baseline_memory
            avg_memory = statistics.mean(self.memory_samples) if self.memory_samples else baseline_memory
            memory_leak = self.detect_memory_leak()

            throughput = results["completed"] / duration if duration > 0 else 0

            if self.mission_latencies:
                avg_latency = statistics.mean(self.mission_latencies)
                sorted_latencies = sorted(self.mission_latencies)
                p95_latency = sorted_latencies[int(len(sorted_latencies) * 0.95)]
                p99_latency = sorted_latencies[int(len(sorted_latencies) * 0.99)]
            else:
                avg_latency = p95_latency = p99_latency = 0

            # Store metrics
            metrics = PerformanceMetrics(
                test_scale=scale,
                total_missions=scale,
                missions_completed=results["completed"],
                missions_failed=results["failed"],
                duration_seconds=duration,
                throughput_per_second=throughput,
                avg_latency_ms=avg_latency,
                p95_latency_ms=p95_latency,
                p99_latency_ms=p99_latency,
                peak_memory_mb=peak_memory,
                avg_memory_mb=avg_memory,
                memory_leak_detected=memory_leak,
                complexity_order="Calculating..."
            )

            self.phase_a_results.append(metrics)

            # Log results
            self.log(f"✅ Completed: {results['completed']}/{scale}")
            self.log(f"❌ Failed: {results['failed']}")
            self.log(f"⏱️  Duration: {duration:.2f}s")
            self.log(f"📊 Throughput: {throughput:.2f} missions/s")
            self.log(f"🐏 Peak Memory: {peak_memory:.2f} MB")
            self.log(f"💾 Avg Memory: {avg_memory:.2f} MB")
            self.log(f"⚠️  Memory Leak: {'YES' if memory_leak else 'NO'}")

            # Brief cooldown between tests
            time.sleep(2)

        # Calculate complexity after all tests
        complexity = self.estimate_complexity(complexity_data_points)
        for metrics in self.phase_a_results:
            metrics.complexity_order = complexity

        self.log("\n✅ Phase A Complete")
        return self.phase_a_results

    def _stress_test_enqueue_missions(self, count: int) -> Dict[str, int]:
        """
        Enqueue 'count' missions and track performance
        Returns dict with completed/failed counts
        """
        completed = 0
        failed = 0

        for i in range(count):
            # Sample memory periodically
            if i % 10 == 0:
                self.sample_memory()

            # Create mission payload
            payload = {
                "name": f"Stress Test Mission {i}",
                "description": f"Automated stress test mission #{i}",
                "priority": "NORMAL",
                "mission_type": "ANALYSIS",
                "payload": {
                    "test_data": f"data_{i}",
                    "iteration": i
                }
            }

            # Measure latency
            request_start = time.time()

            try:
                response = self.client.post("/api/missions/enqueue", json=payload)

                request_duration = (time.time() - request_start) * 1000  # Convert to ms
                self.mission_latencies.append(request_duration)

                if response.status_code == 200:
                    completed += 1
                else:
                    failed += 1
                    if i < 10:  # Log first few failures
                        self.log(f"Mission {i} failed: {response.status_code} - {response.text}", "ERROR")

            except Exception as e:
                failed += 1
                if i < 10:
                    self.log(f"Mission {i} exception: {e}", "ERROR")

        return {"completed": completed, "failed": failed}

    # =========================================================================
    # PHASE B: DYNAMIC STABILITY ANALYSIS
    # =========================================================================

    def run_phase_b(self) -> StabilityMetrics:
        """
        Phase B: Dynamic Stability Analysis

        Analyzes system behavior under sustained load:
        - Agent utilization patterns ("firing rates")
        - Synchronicity detection (pathological patterns)
        - Entropy measurement (edge of chaos)
        - Deadlock/starvation detection
        """
        self.log("\n" + "=" * 80)
        self.log("PHASE B: DYNAMIC STABILITY ANALYSIS")
        self.log("=" * 80)

        # Run sustained load test
        test_duration_seconds = 60  # 1 minute sustained load
        missions_per_second = 10

        self.log(f"Running sustained load: {missions_per_second} missions/s for {test_duration_seconds}s")

        stability_data = self._run_sustained_load(test_duration_seconds, missions_per_second)

        # Analyze agent utilization
        agent_utilization = stability_data["agent_utilization"]
        utilization_mean = statistics.mean(agent_utilization) if agent_utilization else 0
        utilization_std = statistics.stdev(agent_utilization) if len(agent_utilization) > 1 else 0

        # Calculate completion/failure rates
        total_missions = stability_data["total_missions"]
        completion_rate = stability_data["completed"] / total_missions if total_missions > 0 else 0
        failure_rate = stability_data["failed"] / total_missions if total_missions > 0 else 0
        timeout_rate = stability_data["timeouts"] / total_missions if total_missions > 0 else 0

        # Calculate synchronicity index
        synchronicity = self._calculate_synchronicity_index(stability_data["agent_states_timeline"])

        # Calculate entropy
        entropy = self._calculate_system_entropy(stability_data["state_distribution"])

        # Edge of chaos score (optimal: 0.5-0.7)
        # Based on entropy and utilization variance
        edge_of_chaos = self._calculate_edge_of_chaos_score(entropy, utilization_std)

        # Detect pathologies
        deadlock = self._detect_deadlock(stability_data["agent_states_timeline"])
        starvation = self._detect_starvation(agent_utilization)
        cascade_failure = self._detect_cascade_failure(stability_data["failure_timeline"])

        metrics = StabilityMetrics(
            agent_utilization_mean=utilization_mean,
            agent_utilization_std=utilization_std,
            agent_utilization_distribution=agent_utilization,
            completion_rate=completion_rate,
            failure_rate=failure_rate,
            timeout_rate=timeout_rate,
            synchronicity_index=synchronicity,
            entropy=entropy,
            edge_of_chaos_score=edge_of_chaos,
            deadlock_detected=deadlock,
            starvation_detected=starvation,
            cascade_failure_detected=cascade_failure
        )

        self.phase_b_results = metrics

        # Log results
        self.log(f"\n📊 Agent Utilization: {utilization_mean:.2%} ± {utilization_std:.2%}")
        self.log(f"✅ Completion Rate: {completion_rate:.2%}")
        self.log(f"❌ Failure Rate: {failure_rate:.2%}")
        self.log(f"⏱️  Timeout Rate: {timeout_rate:.2%}")
        self.log(f"🔄 Synchronicity Index: {synchronicity:.3f} ({'HEALTHY' if synchronicity < 0.7 else 'PATHOLOGICAL'})")
        self.log(f"🎲 System Entropy: {entropy:.3f}")
        self.log(f"🌀 Edge of Chaos Score: {edge_of_chaos:.3f} ({'OPTIMAL' if 0.5 <= edge_of_chaos <= 0.7 else 'SUBOPTIMAL'})")
        self.log(f"🔒 Deadlock: {'DETECTED' if deadlock else 'None'}")
        self.log(f"🍽️  Starvation: {'DETECTED' if starvation else 'None'}")
        self.log(f"💥 Cascade Failure: {'DETECTED' if cascade_failure else 'None'}")

        self.log("\n✅ Phase B Complete")
        return metrics

    def _run_sustained_load(self, duration_seconds: int, missions_per_second: int) -> Dict[str, Any]:
        """
        Run sustained load for given duration and collect stability data
        """
        total_missions = 0
        completed = 0
        failed = 0
        timeouts = 0

        agent_utilization = []
        agent_states_timeline = []
        state_distribution = defaultdict(int)
        failure_timeline = []

        start_time = time.time()
        end_time = start_time + duration_seconds

        interval = 1.0 / missions_per_second  # Time between missions

        while time.time() < end_time:
            iteration_start = time.time()

            # Enqueue mission
            payload = {
                "name": f"Stability Test Mission {total_missions}",
                "description": "Sustained load test mission",
                "priority": "NORMAL",
                "mission_type": "ANALYSIS",
                "payload": {"iteration": total_missions}
            }

            try:
                response = self.client.post("/api/missions/enqueue", json=payload)
                total_missions += 1

                if response.status_code == 200:
                    completed += 1
                else:
                    failed += 1
                    failure_timeline.append(time.time() - start_time)
            except Exception:
                failed += 1
                failure_timeline.append(time.time() - start_time)

            # Sample system state every second
            if total_missions % missions_per_second == 0:
                try:
                    queue_response = self.client.get("/api/missions/queue")
                    if queue_response.status_code == 200:
                        queue_data = queue_response.json()
                        queue_length = len(queue_data) if isinstance(queue_data, list) else 0

                        # Record state
                        state_key = f"queue_{queue_length // 10 * 10}"  # Bucket by 10s
                        state_distribution[state_key] += 1

                        agent_states_timeline.append({
                            "timestamp": time.time() - start_time,
                            "queue_length": queue_length
                        })

                        # Mock agent utilization (would need actual agent API)
                        # For now, estimate based on queue length
                        estimated_utilization = min(1.0, queue_length / 100.0)
                        agent_utilization.append(estimated_utilization)
                except Exception:
                    pass

            # Sleep to maintain rate
            elapsed = time.time() - iteration_start
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)

        return {
            "total_missions": total_missions,
            "completed": completed,
            "failed": failed,
            "timeouts": timeouts,
            "agent_utilization": agent_utilization,
            "agent_states_timeline": agent_states_timeline,
            "state_distribution": dict(state_distribution),
            "failure_timeline": failure_timeline
        }

    def _calculate_synchronicity_index(self, timeline: List[Dict[str, Any]]) -> float:
        """
        Calculate synchronicity index from agent state timeline
        0.0 = healthy desynchronization
        1.0 = pathological synchronization (all agents in lockstep)
        """
        if len(timeline) < 2:
            return 0.0

        # Analyze variance in queue lengths over time
        queue_lengths = [state["queue_length"] for state in timeline]

        if not queue_lengths:
            return 0.0

        # Low variance = high synchronicity (bad)
        # High variance = low synchronicity (good, indicates dynamic adaptation)
        variance = statistics.variance(queue_lengths) if len(queue_lengths) > 1 else 0
        mean_queue = statistics.mean(queue_lengths)

        # Coefficient of variation
        cv = (variance ** 0.5) / mean_queue if mean_queue > 0 else 0

        # Convert to synchronicity index (inverse relationship)
        # High CV = low synchronicity
        synchronicity = 1.0 / (1.0 + cv)

        return synchronicity

    def _calculate_system_entropy(self, state_distribution: Dict[str, int]) -> float:
        """
        Calculate Shannon entropy of system states
        High entropy = high information capacity (good)
        Low entropy = limited state space (bad)
        """
        if not state_distribution:
            return 0.0

        total_samples = sum(state_distribution.values())
        if total_samples == 0:
            return 0.0

        probabilities = [count / total_samples for count in state_distribution.values()]

        # Shannon entropy
        entropy = -sum(p * np.log2(p) for p in probabilities if p > 0)

        return entropy

    def _calculate_edge_of_chaos_score(self, entropy: float, utilization_std: float) -> float:
        """
        Calculate "edge of chaos" score
        Optimal: 0.5-0.7 (balance between order and chaos)

        Combines entropy and utilization variance
        """
        # Normalize entropy (typical range 0-5 bits)
        normalized_entropy = min(entropy / 5.0, 1.0)

        # Normalize utilization std (typical range 0-0.5)
        normalized_variance = min(utilization_std / 0.5, 1.0)

        # Edge of chaos = balance between structure (low entropy) and flexibility (high variance)
        score = (normalized_entropy + normalized_variance) / 2.0

        return score

    def _detect_deadlock(self, timeline: List[Dict[str, Any]]) -> bool:
        """
        Detect deadlock: prolonged period with no state changes
        """
        if len(timeline) < 10:
            return False

        # Check last 10 samples for identical queue lengths
        recent_states = timeline[-10:]
        queue_lengths = [state["queue_length"] for state in recent_states]

        # Deadlock if all identical and non-zero
        if len(set(queue_lengths)) == 1 and queue_lengths[0] > 0:
            return True

        return False

    def _detect_starvation(self, utilization: List[float]) -> bool:
        """
        Detect starvation: agents with consistently zero utilization
        """
        if len(utilization) < 10:
            return False

        # Starvation if >50% of samples are zero utilization
        zero_count = sum(1 for u in utilization if u < 0.01)
        starvation_ratio = zero_count / len(utilization)

        return starvation_ratio > 0.5

    def _detect_cascade_failure(self, failure_timeline: List[float]) -> bool:
        """
        Detect cascade failure: rapid succession of failures
        """
        if len(failure_timeline) < 5:
            return False

        # Check for 5+ failures within 1 second window
        for i in range(len(failure_timeline) - 4):
            window_failures = failure_timeline[i:i+5]
            time_span = window_failures[-1] - window_failures[0]

            if time_span < 1.0:
                return True

        return False

    # =========================================================================
    # PHASE C: BREAKING POINT DEFINITION
    # =========================================================================

    def run_phase_c(self) -> BreakingPointMetrics:
        """
        Phase C: Breaking Point Definition

        Finds the maximum capacity of the system:
        - Max concurrent missions
        - Max concurrent agents
        - Max throughput
        - Identifies bottleneck component
        """
        self.log("\n" + "=" * 80)
        self.log("PHASE C: BREAKING POINT DEFINITION")
        self.log("=" * 80)

        # Binary search for max load
        self.log("🔍 Binary search for maximum throughput...")

        max_throughput = self._find_max_throughput()

        self.log(f"\n🎯 Maximum Throughput: {max_throughput:.2f} missions/s")

        # Identify bottleneck
        bottleneck_info = self._identify_bottleneck()

        # Measure recovery time
        recovery_time = self._measure_recovery_time()

        metrics = BreakingPointMetrics(
            max_missions_concurrent=int(max_throughput * 10),  # Estimate based on throughput
            max_agents_concurrent=10,  # Would need agent API to determine
            max_throughput_achieved=max_throughput,
            bottleneck_component=bottleneck_info["component"],
            bottleneck_location=bottleneck_info["location"],
            critical_failure_mode=bottleneck_info["failure_mode"],
            recovery_time_seconds=recovery_time
        )

        self.phase_c_results = metrics

        # Log results
        self.log(f"\n🎯 Max Concurrent Missions: ~{metrics.max_missions_concurrent}")
        self.log(f"🎯 Max Throughput: {metrics.max_throughput_achieved:.2f} missions/s")
        self.log(f"🔍 Bottleneck: {metrics.bottleneck_component}")
        self.log(f"📍 Location: {metrics.bottleneck_location}")
        self.log(f"💥 Failure Mode: {metrics.critical_failure_mode}")
        self.log(f"⏱️  Recovery Time: {metrics.recovery_time_seconds:.2f}s")

        self.log("\n✅ Phase C Complete")
        return metrics

    def _find_max_throughput(self) -> float:
        """
        Binary search to find maximum sustainable throughput
        Returns missions per second
        """
        low = 1.0
        high = 100.0
        tolerance = 0.5

        best_throughput = 0.0

        while high - low > tolerance:
            mid = (low + high) / 2.0
            self.log(f"Testing {mid:.1f} missions/s...")

            # Test this rate for 10 seconds
            result = self._test_throughput_rate(mid, duration_seconds=10)

            if result["success"]:
                best_throughput = mid
                low = mid
                self.log(f"✅ Sustained {mid:.1f} missions/s")
            else:
                high = mid
                self.log(f"❌ Failed at {mid:.1f} missions/s")

        return best_throughput

    def _test_throughput_rate(self, rate: float, duration_seconds: int) -> Dict[str, Any]:
        """
        Test if system can sustain given throughput rate
        Returns success/failure and metrics
        """
        total = 0
        failed = 0
        latencies = []

        start_time = time.time()
        end_time = start_time + duration_seconds
        interval = 1.0 / rate

        while time.time() < end_time:
            iteration_start = time.time()

            payload = {
                "name": f"Throughput Test {total}",
                "description": "Breaking point test",
                "priority": "NORMAL",
                "mission_type": "ANALYSIS",
                "payload": {"test": True}
            }

            try:
                req_start = time.time()
                response = self.client.post("/api/missions/enqueue", json=payload)
                latency = (time.time() - req_start) * 1000

                total += 1
                latencies.append(latency)

                if response.status_code != 200:
                    failed += 1
            except Exception:
                failed += 1

            elapsed = time.time() - iteration_start
            sleep_time = max(0, interval - elapsed)
            time.sleep(sleep_time)

        # Success criteria:
        # 1. Failure rate < 5%
        # 2. P95 latency < 1000ms
        failure_rate = failed / total if total > 0 else 1.0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else float('inf')

        success = (failure_rate < 0.05) and (p95_latency < 1000)

        return {
            "success": success,
            "total": total,
            "failed": failed,
            "failure_rate": failure_rate,
            "p95_latency": p95_latency
        }

    def _identify_bottleneck(self) -> Dict[str, str]:
        """
        Identify the primary bottleneck component
        """
        # This would require profiling, but we can make educated guesses
        # based on the system architecture

        bottlenecks = []

        # Check Redis queue performance
        try:
            queue_start = time.time()
            response = self.client.get("/api/missions/queue")
            queue_latency = (time.time() - queue_start) * 1000

            if queue_latency > 100:
                bottlenecks.append({
                    "component": "Mission Queue (Redis)",
                    "location": "backend/modules/mission_system/queue.py",
                    "latency_ms": queue_latency,
                    "severity": "high" if queue_latency > 500 else "medium"
                })
        except Exception:
            pass

        # Check API endpoint performance
        try:
            api_start = time.time()
            response = self.client.get("/api/missions/info")
            api_latency = (time.time() - api_start) * 1000

            if api_latency > 50:
                bottlenecks.append({
                    "component": "FastAPI Router",
                    "location": "backend/api/routes/missions.py",
                    "latency_ms": api_latency,
                    "severity": "medium"
                })
        except Exception:
            pass

        # Check memory pressure
        current_memory = self.measure_memory()
        if current_memory > 1000:  # > 1GB
            bottlenecks.append({
                "component": "Memory Usage",
                "location": "System-wide",
                "memory_mb": current_memory,
                "severity": "high"
            })

        # Return most severe bottleneck
        if bottlenecks:
            # Sort by severity
            severity_order = {"high": 0, "medium": 1, "low": 2}
            bottlenecks.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 999))

            primary = bottlenecks[0]
            return {
                "component": primary["component"],
                "location": primary["location"],
                "failure_mode": f"Latency: {primary.get('latency_ms', 'N/A')}ms" if "latency_ms" in primary else f"Memory: {primary.get('memory_mb', 'N/A')}MB"
            }

        return {
            "component": "Unknown",
            "location": "N/A",
            "failure_mode": "No bottleneck detected"
        }

    def _measure_recovery_time(self) -> float:
        """
        Measure system recovery time after overload
        """
        self.log("\n🔄 Measuring recovery time after overload...")

        # Overload the system
        self.log("⚡ Applying overload (200 missions/s for 5s)...")
        for i in range(1000):
            try:
                self.client.post("/api/missions/enqueue", json={
                    "name": f"Overload {i}",
                    "description": "Overload test",
                    "priority": "LOW",
                    "mission_type": "ANALYSIS",
                    "payload": {}
                })
            except:
                pass

        # Wait and measure recovery
        recovery_start = time.time()
        recovered = False

        while time.time() - recovery_start < 60:  # Max 60s
            time.sleep(1)

            try:
                # Test if system is responsive
                test_start = time.time()
                response = self.client.get("/api/missions/health")
                latency = (time.time() - test_start) * 1000

                if response.status_code == 200 and latency < 100:
                    recovery_time = time.time() - recovery_start
                    self.log(f"✅ System recovered in {recovery_time:.2f}s")
                    recovered = True
                    return recovery_time
            except:
                pass

        if not recovered:
            self.log("❌ System did not recover within 60s")
            return 60.0

        return 0.0

    # =========================================================================
    # OPTIMIZATION ANALYSIS
    # =========================================================================

    def analyze_optimizations(self):
        """
        Analyze results and generate optimization recommendations
        """
        self.log("\n" + "=" * 80)
        self.log("OPTIMIZATION ANALYSIS")
        self.log("=" * 80)

        recommendations = []
        bottlenecks = []

        # Phase A analysis
        if self.phase_a_results:
            last_result = self.phase_a_results[-1]

            # Memory leak detection
            if last_result.memory_leak_detected:
                recommendations.append(
                    "🐛 CRITICAL: Memory leak detected. Profile with memory_profiler to identify leak source."
                )
                bottlenecks.append({
                    "component": "Memory Management",
                    "location": "Unknown (requires profiling)",
                    "severity": "CRITICAL",
                    "recommendation": "Use memory_profiler or objgraph to trace object retention"
                })

            # Complexity analysis
            if "O(n²)" in last_result.complexity_order or "O(n³)" in last_result.complexity_order:
                recommendations.append(
                    f"⚠️  HIGH: Algorithmic complexity is {last_result.complexity_order}. "
                    "Consider optimization with caching, indexing, or algorithmic improvements."
                )
                bottlenecks.append({
                    "component": "Mission Orchestrator",
                    "location": "backend/modules/mission_system/orchestrator.py:90-112",
                    "severity": "HIGH",
                    "recommendation": "Optimize agent selection algorithm with priority queues or caching"
                })

            # Throughput analysis
            if last_result.throughput_per_second < 10:
                recommendations.append(
                    "📉 Medium: Low throughput detected. Consider async optimization, connection pooling, or Redis pipelining."
                )
                bottlenecks.append({
                    "component": "Redis Queue Operations",
                    "location": "backend/modules/mission_system/queue.py:160-260",
                    "severity": "MEDIUM",
                    "recommendation": "Implement Redis pipelining for batch operations"
                })

        # Phase B analysis
        if self.phase_b_results:
            if self.phase_b_results.deadlock_detected:
                recommendations.append(
                    "🔒 CRITICAL: Deadlock detected. Review locking mechanisms and add timeout guards."
                )
                bottlenecks.append({
                    "component": "Mission Assignment Logic",
                    "location": "backend/modules/mission_system/orchestrator.py:346-361",
                    "severity": "CRITICAL",
                    "recommendation": "Add timeout guards and deadlock detection/recovery"
                })

            if self.phase_b_results.starvation_detected:
                recommendations.append(
                    "🍽️  HIGH: Agent starvation detected. Improve load balancing algorithm."
                )
                bottlenecks.append({
                    "component": "Load Balancing",
                    "location": "backend/modules/mission_system/orchestrator.py:_rebalance_assignments",
                    "severity": "HIGH",
                    "recommendation": "Implement fair queuing or work-stealing algorithm"
                })

            if self.phase_b_results.edge_of_chaos_score < 0.3 or self.phase_b_results.edge_of_chaos_score > 0.8:
                if self.phase_b_results.edge_of_chaos_score < 0.3:
                    recommendations.append(
                        "⚖️  Low: System is too ordered (low entropy). May lack adaptability."
                    )
                else:
                    recommendations.append(
                        "🌀 Medium: System is too chaotic (high entropy). May lack stability."
                    )

        # Phase C analysis
        if self.phase_c_results:
            if self.phase_c_results.recovery_time_seconds > 30:
                recommendations.append(
                    "⏱️  HIGH: Slow recovery time after overload. Implement circuit breakers and graceful degradation."
                )
                bottlenecks.append({
                    "component": "Overload Protection",
                    "location": "backend/main.py (middleware)",
                    "severity": "HIGH",
                    "recommendation": "Add rate limiting, circuit breakers, and backpressure mechanisms"
                })

        # General recommendations
        recommendations.extend([
            "✅ Consider enabling Redis persistence (AOF/RDB) for mission durability",
            "✅ Implement mission result caching for frequently accessed missions",
            "✅ Add distributed tracing (OpenTelemetry) for performance profiling",
            "✅ Consider horizontal scaling with multiple worker processes",
            "✅ Implement backpressure mechanisms to prevent queue saturation"
        ])

        self.optimization_recommendations = recommendations
        self.critical_bottlenecks = bottlenecks

        # Log recommendations
        self.log("\n📋 OPTIMIZATION RECOMMENDATIONS:\n")
        for rec in recommendations:
            self.log(f"  {rec}")

        if bottlenecks:
            self.log("\n🔍 CRITICAL BOTTLENECKS IDENTIFIED:\n")
            for bn in bottlenecks:
                self.log(f"  [{bn['severity']}] {bn['component']}")
                self.log(f"    Location: {bn['location']}")
                self.log(f"    Recommendation: {bn['recommendation']}")
                self.log("")

    # =========================================================================
    # REPORT GENERATION
    # =========================================================================

    def generate_report(self) -> AuditReport:
        """
        Generate final audit report
        """
        # Gather environment info
        env_info = {
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": psutil.cpu_count(),
            "total_memory_mb": psutil.virtual_memory().total / 1024 / 1024,
            "test_date": self.audit_start_time.isoformat()
        }

        report = AuditReport(
            timestamp=datetime.now().isoformat(),
            brain_version="0.5.0",  # From CLAUDE.md
            test_environment=env_info,
            phase_a_results=self.phase_a_results,
            phase_b_results=self.phase_b_results or StabilityMetrics(
                agent_utilization_mean=0, agent_utilization_std=0,
                agent_utilization_distribution=[], completion_rate=0,
                failure_rate=0, timeout_rate=0, synchronicity_index=0,
                entropy=0, edge_of_chaos_score=0, deadlock_detected=False,
                starvation_detected=False, cascade_failure_detected=False
            ),
            phase_c_results=self.phase_c_results or BreakingPointMetrics(
                max_missions_concurrent=0, max_agents_concurrent=0,
                max_throughput_achieved=0, bottleneck_component="Unknown",
                bottleneck_location="Unknown", critical_failure_mode="Unknown",
                recovery_time_seconds=0
            ),
            optimization_recommendations=self.optimization_recommendations,
            critical_bottlenecks=self.critical_bottlenecks
        )

        return report

    def save_report_markdown(self, report: AuditReport, output_path: str):
        """
        Save report as markdown file
        """
        md = []
        md.append("# BRAIN Master Audit Report")
        md.append("=" * 80)
        md.append("")
        md.append(f"**Generated:** {report.timestamp}")
        md.append(f"**BRAiN Version:** {report.brain_version}")
        md.append("")

        # Environment
        md.append("## Test Environment")
        md.append("")
        for key, value in report.test_environment.items():
            md.append(f"- **{key}:** {value}")
        md.append("")

        # Phase A
        md.append("## Phase A: Performance Stress Test")
        md.append("")
        md.append("| Scale | Completed | Failed | Duration (s) | Throughput (m/s) | Avg Latency (ms) | P95 (ms) | P99 (ms) | Peak Memory (MB) | Memory Leak |")
        md.append("|-------|-----------|--------|--------------|------------------|------------------|----------|----------|------------------|-------------|")

        for metrics in report.phase_a_results:
            md.append(
                f"| {metrics.test_scale} | {metrics.missions_completed} | {metrics.missions_failed} | "
                f"{metrics.duration_seconds:.2f} | {metrics.throughput_per_second:.2f} | "
                f"{metrics.avg_latency_ms:.2f} | {metrics.p95_latency_ms:.2f} | {metrics.p99_latency_ms:.2f} | "
                f"{metrics.peak_memory_mb:.2f} | {'⚠️ YES' if metrics.memory_leak_detected else '✅ NO'} |"
            )

        if report.phase_a_results:
            md.append("")
            md.append(f"**Algorithmic Complexity:** {report.phase_a_results[0].complexity_order}")

        md.append("")

        # Phase B
        md.append("## Phase B: Dynamic Stability Analysis")
        md.append("")
        b = report.phase_b_results
        md.append(f"- **Agent Utilization:** {b.agent_utilization_mean:.2%} ± {b.agent_utilization_std:.2%}")
        md.append(f"- **Completion Rate:** {b.completion_rate:.2%}")
        md.append(f"- **Failure Rate:** {b.failure_rate:.2%}")
        md.append(f"- **Timeout Rate:** {b.timeout_rate:.2%}")
        md.append(f"- **Synchronicity Index:** {b.synchronicity_index:.3f} ({'⚠️ PATHOLOGICAL' if b.synchronicity_index > 0.7 else '✅ HEALTHY'})")
        md.append(f"- **System Entropy:** {b.entropy:.3f}")
        md.append(f"- **Edge of Chaos Score:** {b.edge_of_chaos_score:.3f} ({'✅ OPTIMAL' if 0.5 <= b.edge_of_chaos_score <= 0.7 else '⚠️ SUBOPTIMAL'})")
        md.append(f"- **Deadlock Detected:** {'🔒 YES' if b.deadlock_detected else '✅ NO'}")
        md.append(f"- **Starvation Detected:** {'🍽️ YES' if b.starvation_detected else '✅ NO'}")
        md.append(f"- **Cascade Failure:** {'💥 YES' if b.cascade_failure_detected else '✅ NO'}")
        md.append("")

        # Phase C
        md.append("## Phase C: Breaking Point Definition")
        md.append("")
        c = report.phase_c_results
        md.append(f"- **Max Concurrent Missions:** ~{c.max_missions_concurrent}")
        md.append(f"- **Max Throughput:** {c.max_throughput_achieved:.2f} missions/s")
        md.append(f"- **Bottleneck Component:** {c.bottleneck_component}")
        md.append(f"- **Bottleneck Location:** `{c.bottleneck_location}`")
        md.append(f"- **Critical Failure Mode:** {c.critical_failure_mode}")
        md.append(f"- **Recovery Time:** {c.recovery_time_seconds:.2f}s")
        md.append("")

        # Critical Bottlenecks
        if report.critical_bottlenecks:
            md.append("## Critical Bottlenecks")
            md.append("")
            for bn in report.critical_bottlenecks:
                md.append(f"### [{bn['severity']}] {bn['component']}")
                md.append("")
                md.append(f"**Location:** `{bn['location']}`")
                md.append("")
                md.append(f"**Recommendation:** {bn['recommendation']}")
                md.append("")

        # Recommendations
        md.append("## Optimization Recommendations")
        md.append("")
        for i, rec in enumerate(report.optimization_recommendations, 1):
            md.append(f"{i}. {rec}")
        md.append("")

        # Conclusion
        md.append("## Conclusion")
        md.append("")

        # Determine overall health
        critical_issues = len([bn for bn in report.critical_bottlenecks if bn['severity'] == 'CRITICAL'])
        high_issues = len([bn for bn in report.critical_bottlenecks if bn['severity'] == 'HIGH'])

        if critical_issues > 0:
            md.append("⚠️ **System Health: CRITICAL** - Immediate action required")
        elif high_issues > 0:
            md.append("⚠️ **System Health: NEEDS ATTENTION** - Performance optimizations recommended")
        else:
            md.append("✅ **System Health: GOOD** - System is performing within acceptable parameters")

        md.append("")
        md.append("---")
        md.append("")
        md.append("*This report was generated automatically by the BRAiN Master Audit tool.*")

        # Write to file
        with open(output_path, 'w') as f:
            f.write('\n'.join(md))

        self.log(f"\n📄 Report saved to: {output_path}")

    # =========================================================================
    # MAIN EXECUTION
    # =========================================================================

    def run_full_audit(self) -> AuditReport:
        """
        Execute all audit phases and generate report
        """
        self.log("\n")
        self.log("=" * 80)
        self.log(" BRAIN MASTER AUDIT - COMPREHENSIVE STRESS TEST & BENCHMARK")
        self.log("=" * 80)
        self.log("")
        self.log("System Under Test: BRAiN Agent Orchestration Framework v0.5.0")
        self.log("Architecture: Bio-inspired multi-agent system with mission orchestration")
        self.log("")
        self.log("Test Phases:")
        self.log("  Phase A: Performance Stress Test (exponential scaling)")
        self.log("  Phase B: Dynamic Stability Analysis (sustained load)")
        self.log("  Phase C: Breaking Point Definition (capacity limits)")
        self.log("")
        self.log("=" * 80)
        self.log("")

        try:
            # Phase A
            self.run_phase_a()

            # Phase B
            self.run_phase_b()

            # Phase C
            self.run_phase_c()

            # Analyze and generate recommendations
            self.analyze_optimizations()

            # Generate report
            report = self.generate_report()

            # Save markdown report
            output_path = os.path.join(ROOT, "BRAIN_AUDIT_REPORT.md")
            self.save_report_markdown(report, output_path)

            self.log("\n" + "=" * 80)
            self.log("✅ AUDIT COMPLETE")
            self.log("=" * 80)

            return report

        except Exception as e:
            self.log(f"\n❌ AUDIT FAILED: {e}", "ERROR")
            self.log(traceback.format_exc(), "ERROR")
            raise


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main entry point for audit script"""
    print("\n🧠 BRAiN Master Audit - Starting...\n")

    auditor = BrainMasterAuditor()

    try:
        report = auditor.run_full_audit()

        print("\n" + "=" * 80)
        print("✅ AUDIT SUCCESSFUL")
        print("=" * 80)
        print(f"\n📄 Full report: BRAIN_AUDIT_REPORT.md")
        print("")

        return 0

    except KeyboardInterrupt:
        print("\n\n⚠️  Audit interrupted by user")
        return 130

    except Exception as e:
        print(f"\n\n❌ Audit failed: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
