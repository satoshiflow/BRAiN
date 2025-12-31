"""
E2E Test for NeuroRail Integration (Phase 1: Observe-only).

Tests the complete trace chain flow:
1. Mission creation → Plan → Job → Attempt
2. State transitions (lifecycle)
3. Audit logging
4. Telemetry metrics collection
5. Governor mode decision

This test validates that all NeuroRail modules are properly integrated
and can work together end-to-end.
"""

from __future__ import annotations

import sys
import os
import time
from typing import Dict, Any, Optional

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ============================================================================
# Test 1: Verify All NeuroRail Endpoints Are Registered
# ============================================================================

def test_neurorail_endpoints_registered():
    """Verify all NeuroRail API endpoints are registered."""
    response = client.get("/debug/routes")
    assert response.status_code == 200

    routes = response.json()["routes"]

    # Expected NeuroRail endpoints
    expected_prefixes = [
        "/api/neurorail/v1/identity",
        "/api/neurorail/v1/lifecycle",
        "/api/neurorail/v1/audit",
        "/api/neurorail/v1/telemetry",
        "/api/neurorail/v1/execution",
        "/api/governor/v1",
    ]

    for prefix in expected_prefixes:
        matching_routes = [r for r in routes if prefix in r]
        assert len(matching_routes) > 0, f"No routes found for {prefix}"
        print(f"✓ {prefix}: {len(matching_routes)} endpoints registered")


# ============================================================================
# Test 2: Complete Trace Chain Generation
# ============================================================================

@pytest.mark.asyncio
async def test_trace_chain_generation():
    """
    Test complete trace chain creation:
    mission_id → plan_id → job_id → attempt_id
    """
    # 1. Create Mission Identity
    response = client.post("/api/neurorail/v1/identity/mission", json={
        "parent_mission_id": None,
        "tags": {"environment": "test", "type": "e2e"}
    })
    assert response.status_code == 200
    mission = response.json()
    mission_id = mission["mission_id"]
    assert mission_id.startswith("m_")
    print(f"✓ Mission created: {mission_id}")

    # 2. Create Plan Identity
    response = client.post("/api/neurorail/v1/identity/plan", json={
        "mission_id": mission_id,
        "plan_type": "sequential",
        "tags": {"stage": "planning"}
    })
    assert response.status_code == 200
    plan = response.json()
    plan_id = plan["plan_id"]
    assert plan_id.startswith("p_")
    print(f"✓ Plan created: {plan_id}")

    # 3. Create Job Identity
    response = client.post("/api/neurorail/v1/identity/job", json={
        "plan_id": plan_id,
        "job_type": "llm_call",
        "tags": {"model": "test-model"}
    })
    assert response.status_code == 200
    job = response.json()
    job_id = job["job_id"]
    assert job_id.startswith("j_")
    print(f"✓ Job created: {job_id}")

    # 4. Create Attempt Identity
    response = client.post("/api/neurorail/v1/identity/attempt", json={
        "job_id": job_id,
        "attempt_number": 1,
        "retry_reason": None
    })
    assert response.status_code == 200
    attempt = response.json()
    attempt_id = attempt["attempt_id"]
    assert attempt_id.startswith("a_")
    print(f"✓ Attempt created: {attempt_id}")

    # 5. Retrieve Trace Chain
    response = client.get(f"/api/neurorail/v1/identity/trace/attempt/{attempt_id}")
    assert response.status_code == 200
    trace = response.json()

    # Verify complete chain
    assert trace["mission"]["mission_id"] == mission_id
    assert trace["plan"]["plan_id"] == plan_id
    assert trace["job"]["job_id"] == job_id
    assert trace["attempt"]["attempt_id"] == attempt_id
    print(f"✓ Trace chain verified: {mission_id} → {plan_id} → {job_id} → {attempt_id}")


# ============================================================================
# Test 3: State Machine Transitions
# ============================================================================

