"""
Unit tests for Manifest Registry (Phase 2 Foundation).

Tests hash chain validation, versioning, and activation gate enforcement.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from app.modules.governor.manifest.schemas import (
    GovernorManifest,
    ManifestRule,
    RuleCondition,
    Budget,
    ShadowReport,
    ActivationGateConfig,
)
from app.modules.governor.manifest.registry import ManifestRegistry
from app.modules.neurorail.errors import (
    ManifestHashMismatchError,
    ActivationGateBlockedError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Create mock database session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def base_manifest():
    """Create base manifest for testing."""
    return GovernorManifest(
        manifest_id="test_manifest_v1",
        version="1.0.0",
        name="Test Manifest v1",
        description="Base manifest",
        created_at=datetime.utcnow(),
        hash_prev=None,  # First version, no previous hash
        hash_self=None,  # Will be computed
        rules=[
            ManifestRule(
                rule_id="rule_1",
                priority=100,
                enabled=True,
                when=RuleCondition(job_type="llm_call"),
                mode="RAIL",
                reason="LLM calls require governance",
            ),
        ],
        budget_defaults=Budget(
            timeout_ms=30000,
            max_retries=3,
        ),
        risk_classes={},
    )


@pytest.fixture
def successor_manifest(base_manifest):
    """Create successor manifest that references base."""
    # Compute hash of base manifest
    base_hash = base_manifest.compute_hash()

    return GovernorManifest(
        manifest_id="test_manifest_v2",
        version="1.1.0",
        name="Test Manifest v1.1",
        description="Successor manifest",
        created_at=datetime.utcnow(),
        hash_prev=base_hash,  # Reference base manifest
        hash_self=None,  # Will be computed
        rules=[
            ManifestRule(
                rule_id="rule_1",
                priority=100,
                enabled=True,
                when=RuleCondition(job_type="llm_call"),
                mode="RAIL",
                reason="LLM calls require governance",
            ),
            ManifestRule(
                rule_id="rule_2",
                priority=200,
                enabled=True,
                when=RuleCondition(environment="production"),
                mode="RAIL",
                reason="Production requires governance",
            ),
        ],
        budget_defaults=Budget(
            timeout_ms=30000,
            max_retries=3,
        ),
        risk_classes={},
    )


# ============================================================================
# Tests: Hash Computation
# ============================================================================

def test_manifest_compute_hash_deterministic(base_manifest):
    """Test that compute_hash is deterministic."""
    hash1 = base_manifest.compute_hash()
    hash2 = base_manifest.compute_hash()

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest


def test_manifest_compute_hash_different_content():
    """Test that different manifests produce different hashes."""
    manifest1 = GovernorManifest(
        manifest_id="m1",
        version="1.0.0",
        name="Manifest 1",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    manifest2 = GovernorManifest(
        manifest_id="m2",
        version="1.0.0",
        name="Manifest 2",  # Different name
        description="Test",
        created_at=datetime.utcnow(),
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    hash1 = manifest1.compute_hash()
    hash2 = manifest2.compute_hash()

    assert hash1 != hash2


def test_manifest_compute_hash_excludes_metadata():
    """Test that hash excludes metadata fields (manifest_id, created_at, etc.)."""
    manifest1 = GovernorManifest(
        manifest_id="m1",  # Different ID
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime(2023, 1, 1),  # Different timestamp
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    manifest2 = GovernorManifest(
        manifest_id="m2",  # Different ID
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime(2024, 1, 1),  # Different timestamp
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    # Hashes should be identical (metadata excluded)
    assert manifest1.compute_hash() == manifest2.compute_hash()


# ============================================================================
# Tests: Hash Chain Validation
# ============================================================================

@pytest.mark.asyncio
async def test_registry_create_with_valid_hash_chain(mock_db, base_manifest, successor_manifest):
    """Test creating manifest with valid hash chain."""
    registry = ManifestRegistry(mock_db)

    # Mock get method to return base manifest
    async def mock_get(version):
        if version == "1.0.0":
            base_manifest.hash_self = base_manifest.compute_hash()
            return base_manifest
        return None

    registry.get = AsyncMock(side_effect=mock_get)

    # Create successor manifest (should validate hash chain)
    await registry.create(successor_manifest, validate_hash_chain=True)

    # Should succeed (no exception raised)


@pytest.mark.asyncio
async def test_registry_create_with_invalid_hash_chain(mock_db, base_manifest, successor_manifest):
    """Test creating manifest with invalid hash chain raises error."""
    registry = ManifestRegistry(mock_db)

    # Mock get method to return modified base manifest
    async def mock_get(version):
        if version == "1.0.0":
            # Compute different hash (simulate tampered manifest)
            base_manifest.hash_self = "0" * 64  # Wrong hash
            return base_manifest
        return None

    registry.get = AsyncMock(side_effect=mock_get)

    # Should raise ManifestHashMismatchError
    with pytest.raises(ManifestHashMismatchError) as exc_info:
        await registry.create(successor_manifest, validate_hash_chain=True)

    assert "Hash mismatch" in str(exc_info.value)


@pytest.mark.asyncio
async def test_registry_create_skip_hash_validation(mock_db, successor_manifest):
    """Test creating manifest with hash validation skipped."""
    registry = ManifestRegistry(mock_db)

    # Don't mock get method - validation should be skipped
    await registry.create(successor_manifest, validate_hash_chain=False)

    # Should succeed even with invalid hash_prev


# ============================================================================
# Tests: Activation Gate
# ============================================================================

@pytest.mark.asyncio
async def test_registry_activate_with_safe_shadow_report(mock_db):
    """Test activation succeeds with safe shadow report."""
    registry = ManifestRegistry(mock_db)

    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        shadow_mode=True,
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    # Mock get method
    registry.get = AsyncMock(return_value=manifest)
    registry.get_active = AsyncMock(return_value=None)

    # Safe shadow report
    shadow_report = ShadowReport(
        manifest_version="1.0.0",
        shadow_start=datetime.utcnow() - timedelta(hours=48),
        shadow_end=datetime.utcnow(),
        evaluation_count=500,
        mode_divergence_count=10,
        mode_divergence_rate=0.02,  # 2% < 5% threshold
        budget_divergence_count=5,
        budget_divergence_rate=0.01,
        would_have_blocked=20,
        explosion_rate=0.04,  # 4% < 10% threshold
        rule_trigger_counts={},
        safe_to_activate=True,
        activation_gate_reason="All gates passed",
        sample_comparisons=[],
    )

    gate_config = ActivationGateConfig()

    # Should succeed
    await registry.activate("1.0.0", gate_config, shadow_report, force=False)


@pytest.mark.asyncio
async def test_registry_activate_with_unsafe_shadow_report(mock_db):
    """Test activation blocked with unsafe shadow report."""
    registry = ManifestRegistry(mock_db)

    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        shadow_mode=True,
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    # Mock get method
    registry.get = AsyncMock(return_value=manifest)

    # Unsafe shadow report (high divergence)
    shadow_report = ShadowReport(
        manifest_version="1.0.0",
        shadow_start=datetime.utcnow() - timedelta(hours=48),
        shadow_end=datetime.utcnow(),
        evaluation_count=500,
        mode_divergence_count=100,
        mode_divergence_rate=0.20,  # 20% > 5% threshold
        budget_divergence_count=50,
        budget_divergence_rate=0.10,
        would_have_blocked=200,
        explosion_rate=0.40,  # 40% > 10% threshold
        rule_trigger_counts={},
        safe_to_activate=False,
        activation_gate_reason="Mode divergence too high: 20% > 5%",
        sample_comparisons=[],
    )

    gate_config = ActivationGateConfig()

    # Should raise ActivationGateBlockedError
    with pytest.raises(ActivationGateBlockedError) as exc_info:
        await registry.activate("1.0.0", gate_config, shadow_report, force=False)

    assert "Activation gate blocked" in str(exc_info.value)
    assert "Mode divergence too high" in str(exc_info.value)


@pytest.mark.asyncio
async def test_registry_activate_with_force_flag(mock_db):
    """Test activation with force flag bypasses gate."""
    registry = ManifestRegistry(mock_db)

    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        shadow_mode=True,
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    # Mock get method
    registry.get = AsyncMock(return_value=manifest)
    registry.get_active = AsyncMock(return_value=None)

    # Unsafe shadow report
    shadow_report = ShadowReport(
        manifest_version="1.0.0",
        shadow_start=datetime.utcnow() - timedelta(hours=48),
        shadow_end=datetime.utcnow(),
        evaluation_count=500,
        mode_divergence_count=100,
        mode_divergence_rate=0.20,
        budget_divergence_count=50,
        budget_divergence_rate=0.10,
        would_have_blocked=200,
        explosion_rate=0.40,
        rule_trigger_counts={},
        safe_to_activate=False,
        activation_gate_reason="Unsafe",
        sample_comparisons=[],
    )

    gate_config = ActivationGateConfig()

    # Should succeed with force=True
    await registry.activate("1.0.0", gate_config, shadow_report, force=True)


# ============================================================================
# Tests: Version Management
# ============================================================================

@pytest.mark.asyncio
async def test_registry_list_versions(mock_db):
    """Test listing all manifest versions."""
    registry = ManifestRegistry(mock_db)

    # Mock database response
    mock_result = AsyncMock()
    mock_result.fetchall = AsyncMock(return_value=[
        ("1.0.0", "2023-01-01 00:00:00", True, False),
        ("1.1.0", "2023-02-01 00:00:00", False, False),
        ("1.2.0", "2023-03-01 00:00:00", False, True),
    ])
    mock_db.execute = AsyncMock(return_value=mock_result)

    versions = await registry.list_versions()

    assert len(versions) == 3
    assert versions[0]["version"] == "1.0.0"
    assert versions[0]["shadow_mode"] is True
    assert versions[2]["version"] == "1.2.0"
    assert versions[2]["shadow_mode"] is False


@pytest.mark.asyncio
async def test_registry_get_active_returns_none_if_no_active(mock_db):
    """Test get_active returns None when no manifest is active."""
    registry = ManifestRegistry(mock_db)

    # Mock database response (no active manifest)
    mock_result = AsyncMock()
    mock_result.fetchone = AsyncMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_result)

    active = await registry.get_active()

    assert active is None


# ============================================================================
# Tests: Edge Cases
# ============================================================================

def test_manifest_hash_chain_first_version():
    """Test that first version has hash_prev=None."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="First version",
        created_at=datetime.utcnow(),
        hash_prev=None,  # No previous version
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    # Should compute hash successfully
    hash_self = manifest.compute_hash()
    assert hash_self is not None
    assert len(hash_self) == 64


def test_manifest_hash_includes_all_rules():
    """Test that hash changes when rules are modified."""
    manifest1 = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_1",
                priority=100,
                enabled=True,
                when=RuleCondition(job_type="llm_call"),
                mode="RAIL",
                reason="LLM",
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    manifest2 = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_1",
                priority=100,
                enabled=True,
                when=RuleCondition(job_type="llm_call"),
                mode="DIRECT",  # Different mode
                reason="LLM",
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    hash1 = manifest1.compute_hash()
    hash2 = manifest2.compute_hash()

    # Hashes should differ
    assert hash1 != hash2
