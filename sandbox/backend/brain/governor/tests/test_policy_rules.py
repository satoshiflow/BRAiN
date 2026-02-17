"""
Unit Tests for Policy Rules v1 (Phase 2a)

Tests each rule group (A-E) to ensure deterministic behavior.

Test Coverage:
- Group A: Role & Authorization (A1, A2)
- Group B: Template Integrity (B1, B2)
- Group C: DNA Constraints (C1, C2, C3)
- Group D: Budget & Population (D1, D2)
- Group E: Risk & Quarantine (E1, E2, E3)

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-02
"""

import pytest

from brain.agents.genesis_agent.dna_schema import AgentType
from brain.governor.decision.models import ReasonCode
from brain.governor.policy import rules


# ============================================================================
# Group A: Role & Authorization
# ============================================================================

class TestGroupA:
    """Tests for Group A: Role & Authorization."""

    def test_a1_system_admin_required_success(self):
        """A1: SYSTEM_ADMIN role should be approved."""
        approved, code, detail, triggered = rules.rule_a1_require_system_admin("SYSTEM_ADMIN")

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_a1_system_admin_required_failure(self):
        """A1: Non-SYSTEM_ADMIN role should be rejected."""
        approved, code, detail, triggered = rules.rule_a1_require_system_admin("USER")

        assert approved is False
        assert code == ReasonCode.UNAUTHORIZED_ROLE
        assert triggered is True
        assert "SYSTEM_ADMIN" in detail

    def test_a2_killswitch_check_success(self):
        """A2: Kill switch not active should be approved."""
        approved, code, detail, triggered = rules.rule_a2_killswitch_check(False)

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_a2_killswitch_check_failure(self):
        """A2: Kill switch active should be rejected."""
        approved, code, detail, triggered = rules.rule_a2_killswitch_check(True)

        assert approved is False
        assert code == ReasonCode.KILLSWITCH_ACTIVE
        assert triggered is True
        assert "Kill switch" in detail


# ============================================================================
# Group B: Template Integrity
# ============================================================================

class TestGroupB:
    """Tests for Group B: Template Integrity."""

    def test_b1_template_hash_required_success(self):
        """B1: Valid template hash should be approved."""
        approved, code, detail, triggered = rules.rule_b1_template_hash_required(
            "sha256:abc123def456"
        )

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_b1_template_hash_required_missing(self):
        """B1: Missing template hash should be rejected."""
        approved, code, detail, triggered = rules.rule_b1_template_hash_required("")

        assert approved is False
        assert code == ReasonCode.TEMPLATE_HASH_MISSING
        assert triggered is True

    def test_b1_template_hash_required_invalid_format(self):
        """B1: Invalid hash format should be rejected."""
        approved, code, detail, triggered = rules.rule_b1_template_hash_required(
            "abc123"  # No 'sha256:' prefix
        )

        assert approved is False
        assert code == ReasonCode.TEMPLATE_HASH_MISSING
        assert triggered is True

    def test_b2_template_in_allowlist_success(self):
        """B2: Template in allowlist should be approved."""
        allowlist = ["worker_base", "analyst_base"]
        approved, code, detail, triggered = rules.rule_b2_template_in_allowlist(
            "worker_base",
            allowlist
        )

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_b2_template_in_allowlist_failure(self):
        """B2: Template not in allowlist should be rejected."""
        allowlist = ["worker_base", "analyst_base"]
        approved, code, detail, triggered = rules.rule_b2_template_in_allowlist(
            "hacker_agent",
            allowlist
        )

        assert approved is False
        assert code == ReasonCode.TEMPLATE_NOT_IN_ALLOWLIST
        assert triggered is True
        assert "hacker_agent" in detail


# ============================================================================
# Group C: DNA Constraints
# ============================================================================

