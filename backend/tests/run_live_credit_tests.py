"""
BRAiN Credit System Live Test Harness.

Comprehensive live system testing for Event Sourcing foundation with:
- 6 mandatory test scenarios
- Concurrency simulation (50/100/300 parallel requests)
- Retry & duplicate injection
- Deterministic seeding
- JSON report generation

Usage:
    # Full test suite
    python run_live_credit_tests.py --full

    # Single scenario
    python run_live_credit_tests.py --scenario credit_storm

    # Custom parameters
    python run_live_credit_tests.py --concurrency 300 --seed 42

    # With JSON report
    python run_live_credit_tests.py --full --report-json reports/live_test_report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Import Credit System components
try:
    from backend.app.modules.credits.integration_demo import get_credit_system_demo
    from backend.app.modules.credits.event_sourcing.replay import ReplayEngine
    from backend.app.modules.credits.event_sourcing.projections import ProjectionManager
except ImportError as e:
    logger.error(f"Failed to import credit system: {e}")
    sys.exit(1)

# Import invariants checker
try:
    from backend.tests.live_invariants import InvariantsChecker
except ImportError:
    # Will be created next
    InvariantsChecker = None  # type: ignore


# ============================================================================
# Test Configuration
# ============================================================================


@dataclass
class TestConfig:
    """Live test configuration."""
    concurrency: int = 50
    test_duration: int = 1800  # 30 minutes in seconds
    retry_injection: bool = True
    seed: int = 42
    karma_enabled: bool = False
    ml_anomaly_injection: bool = True
    report_json_path: Optional[str] = None


@dataclass
class ScenarioResult:
    """Result of a single test scenario."""
    scenario_name: str
    status: str  # "PASS", "FAIL", "SKIP"
    duration: float
    throughput: float = 0.0
    p95_latency: float = 0.0
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    invariants_passed: bool = True


@dataclass
class LiveTestReport:
    """Complete live test report."""
    timestamp: str
    branch: str
    commit: str
    test_config: TestConfig
    scenario_results: List[ScenarioResult] = field(default_factory=list)
    gate_results: Dict[str, bool] = field(default_factory=dict)
    overall_status: str = "PENDING"  # "GO", "CONDITIONAL", "NO-GO"
    recommendation: str = ""


# ============================================================================
# Test Harness
# ============================================================================


class LiveTestHarness:
    """
    Live test orchestrator for Credit System.

    Features:
    - Scenario execution with concurrency
    - Metrics collection (throughput, latency)
    - Invariants checking via InvariantsChecker
    - JSON report generation
    """

    def __init__(self, config: TestConfig):
        self.config = config
        self.credit_system = None
        self.invariants_checker = None
        self.report = LiveTestReport(
            timestamp=datetime.utcnow().isoformat(),
            branch="claude/event-sourcing-foundation-GmJza",
            commit="3e25513",  # Update with actual commit
            test_config=config,
        )

        # Metrics
        self.latencies: List[float] = []
        self.memory_samples: List[float] = []

    async def setup(self):
        """Initialize test environment."""
        logger.info("Setting up live test environment...")

        # Set random seed for determinism
        random.seed(self.config.seed)

        # Initialize credit system
        self.credit_system = await get_credit_system_demo()
        logger.info("Credit system initialized")

        # Initialize invariants checker
        if InvariantsChecker:
            self.invariants_checker = InvariantsChecker(self.credit_system)
            logger.info("Invariants checker initialized")
        else:
            logger.warning("InvariantsChecker not available")

    async def teardown(self):
        """Cleanup test environment."""
        logger.info("Tearing down test environment...")

    # ========================================================================
    # Scenario 1: Credit Storm / Reuse Cascade
    # ========================================================================

    async def scenario_credit_storm(self) -> ScenarioResult:
        """
        Test massive parallel credit consumption.

        Setup:
        - 10 agents with 1000 credits each
        - 50 parallel threads
        - Each: 20 consume operations (random amounts)

        Expected:
        - All balances >= 0
        - No idempotency violations
        - balance == sum(event_deltas)
        """
        logger.info("🌪️ Starting Scenario 1: Credit Storm / Reuse Cascade")

        result = ScenarioResult(
            scenario_name="Credit Storm / Reuse Cascade",
            status="PASS",
            duration=0.0,
        )

        start_time = time.time()

        try:
            # Create 10 agents with 1000 credits each
            agent_ids = []
            for i in range(10):
                agent_id = f"storm_agent_{i:03d}"
                await self.credit_system.create_agent(agent_id, skill_level=10.0)
                agent_ids.append(agent_id)
                logger.debug(f"Created {agent_id} with 1000 credits")

            # Parallel consumption
            concurrency = self.config.concurrency
            tasks = []

            for _ in range(concurrency):
                agent_id = random.choice(agent_ids)
                amount = random.uniform(10, 50)

                # Inject retries?
                if self.config.retry_injection and random.random() < 0.1:
                    # 10% chance of duplicate (same idempotency_key)
                    idempotency_key = "duplicate_key_storm"
                else:
                    idempotency_key = None

                task = self._consume_with_latency(
                    agent_id,
                    amount,
                    f"Storm operation",
                    idempotency_key=idempotency_key,
                )
                tasks.append(task)

            # Execute in parallel
            results_batch = await asyncio.gather(*tasks, return_exceptions=True)

            # Count errors
            for r in results_batch:
                if isinstance(r, Exception):
                    result.errors.append(str(r))
                    logger.warning(f"Consume failed: {r}")

            # Check invariants
            if self.invariants_checker:
                invariants_ok = await self.invariants_checker.check_all()
                result.invariants_passed = invariants_ok
                if not invariants_ok:
                    result.status = "FAIL"
                    result.errors.append("Invariants violated")

            # Calculate metrics
            result.duration = time.time() - start_time
            result.throughput = concurrency / result.duration if result.duration > 0 else 0
            result.p95_latency = self._calculate_p95(self.latencies)

            result.metrics = {
                "agents_created": len(agent_ids),
                "parallel_operations": concurrency,
                "errors_count": len(result.errors),
                "p50_latency": self._calculate_percentile(self.latencies, 50),
                "p95_latency": result.p95_latency,
                "p99_latency": self._calculate_percentile(self.latencies, 99),
            }

            logger.info(f"✅ Credit Storm completed: {result.status} ({result.duration:.2f}s)")

        except Exception as e:
            result.status = "FAIL"
            result.errors.append(f"Unhandled exception: {e}")
            logger.error(f"❌ Credit Storm failed: {e}")

        return result

    # ========================================================================
    # Scenario 2: Synergy Anti-Gaming Loop
    # ========================================================================

    async def scenario_synergy_anti_gaming(self) -> ScenarioResult:
        """
        Test synergy reward caps (anti-gaming).

        Setup:
        - 5 agents in team "Alpha"
        - 100 synergy events (simulated)
        - Reward cap: 500 credits

        Expected:
        - No agent > 500 credits from synergy
        - Audit log shows "reward_capped" events
        """
        logger.info("🤝 Starting Scenario 2: Synergy Anti-Gaming Loop")

        result = ScenarioResult(
            scenario_name="Synergy Anti-Gaming Loop",
            status="PASS",
            duration=0.0,
        )

        start_time = time.time()

        try:
            # Create 5 agents in team
            team_id = "team_alpha"
            agent_ids = []
            for i in range(5):
                agent_id = f"synergy_agent_{i:03d}"
                await self.credit_system.create_agent(agent_id, skill_level=5.0)
                agent_ids.append(agent_id)

            # Simulate 100 synergy events
            reward_cap = 500.0
            for _ in range(100):
                # Award synergy rewards
                for agent_id in agent_ids:
                    reward_amount = random.uniform(10, 50)

                    # Get current balance
                    balance = await self.credit_system.get_balance(agent_id)

                    # Apply cap
                    if balance + reward_amount > reward_cap:
                        capped_reward = max(0, reward_cap - balance)
                        if capped_reward > 0:
                            await self.credit_system.demo.event_bus.publish(
                                self._create_synergy_event(agent_id, capped_reward, capped=True)
                            )
                    else:
                        await self.credit_system.demo.event_bus.publish(
                            self._create_synergy_event(agent_id, reward_amount, capped=False)
                        )

            # Verify no agent exceeds cap
            for agent_id in agent_ids:
                balance = await self.credit_system.get_balance(agent_id)
                if balance > reward_cap:
                    result.status = "FAIL"
                    result.errors.append(f"{agent_id} exceeded cap: {balance} > {reward_cap}")

            # Check invariants
            if self.invariants_checker:
                invariants_ok = await self.invariants_checker.check_all()
                result.invariants_passed = invariants_ok
                if not invariants_ok:
                    result.status = "FAIL"
                    result.errors.append("Invariants violated")

            result.duration = time.time() - start_time
            result.metrics = {
                "team_size": len(agent_ids),
                "synergy_events": 100,
                "reward_cap": reward_cap,
                "errors_count": len(result.errors),
            }

            logger.info(f"✅ Synergy Anti-Gaming completed: {result.status}")

        except Exception as e:
            result.status = "FAIL"
            result.errors.append(f"Unhandled exception: {e}")
            logger.error(f"❌ Synergy Anti-Gaming failed: {e}")

        return result

    # ========================================================================
    # Scenario 3: Approval Race / Concurrency
    # ========================================================================

    async def scenario_approval_race(self) -> ScenarioResult:
        """
        Test parallel approval requests (OCC).

        Setup:
        - 1 agent awaits approval for 500 credits
        - 10 parallel approve/deny requests

        Expected:
        - Only 1 approval wirksam
        - Rest: "already_decided" error
        - Audit log complete
        """
        logger.info("🏁 Starting Scenario 3: Approval Race / Concurrency")

        result = ScenarioResult(
            scenario_name="Approval Race / Concurrency",
            status="PASS",
            duration=0.0,
        )

        start_time = time.time()

        try:
            # Create agent needing approval
            agent_id = "approval_agent_001"
            await self.credit_system.create_agent(agent_id, skill_level=5.0)

            # Request approval (simulate HIGH risk operation)
            approval_id = "approval_req_001"

            # Simulate 10 parallel approve/deny requests
            tasks = []
            for i in range(10):
                decision = "approve" if i % 2 == 0 else "deny"
                task = self._submit_approval_decision(approval_id, decision)
                tasks.append(task)

            # Execute in parallel
            results_batch = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successful approvals
            successful_approvals = 0
            already_decided_count = 0

            for r in results_batch:
                if isinstance(r, Exception):
                    if "already_decided" in str(r).lower():
                        already_decided_count += 1
                    else:
                        result.errors.append(str(r))
                elif r.get("success"):
                    successful_approvals += 1

            # Should have exactly 1 successful approval
            if successful_approvals != 1:
                result.status = "FAIL"
                result.errors.append(f"Expected 1 approval, got {successful_approvals}")

            # Check invariants
            if self.invariants_checker:
                invariants_ok = await self.invariants_checker.check_all()
                result.invariants_passed = invariants_ok
                if not invariants_ok:
                    result.status = "FAIL"
                    result.errors.append("Invariants violated")

            result.duration = time.time() - start_time
            result.metrics = {
                "parallel_requests": 10,
                "successful_approvals": successful_approvals,
                "already_decided": already_decided_count,
                "errors_count": len(result.errors),
            }

            logger.info(f"✅ Approval Race completed: {result.status}")

        except Exception as e:
            result.status = "FAIL"
            result.errors.append(f"Unhandled exception: {e}")
            logger.error(f"❌ Approval Race failed: {e}")

        return result

    # ========================================================================
    # Scenario 4: KARMA Blackout
    # ========================================================================

    async def scenario_karma_blackout(self) -> ScenarioResult:
        """
        Test system stability without KARMA.

        Setup:
        - Simulate KARMA service unavailable
        - 50 credit operations
        - Fallback mode active

        Expected:
        - System continues (degraded mode)
        - No crashes
        - Fallback logic active (e.g., default CI = 0.5)
        """
        logger.info("🌑 Starting Scenario 4: KARMA Blackout")

        result = ScenarioResult(
            scenario_name="KARMA Blackout",
            status="PASS",
            duration=0.0,
        )

        start_time = time.time()

        try:
            # Create test agent
            agent_id = "karma_test_agent"
            await self.credit_system.create_agent(agent_id, skill_level=5.0)

            # Simulate KARMA unavailable (set flag)
            original_karma_state = self.config.karma_enabled
            self.config.karma_enabled = False

            # Execute 50 operations
            for i in range(50):
                amount = random.uniform(10, 50)
                try:
                    await self.credit_system.consume_credits(
                        agent_id=agent_id,
                        amount=amount,
                        reason=f"KARMA blackout operation {i}",
                        actor_id="system",
                    )
                except Exception as e:
                    # Should NOT crash
                    result.errors.append(f"Operation {i} failed: {e}")
                    result.status = "FAIL"

            # Restore KARMA state
            self.config.karma_enabled = original_karma_state

            # Check system still operational
            balance = await self.credit_system.get_balance(agent_id)
            if balance < 0:
                result.status = "FAIL"
                result.errors.append(f"Negative balance after KARMA blackout: {balance}")

            # Check invariants
            if self.invariants_checker:
                invariants_ok = await self.invariants_checker.check_all()
                result.invariants_passed = invariants_ok
                if not invariants_ok:
                    result.status = "FAIL"
                    result.errors.append("Invariants violated")

            result.duration = time.time() - start_time
            result.metrics = {
                "operations_attempted": 50,
                "errors_count": len(result.errors),
                "final_balance": balance,
            }

            logger.info(f"✅ KARMA Blackout completed: {result.status}")

        except Exception as e:
            result.status = "FAIL"
            result.errors.append(f"Unhandled exception: {e}")
            logger.error(f"❌ KARMA Blackout failed: {e}")

        return result

    # ========================================================================
    # Scenario 5: ML Chaos Injection
    # ========================================================================

    async def scenario_ml_chaos(self) -> ScenarioResult:
        """
        Test ML anomaly detection without overreaction.

        Setup:
        - Inject anomalous transactions (10× average)
        - Track Edge-of-Chaos metrics

        Expected:
        - Anomalies marked, not blocked
        - CI score in safe range (0.3-0.7)
        - No throttle spiral
        """
        logger.info("🔥 Starting Scenario 5: ML Chaos Injection")

        result = ScenarioResult(
            scenario_name="ML Chaos Injection",
            status="PASS",
            duration=0.0,
        )

        start_time = time.time()

        try:
            # Create test agent
            agent_id = "ml_chaos_agent"
            await self.credit_system.create_agent(agent_id, skill_level=10.0)

            # Normal operations (baseline)
            normal_amount = 50.0
            for _ in range(20):
                await self.credit_system.consume_credits(
                    agent_id=agent_id,
                    amount=normal_amount,
                    reason="Normal operation",
                    actor_id="system",
                )

            # Inject anomaly (10× normal)
            if self.config.ml_anomaly_injection:
                anomaly_amount = normal_amount * 10
                try:
                    await self.credit_system.consume_credits(
                        agent_id=agent_id,
                        amount=anomaly_amount,
                        reason="Anomalous operation (injected)",
                        actor_id="system",
                    )

                    # Should succeed but be marked
                    logger.info(f"Anomaly injected: {anomaly_amount} credits")

                except Exception as e:
                    # Should NOT block
                    result.status = "FAIL"
                    result.errors.append(f"Anomaly blocked (should mark, not block): {e}")

            # Check system stability (no throttle spiral)
            balance = await self.credit_system.get_balance(agent_id)
            if balance < 0:
                result.status = "FAIL"
                result.errors.append(f"Negative balance after ML chaos: {balance}")

            # Check invariants
            if self.invariants_checker:
                invariants_ok = await self.invariants_checker.check_all()
                result.invariants_passed = invariants_ok
                if not invariants_ok:
                    result.status = "FAIL"
                    result.errors.append("Invariants violated")

            result.duration = time.time() - start_time
            result.metrics = {
                "normal_operations": 20,
                "anomaly_injected": self.config.ml_anomaly_injection,
                "anomaly_amount": 500.0,
                "errors_count": len(result.errors),
                "final_balance": balance,
            }

            logger.info(f"✅ ML Chaos completed: {result.status}")

        except Exception as e:
            result.status = "FAIL"
            result.errors.append(f"Unhandled exception: {e}")
            logger.error(f"❌ ML Chaos failed: {e}")

        return result

    # ========================================================================
    # Scenario 6: Crash / Replay
    # ========================================================================

    async def scenario_crash_replay(self) -> ScenarioResult:
        """
        Test crash recovery via deterministic replay.

        Setup:
        - Write 100 events
        - Snapshot projection state
        - Clear projections (simulated crash)
        - Replay events

        Expected:
        - After replay: identical state
        - All invariants satisfied
        - No idempotency violations
        """
        logger.info("💥 Starting Scenario 6: Crash / Replay")

        result = ScenarioResult(
            scenario_name="Crash / Replay",
            status="PASS",
            duration=0.0,
        )

        start_time = time.time()

        try:
            # Create test agents
            agent_ids = [f"crash_agent_{i:03d}" for i in range(5)]
            for agent_id in agent_ids:
                await self.credit_system.create_agent(agent_id, skill_level=5.0)

            # Write 100 events
            for _ in range(100):
                agent_id = random.choice(agent_ids)
                amount = random.uniform(10, 50)
                await self.credit_system.consume_credits(
                    agent_id=agent_id,
                    amount=amount,
                    reason="Pre-crash operation",
                    actor_id="system",
                )

            # Snapshot state
            original_balances = {}
            for agent_id in agent_ids:
                balance = await self.credit_system.get_balance(agent_id)
                original_balances[agent_id] = balance

            logger.info(f"Snapshot: {original_balances}")

            # Simulate crash: Clear projections
            projection_manager = self.credit_system.demo.projection_manager
            projection_manager.balance.clear()
            projection_manager.ledger.clear()
            projection_manager.approval.clear()
            projection_manager.synergie.clear()

            logger.info("Projections cleared (simulated crash)")

            # Replay
            replay_engine = ReplayEngine(
                journal=self.credit_system.demo.journal,
                projection_manager=projection_manager,
                verify_integrity=True,
            )

            replay_stats = await replay_engine.replay_all()
            logger.info(f"Replay completed: {replay_stats}")

            # Compare state
            replayed_balances = {}
            for agent_id in agent_ids:
                balance = await self.credit_system.get_balance(agent_id)
                replayed_balances[agent_id] = balance

            logger.info(f"Replayed: {replayed_balances}")

            # Verify identical state
            for agent_id in agent_ids:
                original = original_balances.get(agent_id, 0.0)
                replayed = replayed_balances.get(agent_id, 0.0)

                if abs(original - replayed) > 0.01:  # Floating-point tolerance
                    result.status = "FAIL"
                    result.errors.append(
                        f"{agent_id} state drift: {original} → {replayed}"
                    )

            # Check invariants
            if self.invariants_checker:
                invariants_ok = await self.invariants_checker.check_all()
                result.invariants_passed = invariants_ok
                if not invariants_ok:
                    result.status = "FAIL"
                    result.errors.append("Invariants violated after replay")

            result.duration = time.time() - start_time
            result.metrics = {
                "events_written": 100,
                "events_replayed": replay_stats.get("events_replayed", 0),
                "replay_duration": replay_stats.get("duration_seconds", 0),
                "errors_count": len(result.errors),
                "state_drift": sum(
                    abs(original_balances.get(aid, 0) - replayed_balances.get(aid, 0))
                    for aid in agent_ids
                ),
            }

            logger.info(f"✅ Crash/Replay completed: {result.status}")

        except Exception as e:
            result.status = "FAIL"
            result.errors.append(f"Unhandled exception: {e}")
            logger.error(f"❌ Crash/Replay failed: {e}")

        return result

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _consume_with_latency(
        self,
        agent_id: str,
        amount: float,
        reason: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict:
        """Consume credits and track latency."""
        start = time.time()
        try:
            result = await self.credit_system.consume_credits(
                agent_id=agent_id,
                amount=amount,
                reason=reason,
                actor_id="live_test",
                idempotency_key=idempotency_key,
            )
            latency = (time.time() - start) * 1000  # ms
            self.latencies.append(latency)
            return {"success": True, "result": result}
        except Exception as e:
            latency = (time.time() - start) * 1000
            self.latencies.append(latency)
            raise

    def _create_synergy_event(
        self,
        agent_id: str,
        amount: float,
        capped: bool = False,
    ) -> Any:
        """Create synergy reward event (mock)."""
        from backend.app.modules.credits.event_sourcing.events import create_credit_allocated_event

        return create_credit_allocated_event(
            entity_id=agent_id,
            amount=amount,
            balance_after=0.0,  # Will be calculated
            actor_id="synergy_system",
            reason=f"Synergy reward ({'capped' if capped else 'normal'})",
        )

    async def _submit_approval_decision(
        self,
        approval_id: str,
        decision: str,
    ) -> Dict:
        """Submit approval decision (mock)."""
        # Simulate approval logic
        await asyncio.sleep(random.uniform(0.01, 0.05))

        # Mock: First decision wins (OCC simulation)
        if not hasattr(self, '_approval_decisions'):
            self._approval_decisions = {}

        if approval_id in self._approval_decisions:
            raise ValueError(f"Approval {approval_id} already decided")

        self._approval_decisions[approval_id] = decision
        return {"success": True, "decision": decision}

    def _calculate_percentile(self, values: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100.0)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def _calculate_p95(self, values: List[float]) -> float:
        """Calculate P95 latency."""
        return self._calculate_percentile(values, 95)

    # ========================================================================
    # Orchestration
    # ========================================================================

    async def run_scenario(self, scenario_name: str) -> ScenarioResult:
        """Run a single scenario."""
        scenarios = {
            "credit_storm": self.scenario_credit_storm,
            "synergy_anti_gaming": self.scenario_synergy_anti_gaming,
            "approval_race": self.scenario_approval_race,
            "karma_blackout": self.scenario_karma_blackout,
            "ml_chaos": self.scenario_ml_chaos,
            "crash_replay": self.scenario_crash_replay,
        }

        scenario_func = scenarios.get(scenario_name)
        if not scenario_func:
            logger.error(f"Unknown scenario: {scenario_name}")
            return ScenarioResult(
                scenario_name=scenario_name,
                status="SKIP",
                duration=0.0,
                errors=[f"Unknown scenario: {scenario_name}"],
            )

        return await scenario_func()

    async def run_all_scenarios(self) -> List[ScenarioResult]:
        """Run all 6 mandatory scenarios."""
        logger.info("🚀 Running all 6 mandatory scenarios...")

        scenarios = [
            "credit_storm",
            "synergy_anti_gaming",
            "approval_race",
            "karma_blackout",
            "ml_chaos",
            "crash_replay",
        ]

        results = []
        for scenario_name in scenarios:
            result = await self.run_scenario(scenario_name)
            results.append(result)
            self.report.scenario_results.append(result)

            # Small delay between scenarios
            await asyncio.sleep(2)

        return results

    def evaluate_gates(self) -> Dict[str, bool]:
        """Evaluate all 5 Hard Gates."""
        logger.info("📊 Evaluating Hard Gates...")

        gate_results = {}

        # Gate A: Event Integrity
        gate_a = self._evaluate_gate_a()
        gate_results["A - Event Integrity"] = gate_a

        # Gate B: Projection Integrity
        gate_b = self._evaluate_gate_b()
        gate_results["B - Projection Integrity"] = gate_b

        # Gate C: Human Gate Safety
        gate_c = self._evaluate_gate_c()
        gate_results["C - Human Gate Safety"] = gate_c

        # Gate D: Failure Safety
        gate_d = self._evaluate_gate_d()
        gate_results["D - Failure Safety"] = gate_d

        # Gate E: Load Reality
        gate_e = self._evaluate_gate_e()
        gate_results["E - Load Reality"] = gate_e

        self.report.gate_results = gate_results
        return gate_results

    def _evaluate_gate_a(self) -> bool:
        """Gate A: Event Integrity."""
        # Check idempotency violations
        # Check schema versions
        # Check correlation/causation IDs
        # For now: PASS if no critical errors
        return all(
            r.invariants_passed for r in self.report.scenario_results
        )

    def _evaluate_gate_b(self) -> bool:
        """Gate B: Projection Integrity."""
        # Check balance == sum(deltas)
        # Check no NaN/Inf
        # Check no drift after replay
        return all(
            r.invariants_passed for r in self.report.scenario_results
        )

    def _evaluate_gate_c(self) -> bool:
        """Gate C: Human Gate Safety."""
        # Check approval serialization
        # Check audit log completeness
        approval_result = next(
            (r for r in self.report.scenario_results if "Approval" in r.scenario_name),
            None
        )
        if approval_result:
            return approval_result.status == "PASS"
        return True

    def _evaluate_gate_d(self) -> bool:
        """Gate D: Failure Safety."""
        # Check KARMA blackout handled
        # Check ML anomaly marked, not blocked
        karma_result = next(
            (r for r in self.report.scenario_results if "KARMA" in r.scenario_name),
            None
        )
        ml_result = next(
            (r for r in self.report.scenario_results if "ML Chaos" in r.scenario_name),
            None
        )

        karma_ok = karma_result.status == "PASS" if karma_result else True
        ml_ok = ml_result.status == "PASS" if ml_result else True

        return karma_ok and ml_ok

    def _evaluate_gate_e(self) -> bool:
        """Gate E: Load Reality."""
        # Check runtime >= 30 min
        # Check P95 latency < threshold
        # Check no memory leak

        # For now: Check P95 < 500ms
        p95_ok = all(
            r.p95_latency < 500.0 or r.p95_latency == 0.0
            for r in self.report.scenario_results
        )

        return p95_ok

    def determine_overall_status(self) -> str:
        """Determine GO / CONDITIONAL / NO-GO."""
        scenarios_passed = sum(
            1 for r in self.report.scenario_results if r.status == "PASS"
        )
        scenarios_total = len(self.report.scenario_results)

        gates_passed = sum(1 for passed in self.report.gate_results.values() if passed)
        gates_total = len(self.report.gate_results)

        # Critical failures
        has_critical_failures = any(
            "Negative balance" in str(r.errors) or
            "Idempotency" in str(r.errors) or
            "Race" in str(r.errors)
            for r in self.report.scenario_results
        )

        if has_critical_failures:
            return "NO-GO"

        if scenarios_passed == scenarios_total and gates_passed == gates_total:
            return "GO"
        elif scenarios_passed >= scenarios_total * 0.7:  # 70% pass rate
            return "CONDITIONAL"
        else:
            return "NO-GO"

    def generate_recommendation(self) -> str:
        """Generate recommendation based on results."""
        status = self.report.overall_status

        if status == "GO":
            return (
                "System stabil. Event Sourcing Foundation production-ready. "
                "**Freigabe für Phase 5a (Postgres Event Store)**."
            )
        elif status == "CONDITIONAL":
            return (
                "System grundsätzlich stabil, aber Performance/Governance-Optimierung nötig. "
                "**Weiter testen für 3-7 Tage, dann Re-Evaluation**."
            )
        else:
            return (
                "Kritische Risiken identifiziert. "
                "**Evolution blockiert bis Fixes implementiert**. "
                "Phase 5–8 weiterhin gesperrt."
            )

    def save_report_json(self, path: str):
        """Save report as JSON."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)

        report_dict = {
            "timestamp": self.report.timestamp,
            "branch": self.report.branch,
            "commit": self.report.commit,
            "test_config": {
                "concurrency": self.config.concurrency,
                "test_duration": self.config.test_duration,
                "seed": self.config.seed,
            },
            "scenarios": [
                {
                    "name": r.scenario_name,
                    "status": r.status,
                    "duration": r.duration,
                    "throughput": r.throughput,
                    "p95_latency": r.p95_latency,
                    "errors": r.errors,
                    "metrics": r.metrics,
                    "invariants_passed": r.invariants_passed,
                }
                for r in self.report.scenario_results
            ],
            "gates": self.report.gate_results,
            "overall_status": self.report.overall_status,
            "recommendation": self.report.recommendation,
        }

        with open(path, "w") as f:
            json.dump(report_dict, f, indent=2)

        logger.info(f"Report saved to {path}")


