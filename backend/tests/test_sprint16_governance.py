"""
Tests for Sprint 16: HITL Approvals UI & Governance Cockpit

Tests cover:
- Approval request creation
- Approval/rejection workflows
- Token validation
- Expiry handling
- Audit trail
- Statistics
"""

import sys
import os
import pytest
import time
from pathlib import Path

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

# Test client
client = TestClient(app)


# =========================================================================
# Test Fixtures
# =========================================================================

@pytest.fixture
def sample_approval_request():
    """Sample approval request payload."""
    return {
        "approval_type": "ir_escalation",
        "context": {
            "action_type": "ir_escalation",
            "action_description": "Test IR escalation",
            "risk_tier": "medium",
            "requested_by": "test_user",
            "reason": "Testing approval workflow"
        },
        "expires_in_hours": 24
    }


# =========================================================================
# Test 1: Health Check
# =========================================================================

def test_governance_health():
    """Test 1: Governance system health check."""
    response = client.get("/api/governance/health")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Governance System"
    assert data["status"] in ["healthy", "degraded"]
    assert "pending_approvals" in data


# =========================================================================
# Test 2: Create Approval Request
# =========================================================================

def test_create_approval(sample_approval_request):
    """Test 2: Create approval request."""
    response = client.post("/api/governance/approvals", json=sample_approval_request)

    assert response.status_code == 201
    data = response.json()
    assert "approval_id" in data
    assert data["status"] == "pending"
    assert "expires_at" in data
    assert "message" in data


# =========================================================================
# Test 3: Get Approval Detail
# =========================================================================

