"""
Unit tests for Manifest Loader (Phase 2 Foundation).

Tests JSON loading, schema validation, and default manifest creation.
"""

import pytest
import json
from datetime import datetime
from backend.app.modules.governor.manifest.schemas import (
    GovernorManifest,
    Budget,
    RiskClass,
)
from backend.app.modules.governor.manifest.loader import ManifestLoader
from backend.app.modules.governor.decision.models import RecoveryStrategy


# ============================================================================
# Tests: Default Manifest
# ============================================================================

def test_loader_create_default_manifest():
    """Test creating default manifest."""
    manifest = ManifestLoader.create_default_manifest()

    assert manifest.version == "1.0.0"
    assert manifest.name == "Default Manifest"
    assert len(manifest.rules) > 0
    assert manifest.budget_defaults is not None
    assert len(manifest.risk_classes) > 0


def test_loader_default_manifest_has_risk_classes():
    """Test default manifest includes risk classes."""
    manifest = ManifestLoader.create_default_manifest()

    assert "INTERNAL" in manifest.risk_classes
    assert "EXTERNAL" in manifest.risk_classes
    assert "NON_IDEMPOTENT" in manifest.risk_classes

    # Check risk class attributes
    external = manifest.risk_classes["EXTERNAL"]
    assert external.recovery_strategy == RecoveryStrategy.RETRY
    assert external.budget_multiplier == 1.5

    non_idempotent = manifest.risk_classes["NON_IDEMPOTENT"]
    assert non_idempotent.recovery_strategy == RecoveryStrategy.ROLLBACK_REQUIRED
    assert non_idempotent.budget_multiplier == 2.0


def test_loader_default_manifest_has_governance_rules():
    """Test default manifest includes key governance rules."""
    manifest = ManifestLoader.create_default_manifest()

    rule_ids = [rule.rule_id for rule in manifest.rules]

    # Should have core governance rules
    assert "llm_call_governance" in rule_ids
    assert "production_governance" in rule_ids
    assert "personal_data_governance" in rule_ids


# ============================================================================
# Tests: Dictionary Loading
# ============================================================================

def test_loader_from_dict_simple():
    """Test loading manifest from simple dictionary."""
    data = {
        "version": "1.0.0",
        "name": "Test Manifest",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [],
    }

    manifest = ManifestLoader.from_dict(data)

    assert manifest.version == "1.0.0"
    assert manifest.name == "Test Manifest"
    assert manifest.budget_defaults.timeout_ms == 30000
    assert manifest.budget_defaults.max_retries == 3
    assert len(manifest.rules) == 0


def test_loader_from_dict_with_rules():
    """Test loading manifest with rules."""
    data = {
        "version": "1.0.0",
        "name": "Test Manifest",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [
            {
                "rule_id": "rule_1",
                "priority": 100,
                "enabled": True,
                "when": {
                    "job_type": "llm_call"
                },
                "mode": "RAIL",
                "reason": "LLM calls require governance",
            },
        ],
    }

    manifest = ManifestLoader.from_dict(data)

    assert len(manifest.rules) == 1
    rule = manifest.rules[0]
    assert rule.rule_id == "rule_1"
    assert rule.priority == 100
    assert rule.mode == "RAIL"
    assert rule.when.job_type == "llm_call"


def test_loader_from_dict_with_or_logic():
    """Test loading manifest with OR-logic rules."""
    data = {
        "version": "1.0.0",
        "name": "Test Manifest",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [
            {
                "rule_id": "rule_or",
                "priority": 100,
                "enabled": True,
                "when": {
                    "any": [
                        {"job_type": "llm_call"},
                        {"job_type": "tool_execution"},
                    ]
                },
                "mode": "RAIL",
                "reason": "LLM or tool execution",
            },
        ],
    }

    manifest = ManifestLoader.from_dict(data)

    rule = manifest.rules[0]
    assert rule.when.any is not None
    assert len(rule.when.any) == 2


def test_loader_from_dict_with_and_logic():
    """Test loading manifest with AND-logic rules."""
    data = {
        "version": "1.0.0",
        "name": "Test Manifest",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [
            {
                "rule_id": "rule_and",
                "priority": 100,
                "enabled": True,
                "when": {
                    "all": [
                        {"job_type": "llm_call"},
                        {"environment": "production"},
                    ]
                },
                "mode": "RAIL",
                "reason": "Production LLM calls",
            },
        ],
    }

    manifest = ManifestLoader.from_dict(data)

    rule = manifest.rules[0]
    assert rule.when.all is not None
    assert len(rule.when.all) == 2


