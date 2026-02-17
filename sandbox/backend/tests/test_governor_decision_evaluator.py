"""
Unit tests for Decision Evaluator (Phase 2 Foundation).

Tests deterministic rule evaluation, OR/AND logic, budget resolution,
and immune system integration.
"""

import pytest
from datetime import datetime
from app.modules.governor.manifest.schemas import (
    GovernorManifest,
    ManifestRule,
    RuleCondition,
    Budget,
    RiskClass,
)
from app.modules.governor.decision.models import (
    DecisionContext,
    RecoveryStrategy,
)
from app.modules.governor.decision.evaluator import DecisionEvaluator


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def simple_manifest():
    """Create simple manifest for testing."""
    return GovernorManifest(
        manifest_id="test_manifest",
        version="1.0.0",
        name="Test Manifest",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_llm_call",
                priority=100,
                enabled=True,
                when=RuleCondition(job_type="llm_call"),
                mode="RAIL",
                reason="LLM calls require governance",
            ),
            ManifestRule(
                rule_id="rule_production",
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
            max_parallel_attempts=5,
        ),
        risk_classes={
            "EXTERNAL": RiskClass(
                name="EXTERNAL",
                description="External services",
                recovery_strategy=RecoveryStrategy.RETRY,
                budget_multiplier=1.5,
            ),
        },
    )


@pytest.fixture
def or_logic_manifest():
    """Create manifest with OR-logic rules."""
    return GovernorManifest(
        manifest_id="or_test",
        version="1.0.0",
        name="OR Test",
        description="Test OR-logic",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_or",
                priority=100,
                enabled=True,
                when=RuleCondition(
                    any=[
                        {"job_type": "llm_call"},
                        {"job_type": "tool_execution"},
                    ]
                ),
                mode="RAIL",
                reason="LLM or tool execution",
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )


@pytest.fixture
def and_logic_manifest():
    """Create manifest with AND-logic rules."""
    return GovernorManifest(
        manifest_id="and_test",
        version="1.0.0",
        name="AND Test",
        description="Test AND-logic",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_and",
                priority=100,
                enabled=True,
                when=RuleCondition(
                    all=[
                        {"job_type": "llm_call"},
                        {"environment": "production"},
                    ]
                ),
                mode="RAIL",
                reason="Production LLM calls",
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )


# ============================================================================
# Tests: Deterministic Behavior
# ============================================================================

def test_evaluator_deterministic_same_input_same_output(simple_manifest):
    """Test that same inputs always produce same outputs."""
    evaluator = DecisionEvaluator(simple_manifest)

    context = DecisionContext(
        job_type="llm_call",
        mission_id="m_test",
        job_id="j_test",
    )

    # Evaluate 10 times
    decisions = [evaluator.evaluate(context, shadow_mode=False) for _ in range(10)]

    # All decisions should be identical
    first_decision = decisions[0]
    for decision in decisions[1:]:
        assert decision.mode == first_decision.mode
        assert decision.recovery_strategy == first_decision.recovery_strategy
        assert decision.triggered_rules == first_decision.triggered_rules
        assert decision.reason == first_decision.reason


def test_evaluator_priority_based_matching(simple_manifest):
    """Test that lower priority number wins (higher precedence)."""
    # simple_manifest has rule_llm_call (priority 100) and rule_production (priority 200)
    evaluator = DecisionEvaluator(simple_manifest)

    # Context matches both rules
    context = DecisionContext(
        job_type="llm_call",
        environment="production",
    )

    decision = evaluator.evaluate(context, shadow_mode=False)

    # Should match rule_llm_call (priority 100) because it's higher precedence
    assert decision.triggered_rules == ["rule_llm_call"]
    assert decision.reason == "LLM calls require governance"


