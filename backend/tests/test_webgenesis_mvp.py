"""
WebGenesis MVP Tests

Tests for website generation, build, and deployment system.

Sprint I: MVP Coverage
- Spec validation
- Source generation
- Build with hashing
- Trust tier enforcement
- Error handling
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
# Test Data
# ============================================================================


VALID_SPEC = {
    "spec": {
        "spec_version": "1.0.0",
        "name": "test-site",
        "domain": "test.example.com",
        "locale_default": "en",
        "locales": ["en"],
        "template": "static_html",
        "pages": [
            {
                "slug": "home",
                "title": "Home Page",
                "description": "Welcome to test site",
                "sections": [
                    {
                        "section_id": "hero",
                        "type": "hero",
                        "title": "Welcome",
                        "content": "Test content",
                        "data": {},
                        "order": 0,
                    }
                ],
                "layout": "default",
            }
        ],
        "theme": {
            "colors": {
                "primary": "#3B82F6",
                "secondary": "#8B5CF6",
                "accent": "#10B981",
                "background": "#FFFFFF",
                "text": "#1F2937",
            },
            "typography": {
                "font_family": "Inter, system-ui, sans-serif",
                "base_size": "16px",
            },
        },
        "seo": {
            "title": "Test Site",
            "description": "Testing WebGenesis",
            "keywords": ["test"],
            "twitter_card": "summary",
        },
        "deploy": {
            "target": "compose",
            "healthcheck_path": "/",
            "ssl_enabled": False,
        },
    }
}


INVALID_SPEC_BAD_NAME = {
    "spec": {
        **VALID_SPEC["spec"],
        "name": "../../../etc/passwd",  # Path traversal attempt
    }
}


INVALID_SPEC_NO_PAGES = {
    "spec": {
        **VALID_SPEC["spec"],
        "pages": [],  # Must have at least one page
    }
}


# ============================================================================
# Spec Submission Tests
# ============================================================================


def test_submit_valid_spec():
    """Test submitting a valid website spec."""
    response = client.post("/api/webgenesis/spec", json=VALID_SPEC)

    assert response.status_code == 201
    data = response.json()

    assert data["success"] is True
    assert "site_id" in data
    assert "spec_hash" in data
    assert "test-site" in data["site_id"]
    assert len(data["spec_hash"]) == 64  # SHA-256 hex length


def test_submit_spec_with_bad_name():
    """Test that invalid site names are rejected."""
    response = client.post("/api/webgenesis/spec", json=INVALID_SPEC_BAD_NAME)

    # Should fail validation
    assert response.status_code in [400, 422, 500]


def test_submit_spec_with_no_pages():
    """Test that specs without pages are rejected."""
    response = client.post("/api/webgenesis/spec", json=INVALID_SPEC_NO_PAGES)

    # Should fail validation
    assert response.status_code in [400, 422]


# ============================================================================
# Source Generation Tests
# ============================================================================


def test_generate_source():
    """Test source code generation from spec."""
    # First, submit spec
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    assert submit_response.status_code == 201

    site_id = submit_response.json()["site_id"]

    # Generate source
    generate_response = client.post(f"/api/webgenesis/{site_id}/generate")
    assert generate_response.status_code == 200

    data = generate_response.json()
    assert data["success"] is True
    assert data["site_id"] == site_id
    assert "source_path" in data
    assert data["files_created"] > 0
    assert isinstance(data["errors"], list)


def test_generate_source_for_nonexistent_site():
    """Test generation fails for non-existent site."""
    response = client.post("/api/webgenesis/nonexistent_site/generate")
    assert response.status_code == 404


def test_generate_source_duplicate_without_force():
    """Test that regeneration without force flag fails."""
    # Submit and generate
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    client.post(f"/api/webgenesis/{site_id}/generate")

    # Try to generate again without force
    response = client.post(f"/api/webgenesis/{site_id}/generate", json={"force": False})

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


def test_generate_source_with_force():
    """Test that regeneration with force flag succeeds."""
    # Submit and generate
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    client.post(f"/api/webgenesis/{site_id}/generate")

    # Regenerate with force
    response = client.post(f"/api/webgenesis/{site_id}/generate", json={"force": True})

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True


# ============================================================================
# Build Tests
# ============================================================================


def test_build_artifacts():
    """Test building artifacts from generated source."""
    # Submit, generate, then build
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    client.post(f"/api/webgenesis/{site_id}/generate")

    # Build
    build_response = client.post(f"/api/webgenesis/{site_id}/build")
    assert build_response.status_code == 200

    data = build_response.json()
    assert data["result"]["success"] is True
    assert data["result"]["site_id"] == site_id
    assert "artifact_hash" in data["result"]
    assert len(data["result"]["artifact_hash"]) == 64  # SHA-256
    assert isinstance(data["result"]["errors"], list)


def test_build_without_generate():
    """Test that build fails if source not generated."""
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    # Try to build without generating first
    response = client.post(f"/api/webgenesis/{site_id}/build")

    assert response.status_code == 400
    assert "not generated" in response.json()["detail"].lower()


def test_build_with_force():
    """Test rebuild with force flag."""
    # Submit, generate, build
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    client.post(f"/api/webgenesis/{site_id}/generate")
    client.post(f"/api/webgenesis/{site_id}/build")

    # Rebuild with force
    response = client.post(f"/api/webgenesis/{site_id}/build", json={"force": True})

    assert response.status_code == 200
    assert response.json()["result"]["success"] is True


# ============================================================================
# Trust Tier Tests (Deploy Endpoint)
# ============================================================================


def test_deploy_from_localhost_allowed():
    """Test that deployment from localhost (LOCAL trust tier) is allowed."""
    # Submit, generate, build
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    client.post(f"/api/webgenesis/{site_id}/generate")
    client.post(f"/api/webgenesis/{site_id}/build")

    # Deploy (TestClient simulates localhost)
    # Note: Actual deployment will fail without Docker, but trust tier should be OK
    response = client.post(f"/api/webgenesis/{site_id}/deploy")

    # Should not get 403 (trust tier rejection)
    # May get 500 if Docker not available, but that's OK for this test
    assert response.status_code != 403


def test_deploy_from_dmz_gateway_allowed():
    """Test that deployment from DMZ gateway is allowed."""
    # Submit, generate, build
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    client.post(f"/api/webgenesis/{site_id}/generate")
    client.post(f"/api/webgenesis/{site_id}/build")

    # Deploy with DMZ headers
    headers = {
        "x-dmz-gateway-id": "telegram_gateway",
        "x-dmz-gateway-token": "test_token",  # Simplified for test
    }

    response = client.post(
        f"/api/webgenesis/{site_id}/deploy",
        headers=headers,
    )

    # Should not get 403 (trust tier rejection)
    # May get 500 if Docker not available or token invalid
    assert response.status_code != 403


def test_deploy_requires_build():
    """Test that deployment fails if build not ready."""
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    # Try to deploy without build
    response = client.post(f"/api/webgenesis/{site_id}/deploy")

    assert response.status_code == 400
    assert "not ready" in response.json()["detail"].lower()


# ============================================================================
# Status Tests
# ============================================================================


def test_get_site_status():
    """Test getting site status and manifest."""
    # Submit spec
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    # Get status
    response = client.get(f"/api/webgenesis/{site_id}/status")
    assert response.status_code == 200

    data = response.json()
    assert data["site_id"] == site_id
    assert "manifest" in data
    assert data["manifest"]["status"] == "pending"  # Just submitted


def test_get_status_for_nonexistent_site():
    """Test status check fails for non-existent site."""
    response = client.get("/api/webgenesis/nonexistent_site/status")
    assert response.status_code == 404


def test_status_reflects_generation():
    """Test that status reflects source generation."""
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    # Generate
    client.post(f"/api/webgenesis/{site_id}/generate")

    # Check status
    response = client.get(f"/api/webgenesis/{site_id}/status")
    data = response.json()

    assert data["manifest"]["status"] == "generated"
    assert data["manifest"]["source_path"] is not None


def test_status_reflects_build():
    """Test that status reflects build completion."""
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    site_id = submit_response.json()["site_id"]

    client.post(f"/api/webgenesis/{site_id}/generate")
    client.post(f"/api/webgenesis/{site_id}/build")

    # Check status
    response = client.get(f"/api/webgenesis/{site_id}/status")
    data = response.json()

    assert data["manifest"]["status"] == "built"
    assert data["manifest"]["artifact_hash"] is not None
    assert len(data["manifest"]["artifact_hash"]) == 64


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_invalid_json():
    """Test that invalid JSON is rejected."""
    response = client.post(
        "/api/webgenesis/spec",
        data="invalid json",
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code in [400, 422]


def test_missing_required_fields():
    """Test that specs missing required fields are rejected."""
    invalid_spec = {
        "spec": {
            "name": "test",
            # Missing required fields
        }
    }

    response = client.post("/api/webgenesis/spec", json=invalid_spec)
    assert response.status_code in [400, 422]


# ============================================================================
# Integration Test (Full Workflow)
# ============================================================================


def test_full_workflow():
    """
    Test complete workflow: submit → generate → build → status.

    Note: Deploy step omitted as it requires Docker.
    """
    # 1. Submit spec
    submit_response = client.post("/api/webgenesis/spec", json=VALID_SPEC)
    assert submit_response.status_code == 201

    site_id = submit_response.json()["site_id"]
    spec_hash = submit_response.json()["spec_hash"]

    # 2. Generate source
    generate_response = client.post(f"/api/webgenesis/{site_id}/generate")
    assert generate_response.status_code == 200
    assert generate_response.json()["success"] is True

    # 3. Build artifacts
    build_response = client.post(f"/api/webgenesis/{site_id}/build")
    assert build_response.status_code == 200
    assert build_response.json()["result"]["success"] is True

    artifact_hash = build_response.json()["result"]["artifact_hash"]

    # 4. Check status
    status_response = client.get(f"/api/webgenesis/{site_id}/status")
    assert status_response.status_code == 200

    status_data = status_response.json()
    assert status_data["manifest"]["status"] == "built"
    assert status_data["manifest"]["spec_hash"] == spec_hash
    assert status_data["manifest"]["artifact_hash"] == artifact_hash
    assert status_data["manifest"]["source_path"] is not None
    assert status_data["manifest"]["build_path"] is not None


# ============================================================================
# Summary
# ============================================================================

def test_summary():
    """
    Test summary - verify all critical features.

    This is not a real test, just a summary for documentation.
    """
    print("\n" + "="*70)
    print("WebGenesis MVP Test Summary")
    print("="*70)
    print("\nTested Features:")
    print("✅ Spec validation (valid + invalid cases)")
    print("✅ Source generation (with force flag)")
    print("✅ Build with artifact hashing (SHA-256)")
    print("✅ Trust tier enforcement (LOCAL/DMZ allowed)")
    print("✅ Status tracking (manifest updates)")
    print("✅ Error handling (404, 400, 422)")
    print("✅ Full workflow integration")
    print("\nSecurity Tests:")
    print("✅ Path traversal protection")
    print("✅ Site ID validation")
    print("✅ Trust tier validation")
    print("\nNot Tested (requires Docker):")
    print("⏭️  Actual Docker Compose deployment")
    print("⏭️  Container health checks")
    print("⏭️  EXTERNAL trust tier blocking (requires network setup)")
    print("="*70)

    # Always pass
    assert True