@pytest.mark.asyncio
async def test_lifecycle_state_transitions():
    """Test state machine transitions for attempt lifecycle."""
    # 1. Create attempt
    response = client.post("/api/neurorail/v1/identity/mission", json={})
    mission_id = response.json()["mission_id"]

    response = client.post("/api/neurorail/v1/identity/plan", json={"mission_id": mission_id})
    plan_id = response.json()["plan_id"]

    response = client.post("/api/neurorail/v1/identity/job", json={"plan_id": plan_id, "job_type": "test"})
    job_id = response.json()["job_id"]

    response = client.post("/api/neurorail/v1/identity/attempt", json={"job_id": job_id, "attempt_number": 1})
    attempt_id = response.json()["attempt_id"]

    # 2. Transition: PENDING → RUNNING
    response = client.post("/api/neurorail/v1/lifecycle/transition/attempt", json={
        "entity_id": attempt_id,
        "transition": "start",
        "metadata": {"started_by": "test"}
    })
    assert response.status_code == 200
    event = response.json()
    assert event["from_state"] == "pending"
    assert event["to_state"] == "running"
    print(f"✓ Transition: PENDING → RUNNING")

    # 3. Transition: RUNNING → SUCCEEDED
    response = client.post("/api/neurorail/v1/lifecycle/transition/attempt", json={
        "entity_id": attempt_id,
        "transition": "complete",
        "metadata": {"duration_ms": 150}
    })
    assert response.status_code == 200
    event = response.json()
    assert event["from_state"] == "running"
    assert event["to_state"] == "succeeded"
    print(f"✓ Transition: RUNNING → SUCCEEDED")

    # 4. Verify current state
    response = client.get(f"/api/neurorail/v1/lifecycle/state/attempt/{attempt_id}")
    assert response.status_code == 200
    state_data = response.json()
    assert state_data["current_state"] == "succeeded"
    print(f"✓ Current state verified: SUCCEEDED")


# ============================================================================
# Test 4: Audit Logging
# ============================================================================

@pytest.mark.asyncio
async def test_audit_logging():
    """Test audit event logging."""
    # 1. Create trace chain
    response = client.post("/api/neurorail/v1/identity/mission", json={})
    mission_id = response.json()["mission_id"]

    response = client.post("/api/neurorail/v1/identity/plan", json={"mission_id": mission_id})
    plan_id = response.json()["plan_id"]

    response = client.post("/api/neurorail/v1/identity/job", json={"plan_id": plan_id, "job_type": "test"})
    job_id = response.json()["job_id"]

    response = client.post("/api/neurorail/v1/identity/attempt", json={"job_id": job_id, "attempt_number": 1})
    attempt_id = response.json()["attempt_id"]

    # 2. Log audit event
    response = client.post("/api/neurorail/v1/audit/log", json={
        "mission_id": mission_id,
        "plan_id": plan_id,
        "job_id": job_id,
        "attempt_id": attempt_id,
        "event_type": "execution_start",
        "event_category": "execution",
        "severity": "info",
        "message": "Test execution started",
        "details": {"test_key": "test_value"}
    })
    assert response.status_code == 200
    event = response.json()
    audit_id = event["audit_id"]
    assert audit_id.startswith("aud_")
    print(f"✓ Audit event logged: {audit_id}")

    # 3. Query audit events by mission
    response = client.get(f"/api/neurorail/v1/audit/events?mission_id={mission_id}&limit=10")
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) > 0
    assert any(e["audit_id"] == audit_id for e in events)
    print(f"✓ Audit events retrieved: {len(events)} events")


# ============================================================================
# Test 5: Governor Mode Decision
# ============================================================================

@pytest.mark.asyncio
async def test_governor_mode_decision():
    """Test governor mode decision (direct vs. rail)."""
    # Test 1: LLM call → should be RAIL mode
    response = client.post("/api/governor/v1/decide", json={
        "job_type": "llm_call",
        "context": {"model": "gpt-4"},
        "shadow_evaluate": False
    })
    assert response.status_code == 200
    decision = response.json()
    assert decision["mode"] == "rail"
    assert "llm" in decision["reason"].lower() or "governance" in decision["reason"].lower()
    print(f"✓ LLM call → RAIL mode (reason: {decision['reason']})")

    # Test 2: Personal data → should be RAIL mode
    response = client.post("/api/governor/v1/decide", json={
        "job_type": "data_processing",
        "context": {"uses_personal_data": True},
        "shadow_evaluate": False
    })
    assert response.status_code == 200
    decision = response.json()
    assert decision["mode"] == "rail"
    assert "personal" in decision["reason"].lower() or "dsgvo" in decision["reason"].lower()
    print(f"✓ Personal data → RAIL mode (reason: {decision['reason']})")

    # Test 3: Low-risk operation → should be DIRECT mode
    response = client.post("/api/governor/v1/decide", json={
        "job_type": "read_config",
        "context": {"uses_personal_data": False},
        "shadow_evaluate": False
    })
    assert response.status_code == 200
    decision = response.json()
    assert decision["mode"] == "direct"
    print(f"✓ Low-risk operation → DIRECT mode (reason: {decision['reason']})")


