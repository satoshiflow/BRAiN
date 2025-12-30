"""
Tests for Genesis Agent System

Tests spawn, evolve, and reproduce functionality.
"""

import sys
import os

# Path setup for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.app.modules.genesis.blueprints import get_blueprint_library
from backend.app.modules.genesis.traits import get_trait_service
from backend.app.modules.genesis.foundation import get_foundation_layer

client = TestClient(app)


# ============================================================================
# BLUEPRINT TESTS
# ============================================================================


def test_list_blueprints():
    """Test listing all blueprints."""
    response = client.get("/api/genesis/blueprints")

    assert response.status_code == 200
    blueprints = response.json()

    assert isinstance(blueprints, list)
    assert len(blueprints) >= 5  # At least 5 built-in blueprints

    # Check fleet coordinator exists
    fleet_bp = next(
        (bp for bp in blueprints if bp["id"] == "fleet_coordinator_v1"), None
    )
    assert fleet_bp is not None
    assert fleet_bp["name"] == "Fleet Coordinator"


def test_get_blueprint():
    """Test getting specific blueprint."""
    response = client.get("/api/genesis/blueprints/fleet_coordinator_v1")

    assert response.status_code == 200
    blueprint = response.json()

    assert blueprint["id"] == "fleet_coordinator_v1"
    assert blueprint["name"] == "Fleet Coordinator"
    assert "trait_profile" in blueprint
    assert "capabilities" in blueprint
    assert blueprint["allow_mutations"] is True


def test_get_nonexistent_blueprint():
    """Test getting non-existent blueprint."""
    response = client.get("/api/genesis/blueprints/nonexistent_v1")

    assert response.status_code == 404


# ============================================================================
# TRAIT TESTS
# ============================================================================


def test_list_traits():
    """Test listing all trait definitions."""
    response = client.get("/api/genesis/traits")

    assert response.status_code == 200
    traits = response.json()

    assert isinstance(traits, list)
    assert len(traits) >= 20  # At least 20 traits

    # Check safety priority trait exists
    safety_trait = next(
        (t for t in traits if t["id"] == "ethical.safety_priority"), None
    )
    assert safety_trait is not None
    assert safety_trait["mutable"] is False  # IMMUTABLE
    assert safety_trait["ethics_critical"] is True
    assert safety_trait["min_value"] == 0.7


def test_get_trait():
    """Test getting specific trait."""
    response = client.get("/api/genesis/traits/cognitive.reasoning_depth")

    assert response.status_code == 200
    trait = response.json()

    assert trait["id"] == "cognitive.reasoning_depth"
    assert trait["category"] == "cognitive"
    assert trait["type"] == "float"


def test_filter_traits_by_category():
    """Test filtering traits by category."""
    response = client.get("/api/genesis/traits?category=ethical")

    assert response.status_code == 200
    traits = response.json()

    assert all(t["category"] == "ethical" for t in traits)
    assert len(traits) >= 4  # At least 4 ethical traits


# ============================================================================
# SPAWN TESTS
# ============================================================================


def test_spawn_agent_basic():
    """Test basic agent spawning."""
    payload = {
        "blueprint_id": "fleet_coordinator_v1",
        "agent_id": "test_fleet_001",
        "seed": 42,
    }

    response = client.post("/api/genesis/spawn", json=payload)

    assert response.status_code == 200
    result = response.json()

    assert result["agent_id"] == "test_fleet_001"
    assert result["blueprint_id"] == "fleet_coordinator_v1"
    assert "dna_snapshot_id" in result
    assert "traits" in result
    assert len(result["traits"]) > 0


def test_spawn_agent_with_overrides():
    """Test spawning with trait overrides."""
    payload = {
        "blueprint_id": "code_specialist_v1",
        "agent_id": "test_coder_001",
        "trait_overrides": {
            "cognitive.creativity": 0.8,
            "performance.speed_priority": 0.6,
        },
        "seed": 123,
    }

    response = client.post("/api/genesis/spawn", json=payload)

    assert response.status_code == 200
    result = response.json()

    assert result["agent_id"] == "test_coder_001"
    assert result["traits"]["cognitive.creativity"] == 0.8
    assert result["traits"]["performance.speed_priority"] == 0.6


