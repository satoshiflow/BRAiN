"""
Integration Tests for Governor v1 (Phase 2a)

Tests the complete flow: Genesis → Governor → Registry

Test Scenarios:
1. Approve path (default constraints)
2. Approve path (with constraints)
3. Reject path (unauthorized role)
4. Reject path (capability escalation)
5. Quarantine path (critical agent)

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-02
"""

import pytest
import redis.asyncio as redis

from brain.agents.genesis_agent.dna_schema import AgentDNA, AgentType
from brain.agents.genesis_agent.events import SimpleAuditLog
from brain.governor import (
    ActorContext,
    DecisionRequest,
    Governor,
    GovernorApproval,
    GovernorConfig,
    RequestContext,
)
from brain.governor.decision.models import DecisionType, ReasonCode, RiskTier


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
        policy_version="1.0.0",
        ruleset_version="2a",
        template_allowlist=["worker_base", "analyst_base"],
        reserve_ratio=0.2,
        max_population={
            AgentType.GENESIS: 1,
            AgentType.WORKER: 50
        }
    )


@pytest.fixture
async def governor(redis_client, audit_log, governor_config):
    """Create Governor instance for testing."""
    return Governor(
        redis_client=redis_client,
        audit_log=audit_log,
        config=governor_config,
        killswitch_active=False,
        available_credits=10000,
        population_counts={}
    )


# ============================================================================
# Integration Test: Approve Path (Default Constraints)
# ============================================================================

