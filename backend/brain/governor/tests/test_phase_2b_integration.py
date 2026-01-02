"""
Integration Tests for Phase 2b (Governor v1 + Reductions)

Tests the complete flow: Manifest → Reductions → Events → Constraints

Test Scenarios:
1. Approve with reductions (customizations present)
2. Approve with risk tier override from manifest
3. Multiple reduction sections applied incrementally
4. Manifest events emitted correctly
5. Reduction monotonicity in practice
6. Locked fields enforcement (future)

Author: Governor v1 System
Version: 2b.1
Created: 2026-01-02
"""

import pytest
import redis.asyncio as redis

from backend.brain.agents.genesis_agent.dna_schema import AgentType
from backend.brain.agents.genesis_agent.events import SimpleAuditLog
from backend.brain.governor import (
    ActorContext,
    DecisionRequest,
    Governor,
    GovernorConfig,
    RequestContext,
)
from backend.brain.governor.decision.models import DecisionType, ReasonCode, RiskTier
from backend.brain.governor.manifests.schema import (
    AppliesToSpec,
    GovernanceManifest,
    LockSpec,
    ReductionSections,
    ReductionSpec,
    RiskOverride,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    client = redis.from_url("redis://localhost:6379/15", decode_responses=False)
    yield client
    await client.flushdb()
    await client.aclose()


@pytest.fixture
def audit_log():
    """Create simple audit log for testing."""
    return SimpleAuditLog()


@pytest.fixture
def governor_config():
    """Create Governor config for testing."""
    return GovernorConfig(
        policy_version="2b.1",
        ruleset_version="2b",
        template_allowlist=["worker_base", "analyst_base"],
        reserve_ratio=0.2,
        max_population={
            AgentType.GENESIS: 1,
            AgentType.WORKER: 50
        }
    )


@pytest.fixture
def test_manifest():
    """
    Create test manifest with reductions.

    Reductions:
    - on_customization: -30% LLM calls, -50% parallelism
    - on_high_risk: disable network, cap at 50 credits
    """
    return GovernanceManifest(
        manifest_version=1,
        policy_version="2b.1",
        name="test_manifest",
        description="Test manifest for Phase 2b integration tests",
        applies_to=AppliesToSpec(),  # Apply to all
        reductions=ReductionSections(
            on_customization=ReductionSpec(
                max_llm_calls_per_day="-30%",
                parallelism="-50%"
            ),
            on_high_risk=ReductionSpec(
                network_access="disable",
                max_credits_per_mission="50"
            )
        ),
        risk_overrides=RiskOverride(
            if_customizations="MEDIUM"
        ),
        locks=LockSpec(
            locked_fields=["ethics_flags.human_override"]
        )
    )


@pytest.fixture
async def governor(redis_client, audit_log, governor_config, test_manifest):
    """Create Governor instance with test manifest."""
    return Governor(
        redis_client=redis_client,
        audit_log=audit_log,
        config=governor_config,
        killswitch_active=False,
        available_credits=10000,
        population_counts={},
        manifest=test_manifest
    )


# ============================================================================
# Integration Test: Approve with Customization Reductions
# ============================================================================

@pytest.mark.asyncio
async def test_approve_with_customization_reductions(governor, redis_client, audit_log):
    """
    Test approve path with customization reductions applied.

    Flow:
    1. Create DecisionRequest with customizations
    2. Governor evaluates → APPROVE_WITH_CONSTRAINTS
    3. on_customization reduction applied (-30% LLM calls, -50% parallelism)
    4. Risk tier elevated to MEDIUM (manifest override)
    5. Events emitted: constraints.reduced, manifest.applied
    6. Constraints returned with reductions
    """
    # Build request
    dna_dict = {
        "metadata": {
            "id": "agent-custom-01",
            "name": "worker_custom_test",
            "type": "Worker",
            "version": "1.0.0",
            "dna_schema_version": "2.0",
            "template_hash": "sha256:abc123",
            "template_version": "1.0",
            "created_by": "genesis_agent"
        },
        "traits": {
            "base_type": "Worker",
            "primary_function": "task_execution",
            "autonomy_level": 2
        },
        "ethics_flags": {
            "human_override": "always_allowed"
        },
        "capabilities": {
            "network_access": "restricted"
        }
    }

    request = DecisionRequest(
        request_id="req-custom-01",
        actor=ActorContext(
            user_id="admin-001",
            role="SYSTEM_ADMIN",
            source="genesis_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash_custom_01",
        template_name="worker_base",
        template_hash="sha256:abc123",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["metadata.name"]  # Customization present
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions: Decision
    assert result.approved is True
    assert result.decision_type == DecisionType.APPROVE_WITH_CONSTRAINTS
    assert result.reason_code == ReasonCode.APPROVED_WITH_CONSTRAINTS
    assert result.risk_tier == RiskTier.MEDIUM  # Manifest override
    assert result.quarantine is False

    # Assertions: Constraints reduced
    assert result.constraints is not None
    constraints = result.constraints

    # Worker base: 1000 LLM calls/day → 700 after -30%
    assert constraints["budget"]["max_llm_calls_per_day"] == 700

    # Worker base: 10 parallelism → 5 after -50%
    assert constraints["runtime"]["parallelism"] == 5

    # Other constraints unchanged
    assert constraints["budget"]["max_credits_per_mission"] == 100  # Worker default
    assert constraints["capabilities"]["network_access"] == "restricted"  # Unchanged

    # Assertions: Events emitted
    events = audit_log.get_events()
    event_types = [e["event_type"] for e in events]

    assert "governor.decision.requested" in event_types
    assert "governor.decision.evaluated" in event_types
    assert "governor.constraints.reduced" in event_types  # Phase 2b event
    assert "governor.manifest.applied" in event_types      # Phase 2b event
    assert "governor.decision.approved" in event_types

    # Find constraints.reduced event
    reduced_event = next(e for e in events if e["event_type"] == "governor.constraints.reduced")
    assert reduced_event["payload"]["applied_reductions"] == ["on_customization"]
    assert "max_llm_calls_per_day" in reduced_event["payload"]["reduction_summary"]
    assert "parallelism" in reduced_event["payload"]["reduction_summary"]

    # Find manifest.applied event
    manifest_event = next(e for e in events if e["event_type"] == "governor.manifest.applied")
    assert manifest_event["payload"]["manifest_name"] == "test_manifest"
    assert manifest_event["payload"]["policy_version"] == "2b.1"
    assert manifest_event["payload"]["applicable_sections"] == ["on_customization"]


# ============================================================================
# Integration Test: Multiple Reduction Sections
# ============================================================================

@pytest.mark.asyncio
async def test_multiple_reduction_sections(redis_client, audit_log, governor_config):
    """
    Test multiple reduction sections applied incrementally.

    Flow:
    1. Create DecisionRequest with customizations + HIGH risk conditions
    2. Both on_customization AND on_high_risk reductions apply
    3. Reductions applied incrementally (on_customization first, then on_high_risk)
    4. Final constraints are cumulative effect of both
    """
    # Create manifest with both reduction sections
    manifest = GovernanceManifest(
        manifest_version=1,
        policy_version="2b.1",
        name="multi_reduction",
        description="Multiple reductions test",
        applies_to=AppliesToSpec(),
        reductions=ReductionSections(
            on_customization=ReductionSpec(
                max_llm_calls_per_day="-30%"  # 1000 → 700
            ),
            on_high_risk=ReductionSpec(
                max_llm_calls_per_day="-50%",  # 700 → 350 (of already-reduced)
                network_access="disable"
            )
        ),
        risk_overrides=RiskOverride(
            if_customizations="HIGH"  # Force HIGH risk
        ),
        locks=LockSpec()
    )

    governor = Governor(
        redis_client=redis_client,
        audit_log=audit_log,
        config=governor_config,
        manifest=manifest
    )

    # Build request (customizations present → triggers both reductions)
    dna_dict = {
        "metadata": {
            "id": "agent-multi-01",
            "name": "worker_multi",
            "type": "Worker",
            "version": "1.0.0",
            "dna_schema_version": "2.0",
            "template_hash": "sha256:multi123",
            "template_version": "1.0",
            "created_by": "genesis_agent"
        },
        "traits": {
            "base_type": "Worker",
            "primary_function": "task_execution",
            "autonomy_level": 2
        },
        "ethics_flags": {
            "human_override": "always_allowed"
        },
        "capabilities": {
            "network_access": "restricted"
        }
    }

    request = DecisionRequest(
        request_id="req-multi-01",
        actor=ActorContext(
            user_id="admin-001",
            role="SYSTEM_ADMIN",
            source="genesis_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash_multi_01",
        template_name="worker_base",
        template_hash="sha256:multi123",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["metadata.name"]
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions
    assert result.approved is True
    assert result.risk_tier == RiskTier.HIGH  # Manifest override

    # Constraints after both reductions
    constraints = result.constraints

    # max_llm_calls_per_day:
    # Base: 1000
    # After on_customization (-30%): 700
    # After on_high_risk (-50% of 700): 350
    assert constraints["budget"]["max_llm_calls_per_day"] == 350

    # network_access: restricted → none (disabled by on_high_risk)
    assert constraints["capabilities"]["network_access"] == "none"

    # Events
    events = audit_log.get_events()
    reduced_event = next(e for e in events if e["event_type"] == "governor.constraints.reduced")

    # Both reduction sections applied
    assert set(reduced_event["payload"]["applied_reductions"]) == {"on_customization", "on_high_risk"}


# ============================================================================
# Integration Test: No Reductions (No Customizations)
# ============================================================================

@pytest.mark.asyncio
async def test_no_reductions_no_customizations(governor, redis_client, audit_log):
    """
    Test that no reductions apply when there are no customizations.

    Flow:
    1. Create DecisionRequest WITHOUT customizations
    2. Governor evaluates → APPROVE (not APPROVE_WITH_CONSTRAINTS)
    3. No reductions apply (base constraints returned)
    4. Risk tier remains LOW
    5. constraints.reduced event NOT emitted (no reductions)
    6. manifest.applied event still emitted (manifest was checked)
    """
    dna_dict = {
        "metadata": {
            "id": "agent-no-custom-01",
            "name": "worker_base_test",
            "type": "Worker",
            "version": "1.0.0",
            "dna_schema_version": "2.0",
            "template_hash": "sha256:base123",
            "template_version": "1.0",
            "created_by": "genesis_agent"
        },
        "traits": {
            "base_type": "Worker",
            "primary_function": "task_execution",
            "autonomy_level": 2
        },
        "ethics_flags": {
            "human_override": "always_allowed"
        },
        "capabilities": {
            "network_access": "restricted"
        }
    }

    request = DecisionRequest(
        request_id="req-no-custom-01",
        actor=ActorContext(
            user_id="admin-001",
            role="SYSTEM_ADMIN",
            source="genesis_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash_no_custom_01",
        template_name="worker_base",
        template_hash="sha256:base123",
        context=RequestContext(
            has_customizations=False,  # No customizations
            customization_fields=[]
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions
    assert result.approved is True
    assert result.decision_type == DecisionType.APPROVE  # NOT approve_with_constraints
    assert result.risk_tier == RiskTier.LOW  # No customizations → LOW risk
    assert result.constraints is not None

    # Constraints should be base defaults (no reductions)
    constraints = result.constraints
    assert constraints["budget"]["max_llm_calls_per_day"] == 1000  # Worker base (unreduced)
    assert constraints["runtime"]["parallelism"] == 10  # Worker base (unreduced)

    # Events
    events = audit_log.get_events()
    event_types = [e["event_type"] for e in events]

    # constraints.reduced should NOT be emitted (no reductions applied)
    assert "governor.constraints.reduced" not in event_types

    # manifest.applied should still be emitted (manifest was loaded and checked)
    assert "governor.manifest.applied" in event_types


# ============================================================================
# Integration Test: Rejection Path (No Reductions)
# ============================================================================

@pytest.mark.asyncio
async def test_rejection_no_reductions(governor, redis_client, audit_log):
    """
    Test that reductions are NOT applied when decision is rejected.

    Flow:
    1. Create DecisionRequest with unauthorized role
    2. Governor evaluates → REJECT (Rule A1)
    3. No reductions applied (decision rejected before constraint application)
    4. No constraints returned
    5. No constraints.reduced or manifest.applied events
    """
    dna_dict = {
        "metadata": {
            "id": "agent-reject-01",
            "name": "worker_reject",
            "type": "Worker",
            "version": "1.0.0",
            "dna_schema_version": "2.0",
            "template_hash": "sha256:reject123",
            "template_version": "1.0",
            "created_by": "genesis_agent"
        },
        "traits": {
            "base_type": "Worker",
            "primary_function": "task_execution",
            "autonomy_level": 2
        },
        "ethics_flags": {
            "human_override": "always_allowed"
        },
        "capabilities": {
            "network_access": "restricted"
        }
    }

    request = DecisionRequest(
        request_id="req-reject-01",
        actor=ActorContext(
            user_id="user-001",
            role="USER",  # NOT SYSTEM_ADMIN → rejection
            source="user_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash_reject_01",
        template_name="worker_base",
        template_hash="sha256:reject123",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["metadata.name"]
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions
    assert result.approved is False
    assert result.decision_type == DecisionType.REJECT
    assert result.reason_code == ReasonCode.UNAUTHORIZED_ROLE
    assert result.constraints is None  # No constraints on rejection

    # Events
    events = audit_log.get_events()
    event_types = [e["event_type"] for e in events]

    assert "governor.decision.rejected" in event_types
    assert "governor.constraints.reduced" not in event_types  # No reductions on reject
    assert "governor.manifest.applied" not in event_types     # No manifest application on reject