class TestGroupC:
    """Tests for Group C: DNA Constraints."""

    def test_c1_ethics_human_override_immutable_success(self):
        """C1: human_override='always_allowed' should be approved."""
        dna = {
            "ethics_flags": {
                "human_override": "always_allowed"
            }
        }
        approved, code, detail, triggered = rules.rule_c1_ethics_human_override_immutable(dna)

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_c1_ethics_human_override_immutable_failure(self):
        """C1: human_override!='always_allowed' should be rejected."""
        dna = {
            "ethics_flags": {
                "human_override": "never"
            }
        }
        approved, code, detail, triggered = rules.rule_c1_ethics_human_override_immutable(dna)

        assert approved is False
        assert code == ReasonCode.CAPABILITY_ESCALATION_DENIED
        assert triggered is True
        assert "always_allowed" in detail

    def test_c2_network_access_cap_within_limit(self):
        """C2: network_access within cap should be approved."""
        dna = {
            "capabilities": {
                "network_access": "restricted"
            }
        }
        approved, code, detail, triggered = rules.rule_c2_network_access_cap(
            dna,
            AgentType.WORKER  # Cap is 'restricted'
        )

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_c2_network_access_cap_exceeds_limit(self):
        """C2: network_access exceeding cap should be rejected."""
        dna = {
            "capabilities": {
                "network_access": "full"
            }
        }
        approved, code, detail, triggered = rules.rule_c2_network_access_cap(
            dna,
            AgentType.WORKER  # Cap is 'restricted', but DNA has 'full'
        )

        assert approved is False
        assert code == ReasonCode.CAPABILITY_ESCALATION_DENIED
        assert triggered is True
        assert "network_access" in detail

    def test_c3_autonomy_level_cap_within_limit(self):
        """C3: autonomy_level within cap should be approved."""
        dna = {
            "traits": {
                "autonomy_level": 2
            }
        }
        approved, code, detail, triggered = rules.rule_c3_autonomy_level_cap(
            dna,
            AgentType.WORKER  # Cap is 3
        )

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_c3_autonomy_level_cap_exceeds_limit(self):
        """C3: autonomy_level exceeding cap should be rejected."""
        dna = {
            "traits": {
                "autonomy_level": 5
            }
        }
        approved, code, detail, triggered = rules.rule_c3_autonomy_level_cap(
            dna,
            AgentType.WORKER  # Cap is 3, but DNA has 5
        )

        assert approved is False
        assert code == ReasonCode.CAPABILITY_ESCALATION_DENIED
        assert triggered is True
        assert "autonomy_level" in detail


# ============================================================================
# Group D: Budget & Population
# ============================================================================

class TestGroupD:
    """Tests for Group D: Budget & Population."""

    def test_d1_creation_cost_affordable_success(self):
        """D1: Affordable creation cost should be approved."""
        approved, code, detail, triggered = rules.rule_d1_creation_cost_affordable(
            available_credits=1000,
            creation_cost=100,
            reserve_ratio=0.2  # Usable = 800
        )

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_d1_creation_cost_affordable_failure(self):
        """D1: Unaffordable creation cost should be rejected."""
        approved, code, detail, triggered = rules.rule_d1_creation_cost_affordable(
            available_credits=100,
            creation_cost=90,
            reserve_ratio=0.2  # Usable = 80, cost = 90
        )

        assert approved is False
        assert code == ReasonCode.BUDGET_INSUFFICIENT
        assert triggered is True
        assert "90" in detail
        assert "80" in detail

    def test_d2_population_limit_within_limit(self):
        """D2: Population within limit should be approved."""
        max_pop = {AgentType.WORKER: 50}
        approved, code, detail, triggered = rules.rule_d2_population_limit(
            AgentType.WORKER,
            current_population=10,
            max_population=max_pop
        )

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_d2_population_limit_exceeded(self):
        """D2: Population exceeding limit should be rejected."""
        max_pop = {AgentType.GENESIS: 1}
        approved, code, detail, triggered = rules.rule_d2_population_limit(
            AgentType.GENESIS,
            current_population=1,  # Already at limit
            max_population=max_pop
        )

        assert approved is False
        assert code == ReasonCode.POPULATION_LIMIT_EXCEEDED
        assert triggered is True
        assert "GENESIS" in detail or "Genesis" in detail


# ============================================================================
# Group E: Risk & Quarantine
# ============================================================================