@pytest.mark.asyncio
async def test_approve_path_default_constraints(governor, redis_client, audit_log):
    """
    Test approve path with default constraints.

    Flow:
    1. Create DecisionRequest (no customizations)
    2. Governor evaluates → APPROVE
    3. Default constraints applied
    4. Events emitted (decision.requested, decision.evaluated, decision.approved)
    """
    # Build request
    dna_dict = {
        "metadata": {
            "id": "agent-123",
            "name": "worker_test_01",
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
        request_id="req-123",
        actor=ActorContext(
            user_id="admin-001",
            role="SYSTEM_ADMIN",
            source="genesis_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash123",
        template_name="worker_base",
        template_hash="sha256:abc123",
        context=RequestContext(
            has_customizations=False,
            customization_fields=[]
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions
    assert result.approved is True
    assert result.decision_type == DecisionType.APPROVE
    assert result.reason_code == ReasonCode.APPROVED_DEFAULT
    assert result.risk_tier == RiskTier.LOW
    assert result.quarantine is False
    assert result.constraints is not None
    assert result.policy_version == "1.0.0"
    assert result.ruleset_version == "2a"

    # Check constraints applied
    assert "budget" in result.constraints
    assert result.constraints["budget"]["max_credits_per_mission"] == 100  # Worker default

    # Check events
    events = audit_log.get_events()
    event_types = [e["event_type"] for e in events]
    assert "governor.decision.requested" in event_types
    assert "governor.decision.evaluated" in event_types
    assert "governor.decision.approved" in event_types


# ============================================================================
# Integration Test: Approve Path (With Constraints)
# ============================================================================

@pytest.mark.asyncio
async def test_approve_path_with_constraints(governor, redis_client, audit_log):
    """
    Test approve path with customizations (constraints applied).

    Flow:
    1. Create DecisionRequest (with customizations)
    2. Governor evaluates → APPROVE_WITH_CONSTRAINTS
    3. Risk tier elevated to MEDIUM
    4. Constraints applied
    """
    dna_dict = {
        "metadata": {
            "id": "agent-456",
            "name": "worker_custom_01",
            "type": "Worker",
            "version": "1.0.0",
            "dna_schema_version": "2.0",
            "template_hash": "sha256:def456",
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
        request_id="req-456",
        actor=ActorContext(
            user_id="admin-001",
            role="SYSTEM_ADMIN",
            source="genesis_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash456",
        template_name="worker_base",
        template_hash="sha256:def456",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["metadata.name"]
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions
    assert result.approved is True
    assert result.decision_type == DecisionType.APPROVE_WITH_CONSTRAINTS
    assert result.reason_code == ReasonCode.APPROVED_WITH_CONSTRAINTS
    assert result.risk_tier == RiskTier.MEDIUM  # Elevated due to customizations
    assert result.quarantine is False
    assert result.constraints is not None


# ============================================================================
# Integration Test: Reject Path (Unauthorized Role)
# ============================================================================

@pytest.mark.asyncio
async def test_reject_path_unauthorized_role(governor, redis_client, audit_log):
    """
    Test reject path due to unauthorized role.

    Flow:
    1. Create DecisionRequest (role != SYSTEM_ADMIN)
    2. Governor evaluates → REJECT (Rule A1)
    3. Reason code: UNAUTHORIZED_ROLE
    """
    dna_dict = {
        "metadata": {
            "id": "agent-789",
            "name": "worker_unauth_01",
            "type": "Worker",
            "version": "1.0.0",
            "dna_schema_version": "2.0",
            "template_hash": "sha256:ghi789",
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
        request_id="req-789",
        actor=ActorContext(
            user_id="user-001",
            role="USER",  # NOT SYSTEM_ADMIN
            source="user_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash789",
        template_name="worker_base",
        template_hash="sha256:ghi789",
        context=RequestContext(
            has_customizations=False,
            customization_fields=[]
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions
    assert result.approved is False
    assert result.decision_type == DecisionType.REJECT
    assert result.reason_code == ReasonCode.UNAUTHORIZED_ROLE
    assert "SYSTEM_ADMIN" in result.reason_detail
    assert result.constraints is None  # No constraints on rejection
    assert "A1" in result.triggered_rules

    # Check events
    events = audit_log.get_events()
    event_types = [e["event_type"] for e in events]
    assert "governor.decision.rejected" in event_types


# ============================================================================
# Integration Test: Reject Path (Capability Escalation)
# ============================================================================

@pytest.mark.asyncio
async def test_reject_path_capability_escalation(governor, redis_client, audit_log):
    """
    Test reject path due to capability escalation.

    Flow:
    1. Create DecisionRequest (customization: capabilities.network_access)
    2. Governor evaluates → REJECT (Rule E3)
    3. Reason code: CAPABILITY_ESCALATION_DENIED
    """
    dna_dict = {
        "metadata": {
            "id": "agent-999",
            "name": "worker_escalate_01",
            "type": "Worker",
            "version": "1.0.0",
            "dna_schema_version": "2.0",
            "template_hash": "sha256:jkl999",
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
            "network_access": "full"  # Escalation attempt
        }
    }

    request = DecisionRequest(
        request_id="req-999",
        actor=ActorContext(
            user_id="admin-001",
            role="SYSTEM_ADMIN",
            source="genesis_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash999",
        template_name="worker_base",
        template_hash="sha256:jkl999",
        context=RequestContext(
            has_customizations=True,
            customization_fields=["capabilities.network_access"]  # Forbidden
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions
    assert result.approved is False
    assert result.decision_type == DecisionType.REJECT
    assert result.reason_code == ReasonCode.CAPABILITY_ESCALATION_DENIED
    assert "capabilities.network_access" in result.reason_detail
    assert "E3" in result.triggered_rules


# ============================================================================
# Integration Test: Quarantine Path (Critical Agent)
# ============================================================================

@pytest.mark.asyncio
async def test_quarantine_path_critical_agent(governor, redis_client, audit_log):
    """
    Test quarantine path for CRITICAL agent (Genesis).

    Flow:
    1. Create DecisionRequest (AgentType.GENESIS)
    2. Governor evaluates → APPROVE_WITH_CONSTRAINTS
    3. Risk tier: CRITICAL
    4. Quarantine: True
    """
    dna_dict = {
        "metadata": {
            "id": "agent-critical-01",
            "name": "genesis_agent_01",
            "type": "Genesis",
            "version": "1.0.0",
            "dna_schema_version": "2.0",
            "template_hash": "sha256:critical123",
            "template_version": "1.0",
            "created_by": "genesis_agent"
        },
        "traits": {
            "base_type": "Genesis",
            "primary_function": "agent_creation",
            "autonomy_level": 5
        },
        "ethics_flags": {
            "human_override": "always_allowed"
        },
        "capabilities": {
            "network_access": "full"
        }
    }

    request = DecisionRequest(
        request_id="req-critical-01",
        actor=ActorContext(
            user_id="admin-001",
            role="SYSTEM_ADMIN",
            source="genesis_api"
        ),
        agent_dna=dna_dict,
        dna_hash="hash_critical_01",
        template_name="genesis_base",
        template_hash="sha256:critical123",
        context=RequestContext(
            has_customizations=False,
            customization_fields=[]
        )
    )

    # Execute
    result = await governor.evaluate_creation(request)

    # Assertions
    assert result.approved is True  # Approved BUT quarantined
    assert result.risk_tier == RiskTier.CRITICAL
    assert result.quarantine is True
    assert result.constraints is not None
    assert result.constraints["lifecycle"]["initial_status"] == "QUARANTINED"


# ============================================================================
# Integration Test: GovernorApproval Wrapper
# ============================================================================

@pytest.mark.asyncio
async def test_governor_approval_wrapper(redis_client, audit_log):
    """
    Test GovernorApproval wrapper (Genesis compatibility).

    Flow:
    1. Create AgentDNA
    2. Call GovernorApproval.request_approval()
    3. Verify response matches Genesis protocol
    """
    from brain.agents.genesis_agent.dna_schema import (
        AgentDNA,
        AgentType,
        DNAMetadata,
        AgentTraits,
        BehaviorModules,
        EthicsFlags,
        Capabilities,
        RuntimeConfig,
        ResourceLimits,
        MissionAffinity,
    )

    # Create AgentDNA
    dna = AgentDNA(
        metadata=DNAMetadata(
            name="worker_wrapper_test_01",
            type=AgentType.WORKER,
            dna_schema_version="2.0",
            template_hash="sha256:wrapper123",
            template_version="1.0"
        ),
        traits=AgentTraits(
            base_type=AgentType.WORKER,
            primary_function="task_execution",
            autonomy_level=2
        ),
        behavior_modules=BehaviorModules(
            communication_style="concise",
            decision_making="rule_based",
            collaboration_preference="sync",
            error_handling="retry_with_backoff"
        ),
        ethics_flags=EthicsFlags(),
        capabilities=Capabilities(
            network_access="restricted"
        ),
        runtime=RuntimeConfig(),
        resource_limits=ResourceLimits(),
        mission_affinity=MissionAffinity()
    )

    # Create GovernorApproval wrapper
    governor_approval = GovernorApproval(
        redis_client=redis_client,
        audit_log=audit_log
    )

    # Request approval
    response = await governor_approval.request_approval(dna)

    # Assertions
    assert response.approved is True
    assert isinstance(response.reason, str)
    assert len(response.reason) > 0
