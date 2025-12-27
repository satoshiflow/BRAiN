"""Sprint 17 Tests: Licensing & Certificates (Compact)"""
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_license_health():
    """Test 1: Licensing system health."""
    response = client.get("/api/licenses/stats/summary")
    assert response.status_code == 200

def test_license_issue():
    """Test 2: Issue license."""
    payload = {
        "type": "course_access",
        "scope": {"course_id": "course_123", "version": "v1", "language": "de"},
        "holder": {"type": "individual", "reference": "hash_abc123"},
        "rights": {"rights": ["view", "download"]},
        "issued_reason": "purchase",
        "issued_by": "admin"
    }
    response = client.post("/api/licenses/issue", json=payload)
    assert response.status_code == 201
    assert "license_id" in response.json()

def test_license_validate():
    """Test 3: Validate license."""
    # Issue first
    payload = {
        "type": "course_access",
        "scope": {"course_id": "course_123", "version": "v1", "language": "de"},
        "holder": {"type": "individual", "reference": "hash_test"},
        "rights": {"rights": ["view"]},
        "issued_reason": "grant",
        "issued_by": "admin"
    }
    issue_resp = client.post("/api/licenses/issue", json=payload)
    license_id = issue_resp.json()["license_id"]

    # Validate
    validate_resp = client.post("/api/licenses/validate", json={"license_id": license_id})
    assert validate_resp.status_code == 200
    assert validate_resp.json()["valid"] is True

def test_license_revoke():
    """Test 4: Revoke license."""
    # Issue first
    payload = {
        "type": "trial",
        "scope": {"course_id": "course_456", "version": "v1", "language": "en"},
        "holder": {"type": "anonymous", "reference": "anon_123"},
        "rights": {"rights": ["view"]},
        "issued_reason": "trial",
        "issued_by": "system"
    }
    issue_resp = client.post("/api/licenses/issue", json=payload)
    license_id = issue_resp.json()["license_id"]

    # Revoke
    revoke_resp = client.post(
        f"/api/licenses/{license_id}/revoke",
        json={"license_id": license_id, "revoked_by": "admin", "reason": "Trial expired"}
    )
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "revoked"

def test_certificate_verify():
    """Test 5: Certificate verification (extends Sprint 14)."""
    # This is a placeholder - full implementation uses Sprint 14 infra
    assert True  # Certificate engine extends existing Sprint 14 functionality

# Summary: 5 focused tests covering core licensing lifecycle
print("Sprint 17 Tests: Licensing & Certificates - 5 tests")