def test_loader_from_dict_with_budget_override():
    """Test loading manifest with rule budget overrides."""
    data = {
        "version": "1.0.0",
        "name": "Test Manifest",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [
            {
                "rule_id": "rule_override",
                "priority": 100,
                "enabled": True,
                "when": {
                    "job_type": "llm_call"
                },
                "mode": "RAIL",
                "reason": "LLM",
                "budget_override": {
                    "timeout_ms": 60000,
                    "max_retries": 5,
                },
            },
        ],
    }

    manifest = ManifestLoader.from_dict(data)

    rule = manifest.rules[0]
    assert rule.budget_override is not None
    assert rule.budget_override.timeout_ms == 60000
    assert rule.budget_override.max_retries == 5


def test_loader_from_dict_with_job_overrides():
    """Test loading manifest with job-specific budget overrides."""
    data = {
        "version": "1.0.0",
        "name": "Test Manifest",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [],
        "job_overrides": {
            "llm_call": {
                "timeout_ms": 90000,
                "max_retries": 7,
            },
        },
    }

    manifest = ManifestLoader.from_dict(data)

    assert "llm_call" in manifest.job_overrides
    override = manifest.job_overrides["llm_call"]
    assert override.timeout_ms == 90000
    assert override.max_retries == 7


def test_loader_from_dict_with_risk_classes():
    """Test loading manifest with risk classes."""
    data = {
        "version": "1.0.0",
        "name": "Test Manifest",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {
            "EXTERNAL": {
                "name": "EXTERNAL",
                "description": "External services",
                "recovery_strategy": "RETRY",
                "budget_multiplier": 1.5,
            },
        },
        "rules": [],
    }

    manifest = ManifestLoader.from_dict(data)

    assert "EXTERNAL" in manifest.risk_classes
    risk_class = manifest.risk_classes["EXTERNAL"]
    assert risk_class.recovery_strategy == RecoveryStrategy.RETRY
    assert risk_class.budget_multiplier == 1.5


# ============================================================================
# Tests: JSON File Loading
# ============================================================================

def test_loader_from_json_file(tmp_path):
    """Test loading manifest from JSON file."""
    # Create temporary JSON file
    manifest_data = {
        "version": "1.0.0",
        "name": "Test Manifest",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [],
    }

    json_file = tmp_path / "manifest.json"
    json_file.write_text(json.dumps(manifest_data, indent=2))

    # Load from file
    manifest = ManifestLoader.from_json_file(str(json_file))

    assert manifest.version == "1.0.0"
    assert manifest.name == "Test Manifest"


def test_loader_from_json_file_invalid_path():
    """Test loading from non-existent file raises error."""
    with pytest.raises(FileNotFoundError):
        ManifestLoader.from_json_file("/nonexistent/manifest.json")


# ============================================================================
# Tests: Validation
# ============================================================================

def test_loader_validates_required_fields():
    """Test that loader validates required fields."""
    # Missing budget_defaults
    data = {
        "version": "1.0.0",
        "name": "Test",
        "description": "Test",
        "rules": [],
    }

    with pytest.raises(Exception):  # Pydantic validation error
        ManifestLoader.from_dict(data)


def test_loader_validates_rule_priority():
    """Test that loader validates rule priority (positive integer)."""
    data = {
        "version": "1.0.0",
        "name": "Test",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [
            {
                "rule_id": "rule_1",
                "priority": -1,  # Invalid (negative)
                "enabled": True,
                "when": {"job_type": "llm_call"},
                "mode": "RAIL",
                "reason": "Test",
            },
        ],
    }

    with pytest.raises(Exception):  # Pydantic validation error
        ManifestLoader.from_dict(data)


def test_loader_validates_mode():
    """Test that loader validates mode (DIRECT or RAIL)."""
    data = {
        "version": "1.0.0",
        "name": "Test",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [
            {
                "rule_id": "rule_1",
                "priority": 100,
                "enabled": True,
                "when": {"job_type": "llm_call"},
                "mode": "INVALID",  # Invalid mode
                "reason": "Test",
            },
        ],
    }

    with pytest.raises(Exception):  # Pydantic validation error
        ManifestLoader.from_dict(data)


# ============================================================================
# Tests: Edge Cases
# ============================================================================

def test_loader_empty_rules_list():
    """Test loading manifest with empty rules list."""
    data = {
        "version": "1.0.0",
        "name": "Test",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [],  # Empty rules
    }

    manifest = ManifestLoader.from_dict(data)

    assert len(manifest.rules) == 0


def test_loader_optional_fields_default_to_none():
    """Test that optional fields default to None/empty."""
    data = {
        "version": "1.0.0",
        "name": "Test",
        "description": "Test",
        "budget_defaults": {
            "timeout_ms": 30000,
            "max_retries": 3,
        },
        "risk_classes": {},
        "rules": [],
        # No job_overrides, hash_prev, etc.
    }

    manifest = ManifestLoader.from_dict(data)

    assert manifest.hash_prev is None
    assert manifest.hash_self is None
    assert len(manifest.job_overrides) == 0
