"""
Locked Fields Enforcement Tests (Phase 2c)

Comprehensive test suite for locked field validation and enforcement.

Test Coverage:
- Unit tests for LockedFieldEnforcer (10 tests)
- Integration tests with Governor (5 tests)
- Edge cases and error handling (3 tests)

Total: 18 tests with >95% coverage target

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-04
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
import time

from backend.brain.agents.genesis_agent.dna_schema import AgentType
from backend.brain.governor.enforcement.locks import (
    LockedFieldEnforcer,
    LockedFieldViolation,
    PolicyViolationError,
)
from backend.brain.governor.manifests.loader import ManifestLoader
from backend.brain.governor.governor import Governor
from backend.brain.governor.decision.models import (
    DecisionRequest,
    ActorContext,
    RequestContext,
    ReasonCode,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def manifest_loader():
    """Create ManifestLoader instance."""
    return ManifestLoader()


@pytest.fixture
def enforcer(manifest_loader):
    """Create LockedFieldEnforcer instance."""
    return LockedFieldEnforcer(manifest_loader=manifest_loader)


@pytest.fixture
def sample_dna():
    """Sample agent DNA for testing."""
    return {
        "metadata": {
            "type": "worker",
            "name": "test_agent"
        },
        "ethics_flags": {
            "human_override": "always_allowed"
        },
        "capabilities": {
            "can_create_agents": False,
            "can_modify_governor": False
        },
        "budget": {
            "max_llm_tokens": 5000
        }
    }


# ============================================================================
# Unit Tests: LockedFieldEnforcer
# ============================================================================

def test_valid_dna_no_mutations(enforcer, sample_dna):
    """Test 1: DNA with no locked field mutations should pass."""
    # Only mutate non-locked field
    dna = {"budget.max_llm_tokens": 3000}

    # Should not raise
    violations = enforcer.validate_dna_against_locks(
        agent_type=AgentType.WORKER,
        dna=dna,
        manifest_name="defaults"
    )

    assert violations == []


def test_locked_field_mutation_detected(enforcer):
    """Test 2: Mutating human_override should be detected."""
    dna = {"ethics_flags.human_override": "never"}  # Locked to "always_allowed"

    with pytest.raises(PolicyViolationError) as exc_info:
        enforcer.validate_dna_against_locks(
            agent_type=AgentType.WORKER,
            dna=dna,
            manifest_name="defaults"
        )

    assert len(exc_info.value.violations) == 1
    violation = exc_info.value.violations[0]
    assert violation.field_path == "ethics_flags.human_override"
    assert violation.locked_value == "always_allowed"
    assert violation.attempted_value == "never"


def test_multiple_violations(enforcer):
    """Test 3: Multiple locked field mutations should all be detected."""
    dna = {
        "ethics_flags.human_override": "never",
        "capabilities.can_modify_governor": True
    }

    with pytest.raises(PolicyViolationError) as exc_info:
        enforcer.validate_dna_against_locks(
            agent_type=AgentType.WORKER,
            dna=dna,
            manifest_name="defaults"
        )

    assert len(exc_info.value.violations) == 2

    field_paths = [v.field_path for v in exc_info.value.violations]
    assert "ethics_flags.human_override" in field_paths
    assert "capabilities.can_modify_governor" in field_paths


def test_genesis_exception_can_create_agents(enforcer):
    """Test 4: Genesis role should be allowed to have can_create_agents=true."""
    dna = {"capabilities.can_create_agents": True}

    # Should NOT raise for Genesis
    violations = enforcer.validate_dna_against_locks(
        agent_type=AgentType.GENESIS,
        dna=dna,
        manifest_name="defaults"
    )
    assert violations == []

    # Should raise for Worker
    with pytest.raises(PolicyViolationError):
        enforcer.validate_dna_against_locks(
            agent_type=AgentType.WORKER,
            dna=dna,
            manifest_name="defaults"
        )


def test_nested_field_path_resolution(enforcer):
    """Test 5: Dot notation paths should resolve correctly."""
    # Test _get_nested_value helper
    obj = {"ethics_flags": {"human_override": "always_allowed"}}
    value = enforcer._get_nested_value(obj, "ethics_flags.human_override")
    assert value == "always_allowed"


def test_dna_matches_locked_value(enforcer):
    """Test 6: DNA value matching locked value should pass."""
    dna = {"ethics_flags.human_override": "always_allowed"}  # Matches locked value

    violations = enforcer.validate_dna_against_locks(
        agent_type=AgentType.WORKER,
        dna=dna,
        manifest_name="defaults"
    )
    assert violations == []


def test_flatten_dict(enforcer):
    """Test 7: Nested dict should be flattened correctly."""
    nested = {
        "ethics_flags": {
            "human_override": "always_allowed"
        },
        "capabilities": {
            "can_create_agents": False
        }
    }

    flattened = enforcer._flatten_dict(nested)

    assert flattened["ethics_flags.human_override"] == "always_allowed"
    assert flattened["capabilities.can_create_agents"] == False


def test_invalid_field_path_graceful_handling(enforcer):
    """Test 8: Invalid field paths should be handled gracefully."""
    dna = {"nonexistent.field": "value"}

    # Should not raise, just skip validation for unknown fields
    violations = enforcer.validate_dna_against_locks(
        agent_type=AgentType.WORKER,
        dna=dna,
        manifest_name="defaults"
    )
    assert violations == []


def test_can_modify_governor_locked(enforcer):
    """Test 9: can_modify_governor field should be locked."""
    dna = {"capabilities.can_modify_governor": True}

    with pytest.raises(PolicyViolationError) as exc_info:
        enforcer.validate_dna_against_locks(
            agent_type=AgentType.WORKER,
            dna=dna,
            manifest_name="defaults"
        )

    assert len(exc_info.value.violations) == 1
    assert exc_info.value.violations[0].field_path == "capabilities.can_modify_governor"


def test_supervisor_cannot_create_agents(enforcer):
    """Test 10: Supervisor role cannot have can_create_agents=true."""
    dna = {"capabilities.can_create_agents": True}

    with pytest.raises(PolicyViolationError):
        enforcer.validate_dna_against_locks(
            agent_type=AgentType.SUPERVISOR,
            dna=dna,
            manifest_name="defaults"
        )


# ============================================================================
# Integration Tests: Governor Integration
# ============================================================================

@pytest.mark.asyncio
async def test_governor_blocks_locked_mutation():
    """Test 11: Governor.evaluate_creation should block locked field mutations."""
    # Create mock dependencies
    redis_mock = AsyncMock()
    audit_mock = Mock()
    audit_mock.log = AsyncMock()

    governor = Governor(
        redis_client=redis_mock,
        audit_log=audit_mock,
        available_credits=10000
    )

    # Create request with locked field mutation
    request = DecisionRequest(
        request_id="req_test_001",
        actor=ActorContext(
            user_id="admin",
            role="SYSTEM_ADMIN",
            source="test"
        ),
        agent_dna={
            "metadata": {"type": "worker"},
            "ethics_flags": {"human_override": "never"},  # LOCKED VIOLATION
            "budget": {}
        },
        dna_hash="sha256:test",
        template_name="worker_base",
        template_hash="sha256:template",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["ethics_flags.human_override"]
        )
    )

    # Execute evaluation
    result = await governor.evaluate_creation(request)

    # Should be rejected
    assert result.approved == False
    assert result.reason_code == ReasonCode.REJECTED_LOCKED_FIELD_VIOLATION
    assert "Locked field violation" in result.reason_detail


@pytest.mark.asyncio
async def test_violation_event_emitted():
    """Test 12: Locked field violation should emit event."""
    redis_mock = AsyncMock()
    audit_mock = Mock()
    audit_mock.log = AsyncMock()

    governor = Governor(
        redis_client=redis_mock,
        audit_log=audit_mock,
        available_credits=10000
    )

    request = DecisionRequest(
        request_id="req_test_002",
        actor=ActorContext(
            user_id="admin",
            role="SYSTEM_ADMIN",
            source="test"
        ),
        agent_dna={
            "metadata": {"type": "worker"},
            "ethics_flags": {"human_override": "never"}
        },
        dna_hash="sha256:test",
        template_name="worker_base",
        template_hash="sha256:template",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["ethics_flags.human_override"]
        )
    )

    await governor.evaluate_creation(request)

    # Check that audit log was called with locked_field_violation event
    audit_calls = [call for call in audit_mock.log.call_args_list
                   if len(call[1]) > 0 and call[1].get('event_type') == 'governance.locked_field_violation']

    assert len(audit_calls) > 0, "Expected locked_field_violation event to be emitted"


@pytest.mark.asyncio
async def test_valid_creation_still_works():
    """Test 13: Valid DNA should still allow creation."""
    redis_mock = AsyncMock()
    audit_mock = Mock()
    audit_mock.log = AsyncMock()

    governor = Governor(
        redis_client=redis_mock,
        audit_log=audit_mock,
        available_credits=10000
    )

    # Valid DNA with non-locked field customization
    request = DecisionRequest(
        request_id="req_test_003",
        actor=ActorContext(
            user_id="admin",
            role="SYSTEM_ADMIN",
            source="test"
        ),
        agent_dna={
            "metadata": {"type": "worker"},
            "budget": {"max_llm_tokens": 3000}  # Non-locked field
        },
        dna_hash="sha256:test",
        template_name="worker_base",
        template_hash="sha256:template",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["budget.max_llm_tokens"]
        )
    )

    result = await governor.evaluate_creation(request)

    assert result.approved == True


@pytest.mark.asyncio
async def test_genesis_creation_with_agent_capability():
    """Test 14: Genesis agent with can_create_agents=true should succeed."""
    redis_mock = AsyncMock()
    audit_mock = Mock()
    audit_mock.log = AsyncMock()

    governor = Governor(
        redis_client=redis_mock,
        audit_log=audit_mock,
        available_credits=10000
    )

    request = DecisionRequest(
        request_id="req_test_004",
        actor=ActorContext(
            user_id="admin",
            role="SYSTEM_ADMIN",
            source="test"
        ),
        agent_dna={
            "metadata": {"type": "genesis"},
            "capabilities": {"can_create_agents": True}  # Genesis exception
        },
        dna_hash="sha256:test",
        template_name="genesis_base",
        template_hash="sha256:template",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["capabilities.can_create_agents"]
        )
    )

    result = await governor.evaluate_creation(request)

    assert result.approved == True


@pytest.mark.asyncio
async def test_no_customizations_skips_validation():
    """Test 15: Requests without customizations should skip locked field validation."""
    redis_mock = AsyncMock()
    audit_mock = Mock()
    audit_mock.log = AsyncMock()

    governor = Governor(
        redis_client=redis_mock,
        audit_log=audit_mock,
        available_credits=10000
    )

    request = DecisionRequest(
        request_id="req_test_005",
        actor=ActorContext(
            user_id="admin",
            role="SYSTEM_ADMIN",
            source="test"
        ),
        agent_dna={
            "metadata": {"type": "worker"},
            "budget": {}
        },
        dna_hash="sha256:test",
        template_name="worker_base",
        template_hash="sha256:template",
        context=RequestContext(
            has_customizations=False  # No customizations
        )
    )

    result = await governor.evaluate_creation(request)

    # Should pass without locked field validation
    assert result.approved == True


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_string_agent_type_conversion(enforcer):
    """Test 16: String agent type should be converted to AgentType enum."""
    dna = {"ethics_flags.human_override": "never"}

    with pytest.raises(PolicyViolationError):
        enforcer.validate_dna_against_locks(
            agent_type="worker",  # String instead of enum
            dna=dna,
            manifest_name="defaults"
        )


def test_unknown_agent_type_raises_error(enforcer):
    """Test 17: Unknown agent type should raise ValueError."""
    dna = {"ethics_flags.human_override": "never"}

    with pytest.raises(ValueError, match="Unknown agent type"):
        enforcer.validate_dna_against_locks(
            agent_type="unknown_type",
            dna=dna,
            manifest_name="defaults"
        )


def test_dna_hash_computation(enforcer):
    """Test 18: DNA hash should be deterministic."""
    dna = {"ethics_flags": {"human_override": "never"}}

    hash1 = enforcer.get_dna_hash(dna)
    hash2 = enforcer.get_dna_hash(dna)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA256 hex digest length


# ============================================================================
# Performance Test
# ============================================================================

def test_validation_performance(enforcer):
    """Test 19: Validation should complete quickly (<10ms per validation)."""
    dna = {"budget.max_llm_tokens": 5000}

    start = time.time()
    for _ in range(100):
        enforcer.validate_dna_against_locks(
            agent_type=AgentType.WORKER,
            dna=dna,
            manifest_name="defaults"
        )
    duration = time.time() - start

    # 100 validations should complete in less than 1 second
    assert duration < 1.0, f"Validation too slow: {duration}s for 100 iterations"


# ============================================================================
# Test Summary
# ============================================================================

"""
Test Coverage Summary:

Unit Tests (10):
1. test_valid_dna_no_mutations - Valid DNA passes
2. test_locked_field_mutation_detected - Single violation detected
3. test_multiple_violations - Multiple violations detected
4. test_genesis_exception_can_create_agents - Genesis exception works
5. test_nested_field_path_resolution - Dot notation works
6. test_dna_matches_locked_value - Matching locked value passes
7. test_flatten_dict - Dict flattening works
8. test_invalid_field_path_graceful_handling - Unknown fields ignored
9. test_can_modify_governor_locked - can_modify_governor locked
10. test_supervisor_cannot_create_agents - Supervisor restriction

Integration Tests (5):
11. test_governor_blocks_locked_mutation - Governor blocks violations
12. test_violation_event_emitted - Events emitted correctly
13. test_valid_creation_still_works - Valid creation succeeds
14. test_genesis_creation_with_agent_capability - Genesis exception works
15. test_no_customizations_skips_validation - No customizations skips validation

Edge Cases (4):
16. test_string_agent_type_conversion - String type conversion
17. test_unknown_agent_type_raises_error - Unknown type error
18. test_dna_hash_computation - Hash determinism
19. test_validation_performance - Performance check

Total: 19 tests
Target Coverage: >95%
"""
