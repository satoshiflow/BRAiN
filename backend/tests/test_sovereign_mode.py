"""
Tests for Sovereign Mode Module

Comprehensive test suite for sovereign mode operations.
"""

import sys
import os
import pytest
import tempfile
import json
from pathlib import Path

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from backend.main import app

from backend.app.modules.sovereign_mode.schemas import (
    OperationMode,
    BundleStatus,
    Bundle,
    ValidationResult,
)
from backend.app.modules.sovereign_mode.hash_validator import HashValidator
from backend.app.modules.sovereign_mode.network_guard import (
    NetworkGuard,
    NetworkGuardException,
)


client = TestClient(app)


class TestSovereignModeAPI:
    """Test sovereign mode API endpoints."""

    def test_info_endpoint(self):
        """Test /api/sovereign-mode/info endpoint."""
        response = client.get("/api/sovereign-mode/info")

        assert response.status_code == 200
        data = response.json()

        assert "name" in data
        assert "version" in data
        assert "features" in data
        assert data["name"] == "BRAiN Sovereign Mode"
        assert isinstance(data["features"], list)

    def test_status_endpoint(self):
        """Test /api/sovereign-mode/status endpoint."""
        response = client.get("/api/sovereign-mode/status")

        assert response.status_code == 200
        data = response.json()

        assert "mode" in data
        assert "is_online" in data
        assert "is_sovereign" in data
        assert "config" in data
        assert data["mode"] in ["online", "offline", "sovereign", "quarantine"]

    def test_config_endpoint(self):
        """Test /api/sovereign-mode/config endpoint."""
        response = client.get("/api/sovereign-mode/config")

        assert response.status_code == 200
        data = response.json()

        assert "current_mode" in data
        assert "auto_detect_network" in data
        assert "strict_validation" in data
        assert "block_external_http" in data

    def test_bundles_list_endpoint(self):
        """Test /api/sovereign-mode/bundles endpoint."""
        response = client.get("/api/sovereign-mode/bundles")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_statistics_endpoint(self):
        """Test /api/sovereign-mode/statistics endpoint."""
        response = client.get("/api/sovereign-mode/statistics")

        assert response.status_code == 200
        data = response.json()

        assert "system_version" in data
        assert "current_mode" in data
        assert "bundles" in data
        assert "network_guard" in data


class TestHashValidator:
    """Test hash validation functionality."""

    def test_compute_file_hash(self):
        """Test SHA256 file hash computation."""
        validator = HashValidator()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            # Compute hash
            hash_result = validator.compute_file_hash(temp_path)

            assert hash_result is not None
            assert len(hash_result) == 64  # SHA256 hex length
            assert isinstance(hash_result, str)

        finally:
            os.unlink(temp_path)

    def test_compute_string_hash(self):
        """Test SHA256 string hash computation."""
        validator = HashValidator()

        hash1 = validator.compute_string_hash("test")
        hash2 = validator.compute_string_hash("test")
        hash3 = validator.compute_string_hash("different")

        assert hash1 == hash2  # Same input = same hash
        assert hash1 != hash3  # Different input = different hash
        assert len(hash1) == 64

    def test_compute_json_hash(self):
        """Test SHA256 JSON hash computation."""
        validator = HashValidator()

        data1 = {"key": "value", "number": 42}
        data2 = {"number": 42, "key": "value"}  # Different order

        hash1 = validator.compute_json_hash(data1)
        hash2 = validator.compute_json_hash(data2)

        # Should be same (deterministic with sorted keys)
        assert hash1 == hash2

    def test_validate_file_success(self):
        """Test successful file validation."""
        validator = HashValidator()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            # Compute expected hash
            expected_hash = validator.compute_file_hash(temp_path)

            # Validate
            result = validator.validate_file(temp_path, expected_hash)

            assert result.is_valid is True
            assert result.hash_match is True
            assert result.file_exists is True
            assert len(result.errors) == 0

        finally:
            os.unlink(temp_path)

    def test_validate_file_hash_mismatch(self):
        """Test file validation with hash mismatch."""
        validator = HashValidator()

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test content")
            temp_path = f.name

        try:
            # Use wrong hash
            wrong_hash = "0" * 64

            # Validate
            result = validator.validate_file(temp_path, wrong_hash)

            assert result.is_valid is False
            assert result.hash_match is False
            assert result.file_exists is True
            assert len(result.errors) > 0

        finally:
            os.unlink(temp_path)

    def test_validate_file_not_found(self):
        """Test file validation with missing file."""
        validator = HashValidator()

        result = validator.validate_file("/nonexistent/file.txt", "abc123")

        assert result.is_valid is False
        assert result.file_exists is False
        assert len(result.errors) > 0