def test_evaluator_first_match_wins():
    """Test that first matching rule wins (no fallthrough)."""
    manifest = GovernorManifest(
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
                reason="Rule 1",
            ),
            ManifestRule(
                rule_id="rule_2",
                priority=200,
                enabled=True,
                when=RuleCondition(job_type="llm_call"),
                mode="DIRECT",
                reason="Rule 2",
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    evaluator = DecisionEvaluator(manifest)
    context = DecisionContext(job_type="llm_call")

    decision = evaluator.evaluate(context, shadow_mode=False)

    # Should match rule_1 only (first match)
    assert decision.triggered_rules == ["rule_1"]
    assert decision.mode == "RAIL"
    assert decision.reason == "Rule 1"


# ============================================================================
# Tests: OR/AND Logic
# ============================================================================

def test_evaluator_or_logic_first_condition_true(or_logic_manifest):
    """Test OR-logic when first condition matches."""
    evaluator = DecisionEvaluator(or_logic_manifest)

    context = DecisionContext(job_type="llm_call")
    decision = evaluator.evaluate(context, shadow_mode=False)

    assert decision.triggered_rules == ["rule_or"]
    assert decision.mode == "RAIL"


def test_evaluator_or_logic_second_condition_true(or_logic_manifest):
    """Test OR-logic when second condition matches."""
    evaluator = DecisionEvaluator(or_logic_manifest)

    context = DecisionContext(job_type="tool_execution")
    decision = evaluator.evaluate(context, shadow_mode=False)

    assert decision.triggered_rules == ["rule_or"]
    assert decision.mode == "RAIL"


def test_evaluator_or_logic_no_conditions_true(or_logic_manifest):
    """Test OR-logic when no conditions match."""
    evaluator = DecisionEvaluator(or_logic_manifest)

    context = DecisionContext(job_type="other")
    decision = evaluator.evaluate(context, shadow_mode=False)

    # Should fall back to defaults
    assert decision.triggered_rules == []
    assert decision.mode == "DIRECT"
    assert "No matching rule" in decision.reason


def test_evaluator_and_logic_both_conditions_true(and_logic_manifest):
    """Test AND-logic when all conditions match."""
    evaluator = DecisionEvaluator(and_logic_manifest)

    context = DecisionContext(
        job_type="llm_call",
        environment="production",
    )
    decision = evaluator.evaluate(context, shadow_mode=False)

    assert decision.triggered_rules == ["rule_and"]
    assert decision.mode == "RAIL"


def test_evaluator_and_logic_one_condition_false(and_logic_manifest):
    """Test AND-logic when one condition doesn't match."""
    evaluator = DecisionEvaluator(and_logic_manifest)

    context = DecisionContext(
        job_type="llm_call",
        environment="development",  # Doesn't match
    )
    decision = evaluator.evaluate(context, shadow_mode=False)

    # Should fall back to defaults
    assert decision.triggered_rules == []
    assert decision.mode == "DIRECT"


# ============================================================================
# Tests: Budget Resolution
# ============================================================================

def test_evaluator_budget_from_defaults(simple_manifest):
    """Test budget resolution from manifest defaults."""
    evaluator = DecisionEvaluator(simple_manifest)

    context = DecisionContext(job_type="other")
    decision = evaluator.evaluate(context, shadow_mode=False)

    assert decision.budget_resolution.source == "defaults"
    assert decision.budget_resolution.budget.timeout_ms == 30000
    assert decision.budget_resolution.budget.max_retries == 3


def test_evaluator_budget_from_rule_override():
    """Test budget resolution from rule override."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_override",
                priority=100,
                enabled=True,
                when=RuleCondition(job_type="llm_call"),
                mode="RAIL",
                reason="LLM",
                budget_override=Budget(
                    timeout_ms=60000,
                    max_retries=5,
                ),
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    evaluator = DecisionEvaluator(manifest)
    context = DecisionContext(job_type="llm_call")

    decision = evaluator.evaluate(context, shadow_mode=False)

    assert decision.budget_resolution.source == "rule_override"
    assert decision.budget_resolution.rule_id == "rule_override"
    assert decision.budget_resolution.budget.timeout_ms == 60000
    assert decision.budget_resolution.budget.max_retries == 5


def test_evaluator_budget_from_job_override():
    """Test budget resolution from job-specific override."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
        job_overrides={
            "llm_call": Budget(
                timeout_ms=90000,
                max_retries=7,
            ),
        },
    )

    evaluator = DecisionEvaluator(manifest)
    context = DecisionContext(job_type="llm_call")

    decision = evaluator.evaluate(context, shadow_mode=False)

    assert decision.budget_resolution.source == "job_override"
    assert decision.budget_resolution.budget.timeout_ms == 90000
    assert decision.budget_resolution.budget.max_retries == 7


def test_evaluator_budget_with_risk_class_multiplier(simple_manifest):
    """Test budget multiplier from risk class."""
    evaluator = DecisionEvaluator(simple_manifest)

    context = DecisionContext(
        job_type="other",
        risk_class="EXTERNAL",  # 1.5x multiplier
    )

    decision = evaluator.evaluate(context, shadow_mode=False)

    # Base timeout: 30000ms, multiplier: 1.5 = 45000ms
    assert decision.budget_resolution.multiplier_applied == 1.5
    assert decision.budget_resolution.budget.timeout_ms == 45000
    # Retries not multiplied
    assert decision.budget_resolution.budget.max_retries == 3


# ============================================================================
# Tests: Recovery Strategy
# ============================================================================