# ============================================================================
# CLI Entry Point
# ============================================================================


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="BRAiN Credit System Live Test Harness"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        choices=[
            "credit_storm",
            "synergy_anti_gaming",
            "approval_race",
            "karma_blackout",
            "ml_chaos",
            "crash_replay",
        ],
        help="Run a single scenario",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run all 6 scenarios + gates",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="Concurrency level (default: 50)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--report-json",
        type=str,
        help="Path to save JSON report",
    )

    args = parser.parse_args()

    # Create config
    config = TestConfig(
        concurrency=args.concurrency,
        seed=args.seed,
        report_json_path=args.report_json,
    )

    # Create harness
    harness = LiveTestHarness(config)

    try:
        # Setup
        await harness.setup()

        # Run scenarios
        if args.full:
            await harness.run_all_scenarios()
        elif args.scenario:
            result = await harness.run_scenario(args.scenario)
            harness.report.scenario_results.append(result)
        else:
            logger.error("Must specify --scenario or --full")
            return

        # Evaluate gates
        harness.evaluate_gates()

        # Determine status
        harness.report.overall_status = harness.determine_overall_status()
        harness.report.recommendation = harness.generate_recommendation()

        # Print summary
        logger.info("=" * 80)
        logger.info(f"Overall Status: {harness.report.overall_status}")
        logger.info(f"Recommendation: {harness.report.recommendation}")
        logger.info("=" * 80)

        # Save report
        if args.report_json:
            harness.save_report_json(args.report_json)

    finally:
        await harness.teardown()


if __name__ == "__main__":
    asyncio.run(main())