# ============================================================================
# Test 6: Telemetry Metrics (Snapshot)
# ============================================================================

@pytest.mark.asyncio
async def test_telemetry_snapshot():
    """Test telemetry snapshot endpoint."""
    response = client.get("/api/neurorail/v1/telemetry/snapshot")
    assert response.status_code == 200
    snapshot = response.json()

    # Verify snapshot structure
    assert "timestamp" in snapshot
    assert "entity_counts" in snapshot
    assert "active_executions" in snapshot

    # Entity counts should have mission/plan/job/attempt
    counts = snapshot["entity_counts"]
    assert "missions" in counts
    assert "plans" in counts
    assert "jobs" in counts
    assert "attempts" in counts

    print(f"✓ Telemetry snapshot retrieved:")
    print(f"  - Missions: {counts['missions']}")
    print(f"  - Plans: {counts['plans']}")
    print(f"  - Jobs: {counts['jobs']}")
    print(f"  - Attempts: {counts['attempts']}")


# ============================================================================
# Test 7: End-to-End Execution Flow (Integration)
# ============================================================================

@pytest.mark.asyncio
async def test_e2e_execution_flow():
    """
    Complete end-to-end test simulating real execution flow:
    1. Governor decides mode
    2. Create trace chain
    3. Execute with observation
    4. Verify audit trail
    5. Check telemetry
    """
    print("\n=== E2E Execution Flow Test ===")

    # Step 1: Governor decision
    response = client.post("/api/governor/v1/decide", json={
        "job_type": "llm_call",
        "context": {"model": "test-model", "environment": "development"},
        "shadow_evaluate": False
    })
    assert response.status_code == 200
    decision = response.json()
    print(f"1. Governor decision: {decision['mode']} (reason: {decision['reason']})")

    # Step 2: Create trace chain
    response = client.post("/api/neurorail/v1/identity/mission", json={"tags": {"test": "e2e"}})
    mission_id = response.json()["mission_id"]

    response = client.post("/api/neurorail/v1/identity/plan", json={"mission_id": mission_id})
    plan_id = response.json()["plan_id"]

    response = client.post("/api/neurorail/v1/identity/job", json={"plan_id": plan_id, "job_type": "llm_call"})
    job_id = response.json()["job_id"]

    response = client.post("/api/neurorail/v1/identity/attempt", json={"job_id": job_id, "attempt_number": 1})
    attempt_id = response.json()["attempt_id"]
    print(f"2. Trace chain created: {mission_id} → {plan_id} → {job_id} → {attempt_id}")

    # Step 3: State transitions (simulating execution)
    response = client.post("/api/neurorail/v1/lifecycle/transition/attempt", json={
        "entity_id": attempt_id,
        "transition": "start",
        "metadata": {"started_at": time.time()}
    })
    assert response.status_code == 200
    print(f"3. Execution started: attempt {attempt_id} → RUNNING")

    # Simulate execution delay
    time.sleep(0.1)

    response = client.post("/api/neurorail/v1/lifecycle/transition/attempt", json={
        "entity_id": attempt_id,
        "transition": "complete",
        "metadata": {"duration_ms": 100, "result": "success"}
    })
    assert response.status_code == 200
    print(f"4. Execution completed: attempt {attempt_id} → SUCCEEDED")

    # Step 4: Verify audit trail
    response = client.get(f"/api/neurorail/v1/audit/events?attempt_id={attempt_id}&limit=10")
    assert response.status_code == 200
    audit_events = response.json()["events"]
    print(f"5. Audit trail: {len(audit_events)} events logged")

    # Step 5: Check telemetry snapshot
    response = client.get("/api/neurorail/v1/telemetry/snapshot")
    assert response.status_code == 200
    snapshot = response.json()
    print(f"6. Telemetry snapshot: {snapshot['entity_counts']['attempts']} total attempts")

    print("✅ E2E execution flow completed successfully")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("NeuroRail E2E Integration Test Suite (Phase 1: Observe-only)")
    print("=" * 80)

    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