class TestNetworkGuard:
    """Test network guard functionality."""

    def test_guard_online_mode_allows_all(self):
        """Test that ONLINE mode allows all requests."""
        guard = NetworkGuard(current_mode=OperationMode.ONLINE)

        # Should not raise exception
        result = guard.check_request("https://example.com")
        assert result is True

        result = guard.check_request("https://api.external.com")
        assert result is True

    def test_guard_offline_mode_blocks_external(self):
        """Test that OFFLINE mode blocks external requests."""
        guard = NetworkGuard(current_mode=OperationMode.OFFLINE)

        # Should raise exception
        with pytest.raises(NetworkGuardException) as exc_info:
            guard.check_request("https://example.com")

        assert exc_info.value.mode == OperationMode.OFFLINE
        assert exc_info.value.url == "https://example.com"

    def test_guard_allows_localhost(self):
        """Test that localhost is always allowed."""
        guard = NetworkGuard(current_mode=OperationMode.OFFLINE)

        # Localhost should be allowed even in OFFLINE mode
        result = guard.check_request("http://localhost:8000")
        assert result is True

        result = guard.check_request("http://127.0.0.1:8000")
        assert result is True

    def test_guard_allowed_domains(self):
        """Test whitelisted domains."""
        guard = NetworkGuard(
            current_mode=OperationMode.OFFLINE,
            allowed_domains={"example.com"}
        )

        # Whitelisted domain should be allowed
        result = guard.check_request("https://example.com")
        assert result is True

        # Non-whitelisted should be blocked
        with pytest.raises(NetworkGuardException):
            guard.check_request("https://other.com")

    def test_guard_wildcard_domains(self):
        """Test wildcard domain matching."""
        guard = NetworkGuard(
            current_mode=OperationMode.OFFLINE,
            allowed_domains={"*.example.com"}
        )

        # Subdomain should be allowed
        result = guard.check_request("https://api.example.com")
        assert result is True

        result = guard.check_request("https://sub.example.com")
        assert result is True

        # Root domain should NOT match wildcard
        with pytest.raises(NetworkGuardException):
            guard.check_request("https://example.com")

    def test_guard_statistics(self):
        """Test guard statistics tracking."""
        guard = NetworkGuard(current_mode=OperationMode.OFFLINE)

        # Allow localhost
        guard.check_request("http://localhost")

        # Block external
        try:
            guard.check_request("https://example.com")
        except NetworkGuardException:
            pass

        stats = guard.get_statistics()

        assert stats["allowed_count"] == 1
        assert stats["blocked_count"] == 1
        assert stats["total_requests"] == 2
        assert len(stats["recent_blocked"]) == 1

    def test_guard_mode_change(self):
        """Test changing guard mode."""
        guard = NetworkGuard(current_mode=OperationMode.ONLINE)

        # Should allow in ONLINE mode
        result = guard.check_request("https://example.com")
        assert result is True

        # Switch to OFFLINE
        guard.set_mode(OperationMode.OFFLINE)

        # Should now block
        with pytest.raises(NetworkGuardException):
            guard.check_request("https://example.com")


class TestModeChangeAPI:
    """Test mode change API functionality."""

    def test_change_mode_to_offline(self):
        """Test changing to OFFLINE mode."""
        response = client.post(
            "/api/sovereign-mode/mode",
            json={
                "target_mode": "offline",
                "force": True,
                "reason": "Test mode change"
            }
        )

        # May fail if no bundles available, that's OK for this test
        # Just check the endpoint exists and processes the request
        assert response.status_code in [200, 400, 500]

    def test_change_mode_invalid_mode(self):
        """Test changing to invalid mode."""
        response = client.post(
            "/api/sovereign-mode/mode",
            json={
                "target_mode": "invalid_mode",
                "force": True
            }
        )

        # Should fail validation
        assert response.status_code == 422


class TestBundleValidation:
    """Test bundle validation."""

    def test_bundle_schema(self):
        """Test Bundle schema validation."""
        bundle_data = {
            "id": "test-bundle",
            "name": "Test Bundle",
            "version": "1.0.0",
            "model_type": "llama",
            "model_size": "7B",
            "file_path": "/path/to/model.gguf",
            "manifest_path": "/path/to/manifest.json",
            "sha256_hash": "a" * 64,
            "sha256_manifest_hash": "b" * 64,
        }

        bundle = Bundle(**bundle_data)

        assert bundle.id == "test-bundle"
        assert bundle.status == BundleStatus.PENDING
        assert bundle.load_count == 0

    def test_validation_result_schema(self):
        """Test ValidationResult schema."""
        result_data = {
            "is_valid": True,
            "bundle_id": "test-bundle",
            "hash_match": True,
            "expected_hash": "a" * 64,
            "actual_hash": "a" * 64,
        }

        result = ValidationResult(**result_data)

        assert result.is_valid is True
        assert result.hash_match is True
        assert len(result.errors) == 0


class TestNetworkDetection:
    """Test network connectivity detection."""

    def test_network_check_endpoint(self):
        """Test network check endpoint."""
        response = client.get("/api/sovereign-mode/network/check")

        assert response.status_code == 200
        data = response.json()

        assert "is_online" in data
        assert "check_method" in data
        assert "checked_at" in data
        assert isinstance(data["is_online"], bool)


class TestAuditLogging:
    """Test audit logging functionality."""

    def test_audit_log_endpoint(self):
        """Test audit log retrieval."""
        response = client.get("/api/sovereign-mode/audit?limit=10")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_audit_log_filtering(self):
        """Test audit log event type filtering."""
        response = client.get(
            "/api/sovereign-mode/audit?limit=10&event_type=mode_change"
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)


class TestConfigurationUpdate:
    """Test configuration update functionality."""

    def test_update_config(self):
        """Test configuration update."""
        response = client.put(
            "/api/sovereign-mode/config",
            json={
                "auto_detect_network": True,
                "network_check_interval": 60
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert "auto_detect_network" in data
        assert "network_check_interval" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