def test_evaluator_recovery_from_rule():
    """Test recovery strategy from matched rule."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_manual",
                priority=100,
                enabled=True,
                when=RuleCondition(uses_personal_data=True),
                mode="RAIL",
                reason="Personal data",
                recovery_strategy=RecoveryStrategy.MANUAL_CONFIRM,
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    evaluator = DecisionEvaluator(manifest)
    context = DecisionContext(
        job_type="llm_call",
        uses_personal_data=True,
    )

    decision = evaluator.evaluate(context, shadow_mode=False)

    assert decision.recovery_strategy == RecoveryStrategy.MANUAL_CONFIRM


def test_evaluator_recovery_from_risk_class():
    """Test recovery strategy from risk class."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_external",
                priority=100,
                enabled=True,
                when=RuleCondition(risk_class="NON_IDEMPOTENT"),
                mode="RAIL",
                reason="Non-idempotent",
                # No recovery_strategy specified
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={
            "NON_IDEMPOTENT": RiskClass(
                name="NON_IDEMPOTENT",
                description="Non-idempotent operations",
                recovery_strategy=RecoveryStrategy.ROLLBACK_REQUIRED,
                budget_multiplier=2.0,
            ),
        },
    )

    evaluator = DecisionEvaluator(manifest)
    context = DecisionContext(
        job_type="database_write",
        risk_class="NON_IDEMPOTENT",
    )

    decision = evaluator.evaluate(context, shadow_mode=False)

    # Should use risk class recovery strategy
    assert decision.recovery_strategy == RecoveryStrategy.ROLLBACK_REQUIRED


# ============================================================================
# Tests: Immune System Integration
# ============================================================================

def test_evaluator_immune_alert_for_manual_confirm():
    """Test immune alert required for MANUAL_CONFIRM recovery."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_manual",
                priority=100,
                enabled=True,
                when=RuleCondition(uses_personal_data=True),
                mode="RAIL",
                reason="Personal data",
                recovery_strategy=RecoveryStrategy.MANUAL_CONFIRM,
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    evaluator = DecisionEvaluator(manifest)
    context = DecisionContext(
        job_type="llm_call",
        uses_personal_data=True,
    )

    decision = evaluator.evaluate(context, shadow_mode=False)

    # Should require immune alert
    assert decision.immune_alert_required is True


def test_evaluator_health_impact_assessment():
    """Test health impact assessment."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_rail",
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

    evaluator = DecisionEvaluator(manifest)

    # RAIL mode → medium health impact
    context_rail = DecisionContext(job_type="llm_call")
    decision_rail = evaluator.evaluate(context_rail, shadow_mode=False)
    assert decision_rail.health_impact == "medium"

    # DIRECT mode → low health impact
    context_direct = DecisionContext(job_type="other")
    decision_direct = evaluator.evaluate(context_direct, shadow_mode=False)
    assert decision_direct.health_impact == "low"


# ============================================================================
# Tests: Shadow Mode
# ============================================================================

def test_evaluator_shadow_mode_flag(simple_manifest):
    """Test shadow mode flag in decision."""
    evaluator = DecisionEvaluator(simple_manifest)

    context = DecisionContext(job_type="llm_call")

    # Active decision
    decision_active = evaluator.evaluate(context, shadow_mode=False)
    assert decision_active.shadow_mode is False

    # Shadow decision
    decision_shadow = evaluator.evaluate(context, shadow_mode=True)
    assert decision_shadow.shadow_mode is True


# ============================================================================
# Tests: Edge Cases
# ============================================================================

def test_evaluator_disabled_rule_not_matched():
    """Test that disabled rules are not matched."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[
            ManifestRule(
                rule_id="rule_disabled",
                priority=100,
                enabled=False,  # Disabled
                when=RuleCondition(job_type="llm_call"),
                mode="RAIL",
                reason="Disabled",
            ),
        ],
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    evaluator = DecisionEvaluator(manifest)
    context = DecisionContext(job_type="llm_call")

    decision = evaluator.evaluate(context, shadow_mode=False)

    # Should fall back to defaults (disabled rule not matched)
    assert decision.triggered_rules == []
    assert decision.mode == "DIRECT"


def test_evaluator_no_rules_defaults():
    """Test that manifest with no rules uses defaults."""
    manifest = GovernorManifest(
        manifest_id="test",
        version="1.0.0",
        name="Test",
        description="Test",
        created_at=datetime.utcnow(),
        rules=[],  # No rules
        budget_defaults=Budget(timeout_ms=30000, max_retries=3),
        risk_classes={},
    )

    evaluator = DecisionEvaluator(manifest)
    context = DecisionContext(job_type="llm_call")

    decision = evaluator.evaluate(context, shadow_mode=False)

    assert decision.triggered_rules == []
    assert decision.mode == "DIRECT"
    assert decision.recovery_strategy == RecoveryStrategy.RETRY
    assert decision.budget_resolution.source == "defaults"