class TestGroupE:
    """Tests for Group E: Risk & Quarantine."""

    def test_e1_critical_agents_quarantined_genesis(self):
        """E1: CRITICAL agent (Genesis) should be quarantined."""
        quarantine, reason = rules.rule_e1_critical_agents_quarantined(AgentType.GENESIS)

        assert quarantine is True
        assert "CRITICAL" in reason or "Genesis" in reason

    def test_e1_critical_agents_quarantined_worker(self):
        """E1: Non-CRITICAL agent (Worker) should not be quarantined."""
        quarantine, reason = rules.rule_e1_critical_agents_quarantined(AgentType.WORKER)

        assert quarantine is False
        assert "Not a critical" in reason

    def test_e2_customizations_increase_risk_yes(self):
        """E2: Customizations should elevate risk to MEDIUM."""
        risk_tier, reason = rules.rule_e2_customizations_increase_risk(True)

        assert risk_tier == "MEDIUM"
        assert "Customizations" in reason

    def test_e2_customizations_increase_risk_no(self):
        """E2: No customizations should keep risk LOW."""
        risk_tier, reason = rules.rule_e2_customizations_increase_risk(False)

        assert risk_tier == "LOW"
        assert "No customizations" in reason

    def test_e3_capability_escalation_reject_none(self):
        """E3: No capability escalations should be approved."""
        approved, code, detail, triggered = rules.rule_e3_capability_escalation_reject(
            customization_fields=["metadata.name"]
        )

        assert approved is True
        assert code == ReasonCode.APPROVED_DEFAULT
        assert triggered is False

    def test_e3_capability_escalation_reject_capabilities(self):
        """E3: Capability escalation (capabilities.*) should be rejected."""
        approved, code, detail, triggered = rules.rule_e3_capability_escalation_reject(
            customization_fields=["capabilities.network_access"]
        )

        assert approved is False
        assert code == ReasonCode.CAPABILITY_ESCALATION_DENIED
        assert triggered is True
        assert "capabilities.network_access" in detail

    def test_e3_capability_escalation_reject_resource_limits(self):
        """E3: Capability escalation (resource_limits.*) should be rejected."""
        approved, code, detail, triggered = rules.rule_e3_capability_escalation_reject(
            customization_fields=["resource_limits.max_credits_per_mission"]
        )

        assert approved is False
        assert code == ReasonCode.CAPABILITY_ESCALATION_DENIED
        assert triggered is True

    def test_e3_capability_escalation_reject_autonomy(self):
        """E3: Capability escalation (autonomy_level) should be rejected."""
        approved, code, detail, triggered = rules.rule_e3_capability_escalation_reject(
            customization_fields=["traits.autonomy_level"]
        )

        assert approved is False
        assert code == ReasonCode.CAPABILITY_ESCALATION_DENIED
        assert triggered is True


# ============================================================================
# Determinism Tests
# ============================================================================

class TestDeterminism:
    """Tests to ensure rules are deterministic (same input → same output)."""

    def test_determinism_rule_a1(self):
        """Rule A1 should be deterministic."""
        result1 = rules.rule_a1_require_system_admin("USER")
        result2 = rules.rule_a1_require_system_admin("USER")
        result3 = rules.rule_a1_require_system_admin("USER")

        assert result1 == result2 == result3

    def test_determinism_rule_c2(self):
        """Rule C2 should be deterministic."""
        dna = {"capabilities": {"network_access": "full"}}

        result1 = rules.rule_c2_network_access_cap(dna, AgentType.WORKER)
        result2 = rules.rule_c2_network_access_cap(dna, AgentType.WORKER)
        result3 = rules.rule_c2_network_access_cap(dna, AgentType.WORKER)

        assert result1 == result2 == result3

    def test_determinism_rule_d1(self):
        """Rule D1 should be deterministic."""
        result1 = rules.rule_d1_creation_cost_affordable(100, 90, 0.2)
        result2 = rules.rule_d1_creation_cost_affordable(100, 90, 0.2)
        result3 = rules.rule_d1_creation_cost_affordable(100, 90, 0.2)

        assert result1 == result2 == result3