def test_spawn_agent_ethics_violation():
    """Test spawning with ethics violation."""
    payload = {
        "blueprint_id": "fleet_coordinator_v1",
        "agent_id": "test_unsafe_001",
        "trait_overrides": {
            "ethical.safety_priority": 0.5  # Below minimum!
        },
    }

    response = client.post("/api/genesis/spawn", json=payload)

    assert response.status_code == 403  # Ethics violation
    assert "ethics violation" in response.json()["detail"].lower()


def test_spawn_agent_invalid_blueprint():
    """Test spawning with invalid blueprint."""
    payload = {
        "blueprint_id": "nonexistent_v1",
        "agent_id": "test_invalid_001",
    }

    response = client.post("/api/genesis/spawn", json=payload)

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


# ============================================================================
# VALIDATION TESTS
# ============================================================================


def test_validate_agent_config_valid():
    """Test validation with valid config."""
    payload = {
        "blueprint_id": "fleet_coordinator_v1",
        "agent_id": "test_validate_001",
        "traits": {
            "ethical.safety_priority": 0.9,
            "performance.speed_priority": 0.7,
        },
        "config": {},
        "tools": [],
        "permissions": [],
    }

    response = client.post("/api/genesis/validate", json=payload)

    assert response.status_code == 200
    result = response.json()

    assert result["allowed"] is True
    assert len(result["violations"]) == 0


def test_validate_agent_config_violation():
    """Test validation with ethics violation."""
    payload = {
        "blueprint_id": "fleet_coordinator_v1",
        "agent_id": "test_validate_002",
        "traits": {
            "ethical.safety_priority": 0.3,  # Too low!
        },
        "config": {},
        "tools": [],
        "permissions": [],
    }

    response = client.post("/api/genesis/validate", json=payload)

    assert response.status_code == 200
    result = response.json()

    assert result["allowed"] is False
    assert len(result["violations"]) > 0


# ============================================================================
# SYSTEM INFO TESTS
# ============================================================================


def test_genesis_info():
    """Test Genesis system info endpoint."""
    response = client.get("/api/genesis/info")

    assert response.status_code == 200
    info = response.json()

    assert info["name"] == "BRAIN Genesis Agent System"
    assert info["version"] == "1.0.0"
    assert "blueprints" in info
    assert "traits" in info
    assert "features" in info

    assert info["blueprints"]["total"] >= 5
    assert info["traits"]["total"] >= 20


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


def test_blueprint_library_singleton():
    """Test blueprint library singleton."""
    lib1 = get_blueprint_library()
    lib2 = get_blueprint_library()

    assert lib1 is lib2  # Same instance


def test_trait_service_singleton():
    """Test trait service singleton."""
    svc1 = get_trait_service()
    svc2 = get_trait_service()

    assert svc1 is svc2  # Same instance


def test_foundation_layer_singleton():
    """Test foundation layer singleton."""
    fl1 = get_foundation_layer()
    fl2 = get_foundation_layer()

    assert fl1 is fl2  # Same instance


def test_builtin_blueprints_count():
    """Test that all built-in blueprints are loaded."""
    library = get_blueprint_library()
    blueprints = library.list_all()

    expected_ids = [
        "fleet_coordinator_v1",
        "safety_monitor_v1",
        "navigation_planner_v1",
        "code_specialist_v1",
        "ops_specialist_v1",
    ]

    for blueprint_id in expected_ids:
        assert library.get(blueprint_id) is not None


def test_trait_categories():
    """Test all trait categories are represented."""
    trait_service = get_trait_service()
    definitions = trait_service.get_all_definitions()

    from backend.app.modules.genesis.traits.schemas import TraitCategory

    categories = set(d.category for d in definitions)

    expected_categories = {
        TraitCategory.COGNITIVE,
        TraitCategory.ETHICAL,
        TraitCategory.PERFORMANCE,
        TraitCategory.BEHAVIORAL,
        TraitCategory.SOCIAL,
        TraitCategory.TECHNICAL,
    }

    assert categories == expected_categories


def test_immutable_traits():
    """Test that critical traits are marked immutable."""
    trait_service = get_trait_service()

    safety = trait_service.get_definition("ethical.safety_priority")
    assert safety.mutable is False
    assert safety.ethics_critical is True

    harm = trait_service.get_definition("ethical.harm_avoidance")
    assert harm.mutable is False
    assert harm.ethics_critical is True
