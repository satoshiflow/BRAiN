"""
Tests for DNA Validation

This module tests the DNA validator including:
- Schema validation
- Template hash computation
- Customization whitelist enforcement
- Forbidden field protection

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

import pytest
from pathlib import Path

from brain.agents.genesis_agent.dna_schema import (
    AgentDNA,
    AgentType,
    AgentTraits,
    BehaviorModules,
    Capabilities,
    DNAMetadata,
    EthicsFlags,
    MissionAffinity,
    ResourceLimits,
    RuntimeConfig,
    Skill,
)
from brain.agents.genesis_agent.dna_validator import (
    DNAValidator,
    ValidationError,
    TemplateNotFoundError,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def templates_dir(tmp_path):
    """Create temporary templates directory."""
    templates = tmp_path / "templates"
    templates.mkdir()

    # Create a sample template
    template_content = """
agent_dna:
  metadata:
    name: "test_agent"
    type: "Worker"
    version: "1.0.0"
    template_version: "1.0"
    parent_id: null

  traits:
    base_type: "Worker"
    primary_function: "testing"
    autonomy_level: 2

  skills:
    - skill_id: "test_skill"
      proficiency: 0.8
      domains: ["testing"]

  behavior_modules:
    communication_style: "concise"
    decision_making: "rule_based"
    collaboration_preference: "sync"
    error_handling: "retry"

  ethics_flags:
    data_privacy: "strict"
    transparency: "full_audit"
    bias_awareness: "enabled"
    human_override: "always_allowed"

  capabilities:
    tools_allowed: ["test_tool"]
    connectors_allowed: []
    network_access: "restricted"

  runtime:
    model_policy: "cheap"
    temperature_cap: 0.5
    max_tokens_cap: 1000
    allowed_models: ["test-model"]

  memory_seeds:
    - "Test knowledge"

  resource_limits:
    max_credits_per_mission: 50
    max_llm_calls_per_day: 100
    timeout_seconds: 300

  mission_affinity:
    preferred_types: ["testing"]
    required_context: ["test_data"]
