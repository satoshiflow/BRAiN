"""
Tests for Genesis Agent Core

This module tests the Genesis Agent core functionality including:
- Agent creation workflow
- Idempotency
- Event emission
- Budget enforcement
- Template loading

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

import pytest
from pathlib import Path

from brain.agents.genesis_agent.genesis_agent import (
    GenesisAgent,
    InMemoryRegistry,
    InMemoryBudget,
)
from brain.agents.genesis_agent.events import SimpleAuditLog
from brain.agents.genesis_agent.config import GenesisSettings, reset_genesis_settings
from brain.agents.genesis_agent.dna_validator import ValidationError


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def templates_dir(tmp_path):
    """Create temporary templates directory with worker template."""
    templates = tmp_path / "templates"
    templates.mkdir()

    template_content = """
agent_dna:
  metadata:
    name: "worker_generic"
    type: "Worker"
    version: "1.0.0"
    template_version: "1.0"
    parent_id: null

  traits:
    base_type: "Worker"
    primary_function: "task_execution"
    autonomy_level: 2

  skills:
    - skill_id: "api_calls"
      proficiency: 0.80
      domains: ["rest"]

  behavior_modules:
    communication_style: "concise"
    decision_making: "rule_based"
    collaboration_preference: "sync"
    error_handling: "retry_with_backoff"

  ethics_flags:
    data_privacy: "standard"
    transparency: "basic_audit"
    bias_awareness: "enabled"
    human_override: "always_allowed"

  capabilities:
    tools_allowed: ["api_call"]
    connectors_allowed: []
    network_access: "restricted"

  runtime:
    model_policy: "cheap"
    temperature_cap: 0.5
    max_tokens_cap: 1000
    allowed_models: ["llama3-8b-instruct-q4"]

  memory_seeds:
    - "Task execution best practices"

  resource_limits:
    max_credits_per_mission: 50
    max_llm_calls_per_day: 200
    timeout_seconds: 180

  mission_affinity:
    preferred_types: ["execution"]
    required_context: ["api_endpoint"]
"""
    (templates / "worker_base.yaml").write_text(template_content)
    return templates


@pytest.fixture
async def genesis_agent(templates_dir):
    """Create Genesis Agent instance."""
    # Create mock Redis client
    class MockRedis:
        async def publish(self, channel, message):
            pass

    registry = InMemoryRegistry()
    budget = InMemoryBudget(initial_credits=1000)
    audit_log = SimpleAuditLog()
    redis_client = MockRedis()

    # Reset settings and configure
    reset_genesis_settings()
    settings = GenesisSettings(
        enabled=True,
        templates_dir=str(templates_dir),
        reserve_ratio=0.2
    )

    genesis = GenesisAgent(
        registry=registry,
        redis_client=redis_client,
        audit_log=audit_log,
        budget=budget,
        settings=settings
    )

    return genesis


# ============================================================================
# Agent Creation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_create_agent_success(genesis_agent):
    """Test successful agent creation from template."""
    dna = await genesis_agent.create_agent(
        request_id="test-001",
        template_name="worker_base",
        customizations=None
    )

    # Verify DNA structure
    assert dna.metadata.type.value == "Worker"
    assert dna.metadata.name == "worker_generic"
    assert dna.metadata.dna_schema_version == "2.0"
    assert dna.metadata.template_hash.startswith("sha256:")
    assert dna.metadata.created_by == "genesis_agent"

    # Verify ethics immutability
    assert dna.ethics_flags.human_override == "always_allowed"


@pytest.mark.asyncio
async def test_create_agent_with_customizations(genesis_agent):
    """Test agent creation with customizations."""
    dna = await genesis_agent.create_agent(
        request_id="test-002",
        template_name="worker_base",
        customizations={
            "metadata.name": "worker_specialized_01",
            "skills[].domains": ["graphql", "grpc"]
        }
    )

    # Verify customizations applied
    assert dna.metadata.name == "worker_specialized_01"

    # Verify domains appended to all skills
    for skill in dna.skills:
        domains_set = set(skill.domains)
        assert "graphql" in domains_set
        assert "grpc" in domains_set
        assert "rest" in domains_set  # Original domain preserved


@pytest.mark.asyncio
async def test_idempotency(genesis_agent):
    """Test duplicate request_id returns existing agent."""
    # First call
    dna1 = await genesis_agent.create_agent(
        request_id="test-003",
        template_name="worker_base"
    )

    # Second call with same request_id
    dna2 = await genesis_agent.create_agent(
        request_id="test-003",
        template_name="worker_base"
    )

    # Should return same agent
    assert dna1.metadata.id == dna2.metadata.id


@pytest.mark.asyncio
async def test_forbidden_customization(genesis_agent):
    """Test forbidden customizations are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        await genesis_agent.create_agent(
            request_id="test-004",
            template_name="worker_base",
            customizations={
                "ethics_flags": {"human_override": "false"}
            }
        )

    assert "FORBIDDEN" in str(exc_info.value)


