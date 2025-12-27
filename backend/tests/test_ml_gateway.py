"""
Test ML Gateway & Risk Scoring Integration

Tests for:
- ML Gateway service (fail-closed architecture)
- Risk Scoring sidecar
- Policy Engine integration with ML enrichment
"""

import sys
import os

# Add backend to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ============================================================================
# ML Gateway Health & Info Tests
# ============================================================================


def test_ml_gateway_health():
    """Test ML Gateway health endpoint"""
    response = client.get("/api/ml/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "provider_available" in data
    assert "model_version" in data
    assert data["model_version"] == "baseline-v1"


def test_ml_gateway_info():
    """Test ML Gateway info endpoint"""
    response = client.get("/api/ml/info")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "ML Gateway"
    assert "version" in data
    assert "enabled" in data
    assert "config" in data


# ============================================================================
# Risk Scoring Tests
# ============================================================================


def test_risk_score_simple_context():
    """Test risk scoring with simple context"""
    payload = {
        "context": {
            "action": "test_action",
            "priority": "NORMAL",
            "payload": {"key": "value"},
        }
    }

    response = client.post("/api/ml/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "risk_score" in data
    assert "confidence" in data
    assert "model_version" in data
    assert 0.0 <= data["risk_score"] <= 1.0
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["model_version"] == "baseline-v1"


def test_risk_score_high_complexity():
    """Test risk scoring detects high complexity"""
    # Create context with many nodes (should trigger anomaly)
    payload = {
        "context": {
            "action": "complex_operation",
            "priority": "CRITICAL",
            "dag": {
                "nodes": [f"node_{i}" for i in range(150)],  # Exceeds threshold
                "edges": [f"edge_{i}" for i in range(250)],  # Exceeds threshold
            },
            "payload": {
                "deeply": {
                    "nested": {
                        "structure": {
                            "with": {
                                "many": {
                                    "levels": {"data": "value"}
                                }
                            }
                        }
                    }
                }
            },
        }
    }

    response = client.post("/api/ml/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    # Should have elevated risk due to anomalies
    assert data["risk_score"] > 0.3, "High complexity should result in higher risk"
    assert len(data["top_factors"]) > 0, "Should return risk factors"


def test_risk_score_low_complexity():
    """Test risk scoring for low complexity (should be low risk)"""
    payload = {
        "context": {
            "action": "simple_operation",
            "priority": "LOW",
            "payload": {"simple": "data"},
        }
    }

    response = client.post("/api/ml/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    # Should have low risk for simple context
    assert (
        data["risk_score"] < 0.5
    ), "Simple context should result in lower risk"


# ============================================================================
# Context Enrichment Tests
# ============================================================================


def test_enrich_context():
    """Test context enrichment endpoint"""
    context = {
        "agent_id": "test_agent",
        "action": "test_action",
        "priority": "NORMAL",
    }

    response = client.post(
        "/api/ml/enrich",
        json=context,
        params={
            "mission_id": "mission_123",
            "agent_id": "agent_001",
            "action": "test_action",
        },
    )
    assert response.status_code == 200

    data = response.json()
    assert "original_context" in data
    assert "ml_risk_score" in data
    assert "ml_confidence" in data
    assert "ml_model_version" in data
    assert "ml_top_factors" in data
    assert "ml_is_fallback" in data


# ============================================================================
# Policy Integration Tests
# ============================================================================


def test_policy_with_ml_risk_score_low():
    """Test policy evaluation with ML enrichment (low risk)"""
    # Note: This test requires Policy Engine to be running
    # and ML Gateway to be enabled

    context = {
        "agent_id": "test_agent",
        "agent_role": "operator",
        "action": "simple_operation",
        "params": {"simple": "data"},
    }

    response = client.post("/api/policy/evaluate", json=context)
    assert response.status_code == 200

    # The response should include policy decision
    # ML enrichment happens automatically if enabled
    data = response.json()
    assert "allowed" in data
    assert "effect" in data


def test_policy_with_ml_risk_score_high():
    """Test policy evaluation with ML enrichment (high risk)"""
    context = {
        "agent_id": "test_agent",
        "agent_role": "operator",
        "action": "risky_operation",
        "params": {
            "dag": {
                "nodes": [f"node_{i}" for i in range(200)],
                "edges": [f"edge_{i}" for i in range(300)],
            }
        },
    }

    response = client.post("/api/policy/evaluate", json=context)
    assert response.status_code == 200

    data = response.json()
    assert "allowed" in data
    # High risk might trigger different policy decisions


# ============================================================================
# Failover Tests
# ============================================================================


def test_ml_gateway_graceful_degradation():
    """Test that ML Gateway returns fallback score when sidecar unavailable"""
    # The service is designed to return fallback scores when ML is unavailable
    # This test verifies that behavior

    payload = {"context": {"action": "test"}}

    response = client.post("/api/ml/score", json=payload)
    assert response.status_code == 200

    data = response.json()
    # Should return valid response even if ML unavailable
    assert "risk_score" in data
    assert "is_fallback" in data

    # If is_fallback is True, confidence should be 0.0
    if data["is_fallback"]:
        assert data["confidence"] == 0.0


# ============================================================================
# Integration Test
# ============================================================================


def test_end_to_end_ml_pipeline():
    """Test complete ML pipeline: score → enrich → policy evaluate"""

    # Step 1: Get risk score
    score_payload = {
        "context": {
            "action": "deploy_application",
            "priority": "HIGH",
            "environment": "production",
        }
    }

    score_response = client.post("/api/ml/score", json=score_payload)
    assert score_response.status_code == 200
    score_data = score_response.json()

    # Step 2: Enrich context
    enrich_response = client.post(
        "/api/ml/enrich",
        json=score_payload["context"],
        params={"action": "deploy_application"},
    )
    assert enrich_response.status_code == 200
    enriched_data = enrich_response.json()

    # Verify enrichment contains ML scores
    assert enriched_data["ml_risk_score"] == score_data["risk_score"]
    assert enriched_data["ml_confidence"] == score_data["confidence"]

    # Step 3: Policy evaluation (automatically enriched)
    policy_context = {
        "agent_id": "deploy_agent",
        "agent_role": "operator",
        "action": "deploy_application",
        "params": score_payload["context"],
    }

    policy_response = client.post("/api/policy/evaluate", json=policy_context)
    assert policy_response.status_code == 200

    # Verify policy made a decision
    policy_data = policy_response.json()
    assert "allowed" in policy_data
    assert "effect" in policy_data
    assert "reason" in policy_data