"""
    (templates / "test_template.yaml").write_text(template_content)
    return templates


@pytest.fixture
def validator(templates_dir):
    """Create DNA validator instance."""
    return DNAValidator(templates_dir)


@pytest.fixture
def valid_dna():
    """Create valid DNA instance."""
    return AgentDNA(
        metadata=DNAMetadata(
            name="test_agent",
            type=AgentType.WORKER,
            dna_schema_version="2.0",
            template_hash="sha256:abc123",
            template_version="1.0"
        ),
        traits=AgentTraits(
            base_type=AgentType.WORKER,
            primary_function="testing",
            autonomy_level=2
        ),
        skills=[
            Skill(skill_id="test", proficiency=0.8, domains=["testing"])
        ],
        behavior_modules=BehaviorModules(
            communication_style="concise",
            decision_making="rule_based",
            collaboration_preference="sync",
            error_handling="retry"
        ),
        ethics_flags=EthicsFlags(),
        capabilities=Capabilities(),
        runtime=RuntimeConfig(),
        memory_seeds=["Test"],
        resource_limits=ResourceLimits(),
        mission_affinity=MissionAffinity()
    )


# ============================================================================
# Template Hash Tests
# ============================================================================

def test_compute_template_hash(validator, templates_dir):
    """Test SHA256 hash computation for templates."""
    hash_val = validator.compute_template_hash("test_template")

    # Should return sha256: prefixed hash
    assert hash_val.startswith("sha256:")
    assert len(hash_val) == 71  # "sha256:" (7) + 64 hex chars

    # Same template should produce same hash
    hash_val2 = validator.compute_template_hash("test_template")
    assert hash_val == hash_val2


def test_compute_hash_template_not_found(validator):
    """Test hash computation fails for missing template."""
    with pytest.raises(TemplateNotFoundError):
        validator.compute_template_hash("nonexistent_template")


def test_verify_template_hash(validator):
    """Test template hash verification."""
    hash_val = validator.compute_template_hash("test_template")

    # Verify with correct hash
    assert validator.verify_template_hash("test_template", hash_val) is True

    # Verify with incorrect hash
    assert validator.verify_template_hash("test_template", "sha256:wrong") is False


# ============================================================================
# Customization Validation Tests
# ============================================================================

def test_validate_allowed_customizations(validator):
    """Test validation accepts whitelisted customizations."""
    customizations = {
        "metadata.name": "custom_agent_01",
        "skills[].domains": ["api", "data"],
        "memory_seeds": ["New knowledge"]
    }

    # Should not raise exception
    validator.validate_customizations(customizations)


def test_validate_forbidden_customization(validator):
    """Test validation rejects forbidden fields."""
    customizations = {
        "ethics_flags": {"human_override": "false"}
    }

    with pytest.raises(ValidationError) as exc_info:
        validator.validate_customizations(customizations)

    assert "FORBIDDEN" in str(exc_info.value)
    assert "ethics_flags" in str(exc_info.value)


def test_validate_not_in_whitelist(validator):
    """Test validation rejects non-whitelisted fields."""
    customizations = {
        "unknown_field": "value"
    }

    with pytest.raises(ValidationError) as exc_info:
        validator.validate_customizations(customizations)

    assert "not in whitelist" in str(exc_info.value)


def test_validate_customization_name_pattern(validator):
    """Test name customization pattern validation."""
    # Valid name
    validator.validate_customizations({"metadata.name": "valid_name_123"})

    # Invalid name (uppercase)
    with pytest.raises(ValidationError):
        validator.validate_customizations({"metadata.name": "InvalidName"})

    # Invalid name (special chars)
    with pytest.raises(ValidationError):
        validator.validate_customizations({"metadata.name": "invalid-name"})


def test_validate_customization_array_max_items(validator):
    """Test array customization max items validation."""
    # Within limit
    validator.validate_customizations({
        "skills[].domains": ["a", "b", "c"]  # 3 items, max is 10
    })

    # Exceeds limit
    with pytest.raises(ValidationError):
        validator.validate_customizations({
            "skills[].domains": [f"item{i}" for i in range(15)]  # 15 > 10
        })


# ============================================================================
# DNA Validation Tests
# ============================================================================

def test_validate_valid_dna(validator, valid_dna):
    """Test validation passes for valid DNA."""
    # Should not raise exception
    validator.validate_dna(valid_dna)


def test_validate_skill_proficiency_bounds(validator, valid_dna):
    """Test validation checks skill proficiency bounds."""
    # Invalid proficiency (> 1.0)
    valid_dna.skills[0].proficiency = 1.5

    with pytest.raises(ValidationError) as exc_info:
        validator.validate_dna(valid_dna)

    assert "proficiency must be 0-1" in str(exc_info.value)


def test_validate_mandatory_fields(validator, valid_dna):
    """Test validation checks mandatory fields."""
    # Missing dna_schema_version
    valid_dna.metadata.dna_schema_version = ""

    with pytest.raises(ValidationError) as exc_info:
        validator.validate_dna(valid_dna)

    assert "dna_schema_version is MANDATORY" in str(exc_info.value)


def test_validate_template_hash_format(validator, valid_dna):
    """Test validation checks template hash format."""
    # Invalid hash format (missing sha256: prefix)
    valid_dna.metadata.template_hash = "abc123"

    with pytest.raises(ValidationError) as exc_info:
        validator.validate_dna(valid_dna)

    assert "must start with 'sha256:'" in str(exc_info.value)


def test_validate_immutable_created_by(validator, valid_dna):
    """Test validation enforces created_by immutability."""
    # Try to set created_by to something other than "genesis_agent"
    with pytest.raises(ValueError):
        valid_dna.metadata.created_by = "hacker"


def test_validate_immutable_human_override(validator, valid_dna):
    """Test validation enforces human_override immutability."""
    # Try to disable human override (EU AI Act violation)
    with pytest.raises(ValueError):
        valid_dna.ethics_flags.human_override = "never"


def test_validate_resource_limits(validator, valid_dna):
    """Test validation checks resource limits."""
    # Negative credits
    valid_dna.resource_limits.max_credits_per_mission = -10

    with pytest.raises(ValidationError) as exc_info:
        validator.validate_dna(valid_dna)

    assert "max_credits_per_mission must be >= 0" in str(exc_info.value)


# ============================================================================
# Utility Tests
# ============================================================================

def test_list_available_templates(validator):
    """Test listing available templates."""
    templates = validator.list_available_templates()

    assert "test_template" in templates
    assert isinstance(templates, list)


def test_get_customization_help(validator):
    """Test getting customization documentation."""
    help_info = validator.get_customization_help()

    assert "metadata.name" in help_info
    assert "skills[].domains" in help_info
    assert "memory_seeds" in help_info

    # Check structure
    assert help_info["metadata.name"]["type"] == "string"
    assert help_info["skills[].domains"]["action"] == "append"


# ============================================================================
# Edge Cases
# ============================================================================

def test_empty_customizations(validator):
    """Test validation handles empty customizations."""
    # Should not raise exception
    validator.validate_customizations({})


def test_base_type_consistency(valid_dna):
    """Test DNA validates base_type consistency."""
    # Mismatch between metadata.type and traits.base_type
    # This should be caught by AgentDNA.model_post_init

    with pytest.raises(ValueError) as exc_info:
        AgentDNA(
            metadata=DNAMetadata(
                name="test",
                type=AgentType.WORKER,
                dna_schema_version="2.0",
                template_hash="sha256:abc",
                template_version="1.0"
            ),
            traits=AgentTraits(
                base_type=AgentType.ANALYST,  # Mismatch!
                primary_function="test",
                autonomy_level=2
            ),
            skills=[],
            behavior_modules=BehaviorModules(
                communication_style="concise",
                decision_making="rule_based",
                collaboration_preference="sync",
                error_handling="retry"
            ),
            ethics_flags=EthicsFlags(),
            capabilities=Capabilities(),
            runtime=RuntimeConfig(),
            memory_seeds=[],
            resource_limits=ResourceLimits(),
            mission_affinity=MissionAffinity()
        )

    assert "Base type mismatch" in str(exc_info.value)