@pytest.mark.asyncio
async def test_template_hash_stored(genesis_agent):
    """Test template hash is computed and stored."""
    dna = await genesis_agent.create_agent(
        request_id="test-005",
        template_name="worker_base"
    )

    # Verify template hash
    assert dna.metadata.template_hash
    assert dna.metadata.template_hash.startswith("sha256:")
    assert len(dna.metadata.template_hash) == 71  # "sha256:" + 64 hex chars


# ============================================================================
# Budget Tests
# ============================================================================

@pytest.mark.asyncio
async def test_budget_deduction(genesis_agent):
    """Test budget is deducted after agent creation."""
    initial_budget = await genesis_agent.budget.get_available_credits()

    await genesis_agent.create_agent(
        request_id="test-006",
        template_name="worker_base"
    )

    final_budget = await genesis_agent.budget.get_available_credits()

    # Budget should be reduced
    assert final_budget < initial_budget


@pytest.mark.asyncio
async def test_budget_reserve_protection(genesis_agent):
    """Test budget reserve is protected."""
    # Set low budget
    genesis_agent.budget.available_credits = 100
    # With 20% reserve, usable = 80
    # Cost is 10, so should succeed

    dna = await genesis_agent.create_agent(
        request_id="test-007",
        template_name="worker_base"
    )

    assert dna is not None


@pytest.mark.asyncio
async def test_insufficient_budget(genesis_agent):
    """Test creation fails when budget is insufficient."""
    # Set budget below reserve threshold
    genesis_agent.budget.available_credits = 5  # Not enough after reserve

    has_budget = await genesis_agent.check_budget(10)

    assert has_budget is False


# ============================================================================
# Kill Switch Tests
# ============================================================================

@pytest.mark.asyncio
async def test_killswitch_disabled(genesis_agent):
    """Test creation fails when kill switch is disabled."""
    # Disable Genesis
    genesis_agent.settings.enabled = False

    with pytest.raises(RuntimeError) as exc_info:
        await genesis_agent.create_agent(
            request_id="test-008",
            template_name="worker_base"
        )

    assert "DISABLED" in str(exc_info.value)


# ============================================================================
# Event Emission Tests
# ============================================================================

@pytest.mark.asyncio
async def test_events_emitted(genesis_agent):
    """Test events are emitted during creation."""
    # Clear audit log
    genesis_agent.audit_log.clear()

    await genesis_agent.create_agent(
        request_id="test-009",
        template_name="worker_base"
    )

    # Check audit log
    events = genesis_agent.audit_log.get_events()

    # Should have multiple events
    assert len(events) > 0

    # Check for expected event types
    event_types = [e["event_type"] for e in events]
    assert "genesis.agent.create.requested" in event_types
    assert "genesis.agent.template.loaded" in event_types
    assert "genesis.agent.create.validated" in event_types
    assert "genesis.agent.create.registered" in event_types


# ============================================================================
# Template Loading Tests
# ============================================================================

@pytest.mark.asyncio
async def test_load_template(genesis_agent):
    """Test template loading from YAML."""
    dna = await genesis_agent.load_template("worker_base")

    assert dna.metadata.name == "worker_generic"
    assert dna.metadata.type.value == "Worker"
    assert len(dna.skills) > 0


@pytest.mark.asyncio
async def test_load_nonexistent_template(genesis_agent):
    """Test loading nonexistent template fails."""
    from brain.agents.genesis_agent.dna_validator import TemplateNotFoundError

    with pytest.raises(TemplateNotFoundError):
        await genesis_agent.load_template("nonexistent")


# ============================================================================
# Hash Computation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_compute_dna_hash(genesis_agent):
    """Test DNA hash computation."""
    dna = await genesis_agent.create_agent(
        request_id="test-010",
        template_name="worker_base"
    )

    dna_hash = genesis_agent.compute_dna_hash(dna)

    # Should be 64 character hex string
    assert len(dna_hash) == 64
    assert all(c in "0123456789abcdef" for c in dna_hash)


# ============================================================================
# Cost Estimation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_estimate_cost(genesis_agent):
    """Test cost estimation for templates."""
    cost = await genesis_agent.estimate_cost("worker_base")

    assert cost > 0
    assert isinstance(cost, int)
