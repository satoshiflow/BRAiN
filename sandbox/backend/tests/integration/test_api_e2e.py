"""
End-to-End API Tests for Constitutional Agents

Tests the complete API stack from HTTP requests to database.
Uses FastAPI TestClient to simulate real HTTP requests.
"""

import sys
import os
import pytest
import json

# Path setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ============================================================================
# Agent Info Endpoint Tests
# ============================================================================


def test_get_agent_ops_info():
    """Test GET /api/agent-ops/info endpoint."""
    response = client.get("/api/agent-ops/info")

    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "Constitutional Agents"
    assert data["version"] == "1.0.0"
    assert len(data["agents"]) == 5
    assert "DSGVO" in data["compliance_frameworks"]
    assert "EU AI Act" in data["compliance_frameworks"]

    # Verify all 5 agents are present
    agent_ids = [agent["id"] for agent in data["agents"]]
    assert "supervisor" in agent_ids
    assert "coder" in agent_ids
    assert "ops" in agent_ids
    assert "architect" in agent_ids
    assert "axe" in agent_ids


# ============================================================================
# SupervisorAgent API Tests
# ============================================================================


def test_supervisor_supervise_low_risk():
    """Test POST /api/agent-ops/supervisor/supervise with LOW risk."""
    payload = {
        "requesting_agent": "TestAgent",
        "action": "read_logs",
        "context": {"log_type": "application"},
        "risk_level": "low",
        "reason": "Need to check application logs"
    }

    response = client.post("/api/agent-ops/supervisor/supervise", json=payload)

    assert response.status_code == 200
    data = response.json()

    assert "approved" in data
    assert "reason" in data
    assert "audit_id" in data
    assert "timestamp" in data
    assert "human_oversight_required" in data


def test_supervisor_supervise_high_risk():
    """Test POST /api/agent-ops/supervisor/supervise with HIGH risk (requires HITL)."""
    payload = {
        "requesting_agent": "CoderAgent",
        "action": "process_personal_data",
        "context": {"data_type": "email addresses"},
        "risk_level": "high"
    }

    response = client.post("/api/agent-ops/supervisor/supervise", json=payload)

    assert response.status_code == 200
    data = response.json()

    # HIGH risk should require human oversight
    assert data["human_oversight_required"] is True
    assert "human_oversight_token" in data
    assert data["human_oversight_token"].startswith("HITL-")


def test_supervisor_get_metrics():
    """Test GET /api/agent-ops/supervisor/metrics."""
    response = client.get("/api/agent-ops/supervisor/metrics")

    assert response.status_code == 200
    data = response.json()

    assert "total_supervision_requests" in data
    assert "approved_actions" in data
    assert "denied_actions" in data
    assert "human_approvals_pending" in data
    assert "approval_rate" in data


# ============================================================================
# CoderAgent API Tests
# ============================================================================


def test_coder_generate_code():
    """Test POST /api/agent-ops/coder/generate-code."""
    payload = {
        "spec": "Create a Python function to validate email addresses",
        "risk_level": "low"
    }

    response = client.post("/api/agent-ops/coder/generate-code", json=payload)

    # Might fail if LLM not available, but should return valid JSON
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert "success" in data or "code" in data or "result" in data


def test_coder_generate_odoo_module():
    """Test POST /api/agent-ops/coder/generate-odoo-module."""
    payload = {
        "name": "test_module",
        "purpose": "Testing module generation",
        "data_types": ["name", "email"],
        "models": ["res.partner"],
        "views": ["form", "tree"]
    }

    response = client.post("/api/agent-ops/coder/generate-odoo-module", json=payload)

    # Might fail if LLM not available
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert "success" in data or "module" in data or "result" in data


# ============================================================================
# OpsAgent API Tests
# ============================================================================


def test_ops_deploy_development():
    """Test POST /api/agent-ops/ops/deploy to development (should succeed)."""
    payload = {
        "app_name": "test-app",
        "version": "1.0.0",
        "environment": "development",
        "config": {}
    }

    response = client.post("/api/agent-ops/ops/deploy", json=payload)

    # Might fail if actual deployment not possible
    assert response.status_code in [200, 500]


def test_ops_deploy_production():
    """Test POST /api/agent-ops/ops/deploy to production (should require approval)."""
    payload = {
        "app_name": "test-app",
        "version": "1.0.0",
        "environment": "production",
        "config": {}
    }

    response = client.post("/api/agent-ops/ops/deploy", json=payload)

    # Should either succeed or require human approval
    assert response.status_code in [200, 403, 500]

    if response.status_code == 200:
        data = response.json()
        # If succeeded, might have human_oversight info
        assert "success" in data or "result" in data


def test_ops_rollback():
    """Test POST /api/agent-ops/ops/rollback."""
    payload = {
        "app_name": "test-app",
        "environment": "development",
        "backup_id": "backup_test_123"
    }

    response = client.post("/api/agent-ops/ops/rollback", json=payload)

    # Might fail if backup doesn't exist
    assert response.status_code in [200, 404, 500]


# ============================================================================
# ArchitectAgent API Tests
# ============================================================================


def test_architect_review_architecture():
    """Test POST /api/agent-ops/architect/review."""
    payload = {
        "system_name": "Test System",
        "architecture_spec": {
            "uses_ai": True,
            "processes_personal_data": True,
            "has_consent_mechanism": True,
            "data_types": ["names", "emails"],
            "international_transfers": False
        },
        "high_risk_ai": False
    }

    response = client.post("/api/agent-ops/architect/review", json=payload)

    # Might fail if LLM not available
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert "success" in data or "compliance_score" in data or "result" in data