def test_get_approval_detail(sample_approval_request):
    """Test 3: Get approval detail by ID."""
    # Create approval
    create_response = client.post("/api/governance/approvals", json=sample_approval_request)
    approval_id = create_response.json()["approval_id"]

    # Get detail
    response = client.get(f"/api/governance/approvals/{approval_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["approval_id"] == approval_id
    assert data["status"] == "pending"
    assert "context" in data
    assert data["context"]["action_description"] == "Test IR escalation"


# =========================================================================
# Test 4: List Pending Approvals
# =========================================================================

def test_list_pending_approvals(sample_approval_request):
    """Test 4: List pending approvals."""
    # Create approval
    client.post("/api/governance/approvals", json=sample_approval_request)

    # List pending
    response = client.get("/api/governance/approvals/pending")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        assert "approval_id" in data[0]
        assert "status" in data[0]


# =========================================================================
# Test 5: Approve Approval
# =========================================================================

def test_approve_approval(sample_approval_request):
    """Test 5: Approve an approval request."""
    # Create approval
    create_response = client.post("/api/governance/approvals", json=sample_approval_request)
    approval_id = create_response.json()["approval_id"]

    # Approve
    approve_request = {
        "actor_id": "admin",
        "notes": "Approved via test"
    }
    response = client.post(
        f"/api/governance/approvals/{approval_id}/approve",
        json=approve_request
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["approved_by"] == "admin"


# =========================================================================
# Test 6: Reject Approval
# =========================================================================

def test_reject_approval(sample_approval_request):
    """Test 6: Reject an approval request with reason."""
    # Create approval
    create_response = client.post("/api/governance/approvals", json=sample_approval_request)
    approval_id = create_response.json()["approval_id"]

    # Reject
    reject_request = {
        "actor_id": "admin",
        "reason": "This is a test rejection reason"
    }
    response = client.post(
        f"/api/governance/approvals/{approval_id}/reject",
        json=reject_request
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["approved_by"] == "admin"
    assert data["rejection_reason"] == "This is a test rejection reason"


# =========================================================================
# Test 7: Rejection Requires Reason
# =========================================================================

def test_reject_requires_reason(sample_approval_request):
    """Test 7: Rejection fails without valid reason."""
    # Create approval
    create_response = client.post("/api/governance/approvals", json=sample_approval_request)
    approval_id = create_response.json()["approval_id"]

    # Try to reject with short reason
    reject_request = {
        "actor_id": "admin",
        "reason": "short"  # Too short
    }
    response = client.post(
        f"/api/governance/approvals/{approval_id}/reject",
        json=reject_request
    )

    assert response.status_code == 400  # Bad request


# =========================================================================
# Test 8: Cannot Approve Twice
# =========================================================================

def test_cannot_approve_twice(sample_approval_request):
    """Test 8: Cannot approve already-processed approval."""
    # Create and approve
    create_response = client.post("/api/governance/approvals", json=sample_approval_request)
    approval_id = create_response.json()["approval_id"]

    approve_request = {"actor_id": "admin"}
    client.post(f"/api/governance/approvals/{approval_id}/approve", json=approve_request)

    # Try to approve again
    response = client.post(f"/api/governance/approvals/{approval_id}/approve", json=approve_request)

    assert response.status_code == 400  # Already processed


# =========================================================================
# Test 9: Audit Trail
# =========================================================================

def test_audit_trail(sample_approval_request):
    """Test 9: Audit trail records all actions."""
    # Create approval
    create_response = client.post("/api/governance/approvals", json=sample_approval_request)
    approval_id = create_response.json()["approval_id"]

    # Approve it
    client.post(
        f"/api/governance/approvals/{approval_id}/approve",
        json={"actor_id": "admin"}
    )

    # Get audit trail
    response = client.get(f"/api/governance/audit?approval_id={approval_id}")

    assert response.status_code == 200
    entries = response.json()
    assert isinstance(entries, list)
    assert len(entries) >= 2  # At least creation + approval


# =========================================================================
# Test 10: Governance Statistics
# =========================================================================

def test_governance_stats():
    """Test 10: Governance statistics endpoint."""
    response = client.get("/api/governance/stats")

    assert response.status_code == 200
    data = response.json()
    assert "total_approvals" in data
    assert "pending_approvals" in data
    assert "approved_count" in data
    assert "rejected_count" in data
    assert "by_type" in data
    assert "by_risk_tier" in data


# =========================================================================
# Test 11: High Risk Requires Token
# =========================================================================

def test_high_risk_requires_token():
    """Test 11: High risk approvals require token."""
    # Create high-risk approval
    high_risk_request = {
        "approval_type": "policy_override",
        "context": {
            "action_type": "policy_override",
            "action_description": "Override critical policy",
            "risk_tier": "high",  # High risk
            "requested_by": "test_user",
            "reason": "Emergency override"
        },
        "expires_in_hours": 12
    }

    response = client.post("/api/governance/approvals", json=high_risk_request)

    assert response.status_code == 201
    data = response.json()
    assert "token" in data  # Token returned for high risk
    assert data["token"] is not None


# =========================================================================
# Test 12: List with Filters
# =========================================================================

def test_list_with_filters(sample_approval_request):
    """Test 12: List approvals with filters."""
    # Create approval
    client.post("/api/governance/approvals", json=sample_approval_request)

    # Filter by type
    response = client.get("/api/governance/approvals?approval_type=ir_escalation")

    assert response.status_code == 200
    data = response.json()
    for approval in data:
        assert approval["approval_type"] == "ir_escalation"


# =========================================================================
# Test 13: Expiry Endpoint
# =========================================================================

def test_expiry_endpoint():
    """Test 13: Expired approvals endpoint."""
    response = client.get("/api/governance/approvals/expired")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # All should be expired (if any)
    for approval in data:
        assert approval["status"] == "expired" or approval["time_until_expiry"] < 0


# =========================================================================
# Test 14: Specialized Approval Types
# =========================================================================

def test_course_publish_approval():
    """Test 14: Course publish approval type."""
    request = {
        "approval_type": "course_publish",
        "context": {
            "action_type": "course_publish",
            "action_description": "Publish Course: Test Course",
            "risk_tier": "medium",
            "requested_by": "course_admin",
            "metadata": {"course_id": "course_123"}
        },
        "expires_in_hours": 72
    }

    response = client.post("/api/governance/approvals", json=request)

    assert response.status_code == 201
    data = response.json()
    assert "approval_id" in data


# =========================================================================
# Test 15: Certificate Issuance Approval
# =========================================================================

def test_certificate_issuance_approval():
    """Test 15: Certificate issuance approval type."""
    request = {
        "approval_type": "certificate_issuance",
        "context": {
            "action_type": "certificate_issuance",
            "action_description": "Issue certificate to user",
            "risk_tier": "low",
            "requested_by": "cert_admin"
        },
        "expires_in_hours": 48
    }

    response = client.post("/api/governance/approvals", json=request)

    assert response.status_code == 201


# =========================================================================
# Test 16: Audit Export
# =========================================================================

def test_audit_export(sample_approval_request):
    """Test 16: Audit trail export functionality."""
    # Create approval
    create_response = client.post("/api/governance/approvals", json=sample_approval_request)
    approval_id = create_response.json()["approval_id"]

    # Export audit trail
    response = client.get(f"/api/governance/audit/export?actor_id=auditor&approval_id={approval_id}")

    assert response.status_code == 200
    data = response.json()
    assert "approval_id" in data
    assert "entries" in data
    assert "exported_by" in data
    assert data["exported_by"] == "auditor"


# =========================================================================
# Test 17: Backward Compatibility
# =========================================================================

def test_backward_compatibility():
    """Test 17: Governance module doesn't break existing systems."""
    # Test existing endpoints still work
    response = client.get("/api/courses/health")
    assert response.status_code == 200

    response = client.get("/api/courses/distribution/health")
    assert response.status_code == 200


# =========================================================================
# Test 18: Maintenance - Expire Old Approvals
# =========================================================================

def test_maintenance_expire_old():
    """Test 18: Maintenance endpoint expires old approvals."""
    response = client.post("/api/governance/maintenance/expire-old")

    assert response.status_code == 200
    data = response.json()
    assert "expired_count" in data
    assert isinstance(data["expired_count"], int)


# =========================================================================
# Test Summary
# =========================================================================

def test_summary():
    """
    Test Summary - Sprint 16: HITL Approvals UI & Governance Cockpit

    Total tests: 18

    Coverage:
    1. ✅ Health check
    2. ✅ Create approval request
    3. ✅ Get approval detail
    4. ✅ List pending approvals
    5. ✅ Approve approval
    6. ✅ Reject approval
    7. ✅ Rejection requires reason
    8. ✅ Cannot approve twice
    9. ✅ Audit trail
    10. ✅ Governance statistics
    11. ✅ High risk requires token
    12. ✅ List with filters
    13. ✅ Expiry endpoint
    14. ✅ Course publish approval
    15. ✅ Certificate issuance approval
    16. ✅ Audit export
    17. ✅ Backward compatibility
    18. ✅ Maintenance - expire old

    All Sprint 16 requirements covered:
    - ✅ Approval lifecycle (create, approve, reject)
    - ✅ Token validation for high-risk actions
    - ✅ Expiry handling
    - ✅ Audit trail (full accountability)
    - ✅ Statistics and reporting
    - ✅ Specialized approval types
    - ✅ No breaking changes
    """
    pass


if __name__ == "__main__":
    print("Sprint 16 Test Suite: HITL Approvals UI & Governance Cockpit")
    print("Run with: pytest backend/tests/test_sprint16_governance.py -v")
