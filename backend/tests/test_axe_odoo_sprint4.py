"""
AXE × Odoo Integration Tests

Tests for Sprint IV: Odoo module generation and orchestration

Test Coverage:
- Odoo connector endpoints
- Module spec parsing
- Module generation
- Registry and versioning
- Orchestration flows
- API endpoints with trust tier

Sprint IV: AXE × Odoo Integration
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
# Sample Module Spec
# ============================================================================

SAMPLE_MODULE_SPEC = """
Create an Odoo module called "test_brain_crm" v1.0.0
Summary: Test CRM extension for BRAiN
Dependencies: base, crm
Category: Customer Relationship Management

Model: test.brain.lead.stage
  Description: Custom Lead Stage for Testing
  - name (required text, label "Stage Name")
  - sequence (integer, default 10, label "Sequence")
  - color (integer, label "Color Index")
  - active (boolean, default True, label "Active")

Views:
  - Tree view with name, sequence, color, active
  - Form view with all fields

Access: base.group_user can read/write/create
"""


# ============================================================================
# Phase 1: Odoo Connector Tests
# ============================================================================


def test_odoo_status_endpoint_exists():
    """Test that Odoo status endpoint exists."""
    response = client.get("/api/odoo/status")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_odoo_status_returns_valid_schema():
    """Test that Odoo status endpoint returns valid schema."""
    response = client.get("/api/odoo/status")

    assert response.status_code == 200
    data = response.json()

    # Verify schema
    assert "connected" in data, "Missing 'connected' field"
    assert "status" in data, "Missing 'status' field"
    assert isinstance(data["connected"], bool), "'connected' must be a boolean"

    # Note: In test environment without Odoo, connected will be False
    # This is expected and correct fail-safe behavior


def test_odoo_modules_list_endpoint_exists():
    """Test that Odoo modules list endpoint exists."""
    response = client.get("/api/odoo/modules")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_odoo_modules_list_returns_valid_schema():
    """Test that Odoo modules list returns valid schema."""
    response = client.get("/api/odoo/modules")

    assert response.status_code == 200
    data = response.json()

    # Verify schema
    assert "modules" in data, "Missing 'modules' field"
    assert "total_count" in data, "Missing 'total_count' field"
    assert isinstance(data["modules"], list), "'modules' must be a list"
    assert isinstance(data["total_count"], int), "'total_count' must be an integer"


# ============================================================================
# Phase 2 & 3: Generator and Registry Tests
# ============================================================================


def test_module_generation_endpoint_exists():
    """Test that module generation endpoint exists."""
    payload = {
        "spec_text": SAMPLE_MODULE_SPEC,
        "auto_install": False,
    }

    response = client.post("/api/axe/odoo/module/generate", json=payload)

    # Should return 200 even if Odoo is not available (fail-safe)
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_module_generation_returns_valid_schema():
    """Test that module generation returns valid schema."""
    payload = {
        "spec_text": SAMPLE_MODULE_SPEC,
        "auto_install": False,
    }

    response = client.post("/api/axe/odoo/module/generate", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verify schema
    assert "success" in data, "Missing 'success' field"
    assert "status" in data, "Missing 'status' field"
    assert "module_name" in data, "Missing 'module_name' field"
    assert "version" in data, "Missing 'version' field"
    assert "operation" in data, "Missing 'operation' field"
    assert "message" in data, "Missing 'message' field"

    # Generation should succeed (even if installation fails)
    assert data["generation_success"] == True, "Generation should succeed"
    assert data["module_name"] == "test_brain_crm", "Module name should match spec"
    assert data["version"] == "1.0.0", "Version should match spec"


def test_module_generation_creates_files():
    """Test that module generation creates files in storage."""
    payload = {
        "spec_text": SAMPLE_MODULE_SPEC,
        "auto_install": False,
    }

    response = client.post("/api/axe/odoo/module/generate", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verify file count
    assert data["file_count"] > 0, "Should generate at least one file"

    # Expected files:
    # - __manifest__.py
    # - __init__.py
    # - models/__init__.py
    # - models/test_brain_lead_stage.py
    # - views/test_brain_lead_stage_views.xml
    # - security/ir.model.access.csv
    # - README.md
    assert data["file_count"] >= 7, "Should generate at least 7 files"


def test_registry_list_endpoint_exists():
    """Test that registry list endpoint exists."""
    response = client.get("/api/axe/odoo/modules")

    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_registry_list_returns_valid_schema():
    """Test that registry list returns valid schema."""
    response = client.get("/api/axe/odoo/modules")

    assert response.status_code == 200
    data = response.json()

    # Verify schema
    assert "modules" in data, "Missing 'modules' field"
    assert "total_count" in data, "Missing 'total_count' field"
    assert isinstance(data["modules"], list), "'modules' must be a list"


def test_registry_contains_generated_module():
    """Test that registry contains previously generated module."""
    # First, ensure module is generated
    payload = {
        "spec_text": SAMPLE_MODULE_SPEC,
        "auto_install": False,
    }

    gen_response = client.post("/api/axe/odoo/module/generate", json=payload)
    assert gen_response.status_code == 200

    # Then, check registry
    list_response = client.get("/api/axe/odoo/modules")
    assert list_response.status_code == 200

    data = list_response.json()

    # Find our module
    module_names = [m["module_name"] for m in data["modules"]]
    assert "test_brain_crm" in module_names, "Generated module should be in registry"


# ============================================================================
# Phase 4: Orchestration Flow Tests
# ============================================================================


def test_module_install_endpoint_exists():
    """Test that module install endpoint exists."""
    payload = {
        "module_name": "test_brain_crm",
        "version": "1.0.0",
        "force": False,
    }

    response = client.post("/api/axe/odoo/module/install", json=payload)

    # Should return 200 even if Odoo is not available (fail-safe)
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_module_upgrade_endpoint_exists():
    """Test that module upgrade endpoint exists."""
    payload = {
        "module_name": "test_brain_crm",
        "new_version": "1.1.0",
    }

    response = client.post("/api/axe/odoo/module/upgrade", json=payload)

    # Should return 200 (will fail without Odoo, but endpoint exists)
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


def test_module_rollback_endpoint_exists():
    """Test that module rollback endpoint exists."""
    payload = {
        "module_name": "test_brain_crm",
    }

    response = client.post("/api/axe/odoo/module/rollback", json=payload)

    # Should return 200 (will fail without multiple versions, but endpoint exists)
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )


# ============================================================================
# Phase 5: API Endpoints & Integration Tests
# ============================================================================


def test_axe_odoo_info_endpoint():
    """Test AXE × Odoo info endpoint."""
    response = client.get("/api/axe/odoo/info")

    assert response.status_code == 200
    data = response.json()

    # Verify info structure
    assert "name" in data
    assert "version" in data
    assert "features" in data
    assert "endpoints" in data

    assert data["name"] == "AXE × Odoo Integration"
    assert data["sprint"] == "Sprint IV"


def test_full_generation_flow():
    """
    Test full generation flow: Spec → Parse → Generate → Store.

    This is the core integration test for Sprint IV.
    """
    payload = {
        "spec_text": SAMPLE_MODULE_SPEC,
        "auto_install": False,  # Don't try to install (no Odoo in test env)
    }

    # Generate module
    response = client.post("/api/axe/odoo/module/generate", json=payload)

    assert response.status_code == 200
    data = response.json()

    # Verify generation succeeded
    assert data["generation_success"] == True
    assert data["module_name"] == "test_brain_crm"
    assert data["version"] == "1.0.0"
    assert data["file_count"] >= 7
    assert data["module_hash"] is not None

    # Verify in registry
    list_response = client.get("/api/axe/odoo/modules")
    assert list_response.status_code == 200

    registry_data = list_response.json()
    module = next(
        (m for m in registry_data["modules"] if m["module_name"] == "test_brain_crm"),
        None,
    )

    assert module is not None, "Module should be in registry"
    assert module["latest_version"] == "1.0.0"
    assert module["total_versions"] >= 1


def test_multiple_version_generation():
    """Test generating multiple versions of the same module."""
    # Generate v1.0.0
    spec_v1 = SAMPLE_MODULE_SPEC

    payload_v1 = {
        "spec_text": spec_v1,
        "auto_install": False,
    }

    response_v1 = client.post("/api/axe/odoo/module/generate", json=payload_v1)
    assert response_v1.status_code == 200

    # Generate v1.1.0 (modified spec)
    spec_v2 = SAMPLE_MODULE_SPEC.replace("v1.0.0", "v1.1.0")

    payload_v2 = {
        "spec_text": spec_v2,
        "auto_install": False,
    }

    response_v2 = client.post("/api/axe/odoo/module/generate", json=payload_v2)
    assert response_v2.status_code == 200

    data_v2 = response_v2.json()
    assert data_v2["version"] == "1.1.0"

    # Verify registry has both versions
    list_response = client.get("/api/axe/odoo/modules")
    assert list_response.status_code == 200

    registry_data = list_response.json()
    module = next(
        (m for m in registry_data["modules"] if m["module_name"] == "test_brain_crm"),
        None,
    )

    assert module is not None
    assert module["total_versions"] >= 2, "Should have at least 2 versions"
    assert module["latest_version"] == "1.1.0"


# ============================================================================
# Fail-Safe Tests (Sprint IV Requirement)
# ============================================================================


def test_generation_with_invalid_spec():
    """Test that generation fails gracefully with invalid spec."""
    payload = {
        "spec_text": "This is not a valid module spec",
        "auto_install": False,
    }

    response = client.post("/api/axe/odoo/module/generate", json=payload)

    # Should return 200 with error details (fail-safe)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] == False or data["generation_success"] == False
    assert len(data["errors"]) > 0, "Should have error messages"


def test_install_nonexistent_module():
    """Test that install fails gracefully for nonexistent module."""
    payload = {
        "module_name": "nonexistent_module_xyz",
        "version": "1.0.0",
    }

    response = client.post("/api/axe/odoo/module/install", json=payload)

    # Should return 200 with error (fail-safe)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] == False
    assert len(data["errors"]) > 0


def test_rollback_with_insufficient_history():
    """Test that rollback fails gracefully with only one version."""
    # Generate single version
    payload = {
        "spec_text": """