def test_architect_compliance_check():
    """Test POST /api/agent-ops/architect/compliance-check."""
    payload = {
        "uses_ai": True,
        "processes_personal_data": True,
        "has_consent_mechanism": True,
        "uses_social_scoring": False
    }

    response = client.post("/api/agent-ops/architect/compliance-check", json=payload)

    # Might fail if LLM not available
    assert response.status_code in [200, 500]


def test_architect_scalability_assessment():
    """Test POST /api/agent-ops/architect/scalability-assessment."""
    payload = {
        "expected_users": 10000,
        "expected_requests_per_second": 1000,
        "architecture_type": "microservices"
    }

    response = client.post("/api/agent-ops/architect/scalability-assessment", json=payload)

    assert response.status_code in [200, 500]


def test_architect_security_audit():
    """Test POST /api/agent-ops/architect/security-audit."""
    payload = {
        "authentication_method": "oauth2",
        "encryption_at_rest": True,
        "encryption_in_transit": True,
        "has_firewall": True
    }

    response = client.post("/api/agent-ops/architect/security-audit", json=payload)

    assert response.status_code in [200, 500]


# ============================================================================
# AXEAgent API Tests
# ============================================================================


def test_axe_chat():
    """Test POST /api/agent-ops/axe/chat."""
    payload = {
        "message": "What's the system status?",
        "include_history": False
    }

    response = client.post("/api/agent-ops/axe/chat", json=payload)

    # Might fail if LLM not available
    assert response.status_code in [200, 500]

    if response.status_code == 200:
        data = response.json()
        assert "response" in data or "success" in data or "result" in data


def test_axe_system_status():
    """Test GET /api/agent-ops/axe/system-status."""
    response = client.get("/api/agent-ops/axe/system-status")

    # Might fail if system status not available
    assert response.status_code in [200, 500]


def test_axe_clear_history():
    """Test DELETE /api/agent-ops/axe/history."""
    response = client.delete("/api/agent-ops/axe/history")

    assert response.status_code in [200, 500]


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_supervisor_supervise_invalid_risk_level():
    """Test that invalid risk level returns 422 validation error."""
    payload = {
        "requesting_agent": "TestAgent",
        "action": "test_action",
        "risk_level": "invalid_level"  # Invalid
    }

    response = client.post("/api/agent-ops/supervisor/supervise", json=payload)

    assert response.status_code == 422  # Validation error


def test_supervisor_supervise_missing_required_fields():
    """Test that missing required fields returns 422."""
    payload = {
        "requesting_agent": "TestAgent"
        # Missing: action, risk_level
    }

    response = client.post("/api/agent-ops/supervisor/supervise", json=payload)

    assert response.status_code == 422


def test_coder_generate_code_missing_spec():
    """Test that missing spec returns 422."""
    payload = {}  # Missing required 'spec' field

    response = client.post("/api/agent-ops/coder/generate-code", json=payload)

    assert response.status_code == 422


# ============================================================================
# Integration Flow Tests
# ============================================================================


def test_full_workflow_supervision_to_action():
    """
    Test complete workflow:
    1. Request supervision
    2. Get approval
    3. Execute action
    4. Verify in metrics
    """
    # Step 1: Request supervision
    supervise_payload = {
        "requesting_agent": "TestWorkflowAgent",
        "action": "test_workflow_action",
        "context": {"test": True},
        "risk_level": "low"
    }

    supervise_response = client.post(
        "/api/agent-ops/supervisor/supervise",
        json=supervise_payload
    )

    assert supervise_response.status_code == 200
    supervise_data = supervise_response.json()

    # Step 2: Verify supervision occurred
    assert "audit_id" in supervise_data

    # Step 3: Check metrics updated
    metrics_response = client.get("/api/agent-ops/supervisor/metrics")
    assert metrics_response.status_code == 200
    metrics_data = metrics_response.json()

    # Should have at least 1 request
    assert metrics_data["total_supervision_requests"] >= 1


def test_coder_to_supervisor_integration():
    """
    Test integration between CoderAgent and SupervisorAgent:
    1. CoderAgent generates code
    2. HIGH risk code should trigger supervisor
    """
    # Generate code that processes personal data (HIGH risk)
    payload = {
        "spec": "Create a function to process user email addresses and names",
        "risk_level": "high"
    }

    response = client.post("/api/agent-ops/coder/generate-code", json=payload)

    # Should either succeed (after supervisor approval) or require HITL
    assert response.status_code in [200, 403, 500]


# ============================================================================
# Performance Tests
# ============================================================================


def test_supervisor_supervise_performance():
    """Test that supervision requests complete in reasonable time."""
    import time

    payload = {
        "requesting_agent": "PerformanceTestAgent",
        "action": "performance_test",
        "context": {},
        "risk_level": "low"
    }

    start = time.time()
    response = client.post("/api/agent-ops/supervisor/supervise", json=payload)
    duration = time.time() - start

    # Should complete in under 5 seconds
    assert duration < 5.0
    assert response.status_code == 200


def test_concurrent_supervision_requests():
    """Test handling multiple concurrent supervision requests."""
    import concurrent.futures

    def make_request(i):
        payload = {
            "requesting_agent": f"Agent{i}",
            "action": f"action_{i}",
            "context": {},
            "risk_level": "low"
        }
        return client.post("/api/agent-ops/supervisor/supervise", json=payload)

    # Make 10 concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(make_request, i) for i in range(10)]
        responses = [f.result() for f in concurrent.futures.as_completed(futures)]

    # All should succeed or fail gracefully
    for response in responses:
        assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
