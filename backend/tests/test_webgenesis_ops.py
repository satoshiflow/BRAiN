"""
WebGenesis Operational Tests (Sprint II)

Tests for lifecycle management, health monitoring, and rollback features.

Coverage:
- Lifecycle operations (start/stop/restart/remove)
- Trust tier enforcement (LOCAL/DMZ allowed, EXTERNAL blocked)
- Release creation and pruning
- Rollback mechanisms
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
# Test: Lifecycle Operations with Trust Tier Enforcement
# ============================================================================


def test_lifecycle_start_requires_dmz_or_local():
    """Test that start endpoint blocks EXTERNAL trust tier."""
    # EXTERNAL request (no headers = EXTERNAL)
    response = client.post("/api/webgenesis/test-site/start")

    # Should block with 403
    assert response.status_code == 403
    data = response.json()
    assert "detail" in data
    assert "EXTERNAL" in str(data)


def test_lifecycle_stop_requires_dmz_or_local():
    """Test that stop endpoint blocks EXTERNAL trust tier."""
    response = client.post("/api/webgenesis/test-site/stop")

    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


def test_lifecycle_restart_requires_dmz_or_local():
    """Test that restart endpoint blocks EXTERNAL trust tier."""
    response = client.post("/api/webgenesis/test-site/restart")

    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


def test_lifecycle_remove_requires_dmz_or_local():
    """Test that remove endpoint blocks EXTERNAL trust tier."""
    response = client.delete("/api/webgenesis/test-site")

    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


def test_lifecycle_rollback_requires_dmz_or_local():
    """Test that rollback endpoint blocks EXTERNAL trust tier."""
    response = client.post("/api/webgenesis/test-site/rollback")

    assert response.status_code == 403
    data = response.json()
    assert "detail" in data


def test_lifecycle_start_with_dmz_headers():
    """Test that start allows DMZ trust tier."""
    headers = {
        "x-dmz-gateway-id": "test_gateway",
        "x-dmz-gateway-token": "test_token",
    }

    response = client.post("/api/webgenesis/test-site/start", headers=headers)

    # Should not be 403 (may be 404 if site doesn't exist, which is expected in tests)
    assert response.status_code != 403


def test_lifecycle_start_nonexistent_site():
    """Test that start returns 404 for non-existent site."""
    headers = {
        "x-dmz-gateway-id": "test_gateway",
        "x-dmz-gateway-token": "test_token",
    }

    response = client.post(
        "/api/webgenesis/nonexistent-site-12345/start", headers=headers
    )

    # Should return 404 (site not found)
    assert response.status_code == 404


def test_remove_with_keep_data_flag():
    """Test that remove endpoint accepts keep_data parameter."""
    headers = {
        "x-dmz-gateway-id": "test_gateway",
        "x-dmz-gateway-token": "test_token",
    }

    payload = {"keep_data": True}

    response = client.delete(
        "/api/webgenesis/test-site",
        headers=headers,
        json=payload,
    )

    # Should not be 403 (may be 404)
    assert response.status_code != 403


def test_rollback_accepts_release_id():
    """Test that rollback endpoint accepts optional release_id."""
    headers = {
        "x-dmz-gateway-id": "test_gateway",
        "x-dmz-gateway-token": "test_token",
    }

    payload = {
        "release_id": "rel_1735660800_a1b2c3d4",
        "current_release_id": "rel_1735664400_e5f6g7h8",
    }

    response = client.post(
        "/api/webgenesis/test-site/rollback",
        headers=headers,
        json=payload,
    )

    # Should not be 403
    assert response.status_code != 403


# ============================================================================
# Test: Releases Listing (ANY trust tier allowed)
# ============================================================================


def test_releases_list_allows_any_trust_tier():
    """Test that /releases endpoint allows ANY trust tier (including EXTERNAL)."""
    # EXTERNAL request (no headers)
    response = client.get("/api/webgenesis/test-site/releases")

    # Should NOT be 403 (may be 404 if site doesn't exist)
    assert response.status_code != 403


def test_releases_list_response_structure():
    """Test that /releases returns correct structure when site exists."""
    # This will return 404 for non-existent site
    response = client.get("/api/webgenesis/nonexistent-site-12345/releases")

    # Should be 404, not 403 or 500
    assert response.status_code == 404


# ============================================================================
# Test: Release ID Validation
# ============================================================================


def test_valid_release_id_format():
    """Test that valid release IDs are accepted."""
    from backend.app.modules.webgenesis.releases import validate_release_id

    valid_ids = [
        "rel_1735660800_a1b2c3d4",
        "rel_1234567890_abcdef12",
        "rel_9999999999_12345678",
    ]

    for release_id in valid_ids:
        assert validate_release_id(release_id), f"Should accept {release_id}"


def test_invalid_release_id_format():
    """Test that invalid release IDs are rejected."""
    from backend.app.modules.webgenesis.releases import validate_release_id

    invalid_ids = [
        "invalid",
        "rel_123_abc",  # Timestamp too short
        "rel_1735660800_short",  # Hash too long
        "rel_1735660800_ABCD1234",  # Uppercase not allowed
        "release_1735660800_a1b2c3d4",  # Wrong prefix
        "../rel_1735660800_a1b2c3d4",  # Path traversal attempt
    ]

    for release_id in invalid_ids:
        assert not validate_release_id(release_id), f"Should reject {release_id}"


# ============================================================================
# Test: Site ID Validation
# ============================================================================


def test_valid_site_id_format():
    """Test that valid site IDs are accepted."""
    from backend.app.modules.webgenesis.service import validate_site_id

    valid_ids = [
        "test-site",
        "my_site_123",
        "site-2025-01-01",
        "a",  # Single char
        "a" * 100,  # Long but valid
    ]

    for site_id in valid_ids:
        assert validate_site_id(site_id), f"Should accept {site_id}"


def test_invalid_site_id_format():
    """Test that invalid site IDs are rejected."""
    from backend.app.modules.webgenesis.service import validate_site_id

    invalid_ids = [
        "",  # Empty
        "../etc/passwd",  # Path traversal
        "site/../other",  # Path traversal
        "site/subdir",  # Directory separator
        "site\\windows",  # Windows separator
        "site with spaces",  # Spaces not allowed
        "site@email",  # Special chars
    ]

    for site_id in invalid_ids:
        assert not validate_site_id(site_id), f"Should reject {site_id}"


# ============================================================================
# Test: Lifecycle Status Enum
# ============================================================================


def test_lifecycle_status_enum_values():
    """Test that SiteLifecycleStatus enum has all required values."""
    from backend.app.modules.webgenesis.schemas import SiteLifecycleStatus

    required_statuses = [
        "running",
        "stopped",
        "exited",
        "restarting",
        "paused",
        "dead",
        "created",
        "unknown",
    ]

    for status in required_statuses:
        assert hasattr(
            SiteLifecycleStatus, status.upper()
        ), f"Missing status: {status}"


# ============================================================================
# Test: Health Status Enum
# ============================================================================


def test_health_status_enum_values():
    """Test that HealthStatus enum has all required values."""
    from backend.app.modules.webgenesis.schemas import HealthStatus

    required_statuses = [
        "healthy",
        "unhealthy",
        "starting",
        "unknown",
    ]

    for status in required_statuses:
        assert hasattr(HealthStatus, status.upper()), f"Missing status: {status}"


# ============================================================================
# Test: Release Metadata Model
# ============================================================================


def test_release_metadata_model():
    """Test ReleaseMetadata model validation."""
    from backend.app.modules.webgenesis.schemas import ReleaseMetadata

    # Valid metadata
    metadata = ReleaseMetadata(
        release_id="rel_1735660800_a1b2c3d4",
        site_id="test-site",
        artifact_hash="a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
        created_at="2025-01-01T12:00:00Z",
    )

    assert metadata.release_id == "rel_1735660800_a1b2c3d4"
    assert metadata.site_id == "test-site"


# ============================================================================
# Test: Rollback Request/Response Models
# ============================================================================


def test_rollback_request_optional_fields():
    """Test that RollbackRequest has optional fields."""
    from backend.app.modules.webgenesis.schemas import RollbackRequest

    # All fields optional
    request1 = RollbackRequest()
    assert request1.release_id is None
    assert request1.current_release_id is None

    # With release_id only
    request2 = RollbackRequest(release_id="rel_1735660800_a1b2c3d4")
    assert request2.release_id == "rel_1735660800_a1b2c3d4"
    assert request2.current_release_id is None


def test_rollback_response_model():
    """Test RollbackResponse model structure."""
    from backend.app.modules.webgenesis.schemas import (
        RollbackResponse,
        SiteLifecycleStatus,
        HealthStatus,
    )

    response = RollbackResponse(
        success=True,
        site_id="test-site",
        from_release="rel_1735664400_e5f6g7h8",
        to_release="rel_1735660800_a1b2c3d4",
        lifecycle_status=SiteLifecycleStatus.RUNNING,
        health_status=HealthStatus.HEALTHY,
        message="Rollback completed",
    )

    assert response.success is True
    assert response.from_release == "rel_1735664400_e5f6g7h8"
    assert response.to_release == "rel_1735660800_a1b2c3d4"


# ============================================================================
# Test: RemoveRequest/Response Models
# ============================================================================


def test_remove_request_default_values():
    """Test RemoveRequest default values."""
    from backend.app.modules.webgenesis.schemas import RemoveRequest

    # Default should be keep_data=True (safer default)
    request = RemoveRequest()
    assert request.keep_data is True


def test_remove_response_model():
    """Test RemoveResponse model structure."""
    from backend.app.modules.webgenesis.schemas import RemoveResponse

    response = RemoveResponse(
        success=True,
        site_id="test-site",
        message="Site removed",
        data_removed=False,
    )

    assert response.success is True
    assert response.data_removed is False


# ============================================================================
# Test: Integration - Full Lifecycle Workflow
# ============================================================================


def test_lifecycle_operations_return_correct_response_model():
    """Test that lifecycle operations return correct response structure."""
    headers = {
        "x-dmz-gateway-id": "test_gateway",
        "x-dmz-gateway-token": "test_token",
    }

    # Test start response structure (for non-existent site)
    response = client.post(
        "/api/webgenesis/test-site-lifecycle/start", headers=headers
    )

    # Should be 404, but check response structure
    if response.status_code == 404:
        data = response.json()
        assert "detail" in data
    elif response.status_code == 200:
        # If it somehow succeeded, check model structure
        data = response.json()
        assert "success" in data
        assert "site_id" in data
        assert "operation" in data
        assert "lifecycle_status" in data


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