Create an Odoo module called "test_rollback_single" v1.0.0
Summary: Test module for rollback

Model: test.rollback.model
  - name (required text)

Views:
  - Form view with all fields
        """,
        "auto_install": False,
    }

    gen_response = client.post("/api/axe/odoo/module/generate", json=payload)
    assert gen_response.status_code == 200

    # Try to rollback (should fail - no previous version)
    rollback_payload = {
        "module_name": "test_rollback_single",
    }

    rollback_response = client.post(
        "/api/axe/odoo/module/rollback", json=rollback_payload
    )

    # Should return 200 with error (fail-safe)
    assert rollback_response.status_code == 200
    data = rollback_response.json()

    assert data["success"] == False
    assert len(data["errors"]) > 0


# ============================================================================
# Edge Case Tests
# ============================================================================


def test_empty_spec_handling():
    """Test handling of empty spec text."""
    payload = {
        "spec_text": "",
        "auto_install": False,
    }

    response = client.post("/api/axe/odoo/module/generate", json=payload)

    # Should return 200 with error (fail-safe)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] == False
    assert len(data["errors"]) > 0


def test_module_name_validation():
    """Test module name validation in spec."""
    spec_invalid_name = """
Create an Odoo module called "Invalid Name With Spaces" v1.0.0
Summary: Test

Model: test.model
  - name (text)
    """

    payload = {
        "spec_text": spec_invalid_name,
        "auto_install": False,
    }

    response = client.post("/api/axe/odoo/module/generate", json=payload)

    # Should either fail or warn (depending on parser implementation)
    assert response.status_code == 200
    data = response.json()

    # Either failed or has warnings about invalid name
    assert data["success"] == False or len(data["warnings"]) > 0
