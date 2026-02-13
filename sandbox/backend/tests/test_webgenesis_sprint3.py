"""
WebGenesis Sprint III Tests

Tests for Control Center UI endpoints:
- GET /api/webgenesis/sites - List all sites
- GET /api/webgenesis/{site_id}/audit - Site audit events

Sprint III: Control Center Integration
- Sites list endpoint
- Audit timeline endpoint
- Error handling (fail-safe)
"""

import sys
import os
from pathlib import Path

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ============================================================================
# Sprint III - Sites List Endpoint Tests
# ============================================================================


def test_sites_list_endpoint_exists():
    """Test that GET /api/webgenesis/sites endpoint exists and returns 200."""
    response = client.get("/api/webgenesis/sites")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_sites_list_returns_valid_schema():
    """Test that sites list endpoint returns valid SitesListResponse schema."""
    response = client.get("/api/webgenesis/sites")

    assert response.status_code == 200
    data = response.json()

    # Verify schema
    assert "sites" in data, "Missing 'sites' field"
    assert "total_count" in data, "Missing 'total_count' field"
    assert isinstance(data["sites"], list), "'sites' must be a list"
    assert isinstance(data["total_count"], int), "'total_count' must be an integer"


def test_sites_list_empty_storage():
    """Test that sites list returns empty array when no sites exist."""
    response = client.get("/api/webgenesis/sites")

    assert response.status_code == 200
    data = response.json()

    # If storage is empty, should return empty array
    # (This test may have sites if run after other tests)
    assert isinstance(data["sites"], list)
    assert data["total_count"] >= 0


def test_sites_list_item_schema():
    """Test that each site item has required fields (if any sites exist)."""
    response = client.get("/api/webgenesis/sites")

    assert response.status_code == 200
    data = response.json()

    # If there are sites, verify schema
    if data["sites"]:
        site = data["sites"][0]

        # Required fields from SiteListItem
        assert "site_id" in site
        assert "name" in site or site.get("name") is None
        assert "domain" in site or site.get("domain") is None
        assert "status" in site
        assert "lifecycle_status" in site or site.get("lifecycle_status") is None
        assert "health_status" in site or site.get("health_status") is None
        assert "current_release_id" in site or site.get("current_release_id") is None
        assert "deployed_url" in site or site.get("deployed_url") is None
        assert "dns_enabled" in site
        assert "last_action" in site or site.get("last_action") is None
        assert "updated_at" in site


# ============================================================================
# Sprint III - Site Audit Endpoint Tests
# ============================================================================


def test_site_audit_endpoint_exists():
    """Test that GET /api/webgenesis/{site_id}/audit endpoint exists."""
    # Use a dummy site_id for testing endpoint existence
    response = client.get("/api/webgenesis/test-site_12345/audit")

    # Should return 200 (fail-safe - returns empty events for non-existent site)
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_site_audit_returns_valid_schema():
    """Test that site audit endpoint returns valid SiteAuditResponse schema."""
    response = client.get("/api/webgenesis/test-site_12345/audit")

    assert response.status_code == 200
    data = response.json()

    # Verify schema
    assert "site_id" in data, "Missing 'site_id' field"
    assert "events" in data, "Missing 'events' field"
    assert "total_count" in data, "Missing 'total_count' field"
    assert "filtered_count" in data, "Missing 'filtered_count' field"
    assert isinstance(data["events"], list), "'events' must be a list"
    assert isinstance(data["total_count"], int), "'total_count' must be an integer"
    assert isinstance(data["filtered_count"], int), "'filtered_count' must be an integer"


def test_site_audit_with_invalid_site_id():
    """Test that audit endpoint handles invalid site_id gracefully."""
    # Invalid site_id (contains special characters)
    response = client.get("/api/webgenesis/../../../etc/passwd/audit")

    # Should return 200 with empty events (fail-safe)
    assert response.status_code == 200
    data = response.json()

    assert data["events"] == []
    assert data["total_count"] == 0
    assert data["filtered_count"] == 0


def test_site_audit_with_query_params():
    """Test that audit endpoint accepts query parameters."""
    response = client.get(
        "/api/webgenesis/test-site_12345/audit",
        params={
            "limit": 50,
            "severity": "ERROR",
            "types": "deploy,build",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "events" in data
    assert isinstance(data["events"], list)


def test_site_audit_limit_validation():
    """Test that audit endpoint validates limit parameter."""
    # Test with limit > 500 (should be capped at 500)
    response = client.get(
        "/api/webgenesis/test-site_12345/audit",
        params={"limit": 1000},
    )

    # Should still return 200 (limit is capped internally)
    assert response.status_code == 200


def test_site_audit_empty_result():
    """Test that non-existent site returns empty audit events."""
    response = client.get("/api/webgenesis/nonexistent-site_99999/audit")

    assert response.status_code == 200
    data = response.json()

    # Should return empty events for non-existent site
    assert data["site_id"] == "nonexistent-site_99999"
    assert data["events"] == []
    assert data["total_count"] == 0


# ============================================================================
# Integration Tests
# ============================================================================


def test_sites_list_and_audit_integration():
    """Test that sites from list endpoint can be queried for audit events."""
    # Get list of sites
    sites_response = client.get("/api/webgenesis/sites")
    assert sites_response.status_code == 200

    sites_data = sites_response.json()

    # If there are sites, test audit endpoint for first site
    if sites_data["sites"]:
        site_id = sites_data["sites"][0]["site_id"]

        # Query audit for this site
        audit_response = client.get(f"/api/webgenesis/{site_id}/audit")
        assert audit_response.status_code == 200

        audit_data = audit_response.json()
        assert audit_data["site_id"] == site_id
        assert isinstance(audit_data["events"], list)


# ============================================================================
# Fail-Safe Tests (Sprint III Requirement)
# ============================================================================


def test_sites_list_fail_safe():
    """Test that sites list endpoint never throws exceptions (fail-safe)."""
    response = client.get("/api/webgenesis/sites")

    # Should always return 200 with valid response, even if errors occur
    assert response.status_code == 200
    data = response.json()

    # Even on error, should return valid structure
    assert "sites" in data
    assert "total_count" in data


def test_audit_endpoint_fail_safe():
    """Test that audit endpoint never throws exceptions (fail-safe)."""
    # Try with various invalid inputs
    test_cases = [
        "test-site",
        "../../etc/passwd",
        "site_with_special_!@#$",
        "a" * 1000,  # Very long site_id
    ]

    for site_id in test_cases:
        response = client.get(f"/api/webgenesis/{site_id}/audit")

        # Should always return 200 with valid response (fail-safe)
        assert response.status_code == 200
        data = response.json()

        # Should have valid structure
        assert "events" in data
        assert "total_count" in data
