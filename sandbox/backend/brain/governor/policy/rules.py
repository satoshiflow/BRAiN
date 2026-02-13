"""
Policy Rules v1 (Phase 2a)

Deterministic policy rules for agent creation governance.

These rules are PURE FUNCTIONS - given the same input, they always return
the same output. No side effects, no I/O, no randomness.

Rule Groups:
- Group A: Role & Authorization
- Group B: Template Integrity
- Group C: DNA Constraints
- Group D: Budget & Population Limits
- Group E: Risk & Quarantine

Each rule returns:
- approved: bool
- reason_code: ReasonCode
- reason_detail: str
- triggered: bool (whether rule caused decision)

Author: Governor v1 System
Version: 1.0.0
Created: 2026-01-02
"""

from __future__ import annotations

from typing import Any, Dict, Tuple

from brain.agents.genesis_agent.dna_schema import AgentType
from brain.governor.constraints.defaults import get_agent_type_caps
from brain.governor.decision.models import ReasonCode


# ============================================================================
# Rule Result Type
# ============================================================================

RuleResult = Tuple[bool, ReasonCode, str, bool]
# (approved, reason_code, reason_detail, triggered)


# ============================================================================
# Group A: Role & Authorization
# ============================================================================

def rule_a1_require_system_admin(actor_role: str) -> RuleResult:
    """
    A1: Agent creation requires SYSTEM_ADMIN role.

    Args:
        actor_role: Actor role from request

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Example:
        >>> approved, code, detail, triggered = rule_a1_require_system_admin("USER")
        >>> assert approved is False
        >>> assert code == ReasonCode.UNAUTHORIZED_ROLE
    """
    if actor_role != "SYSTEM_ADMIN":
        return (
            False,
            ReasonCode.UNAUTHORIZED_ROLE,
            f"Agent creation requires SYSTEM_ADMIN role, got: {actor_role}",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Role authorized", False)


def rule_a2_killswitch_check(killswitch_active: bool) -> RuleResult:
    """
    A2: Kill switch must not be active (Defense in Depth).

    Args:
        killswitch_active: Whether kill switch is active

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Note:
        Genesis Agent already checks kill switch, but this is Defense in Depth.

    Example:
        >>> approved, code, detail, triggered = rule_a2_killswitch_check(True)
        >>> assert approved is False
        >>> assert code == ReasonCode.KILLSWITCH_ACTIVE
    """
    if killswitch_active:
        return (
            False,
            ReasonCode.KILLSWITCH_ACTIVE,
            "Kill switch is active, agent creation disabled",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Kill switch not active", False)


# ============================================================================
# Group B: Template Integrity
# ============================================================================

def rule_b1_template_hash_required(template_hash: str) -> RuleResult:
    """
    B1: Template hash must exist.

    Args:
        template_hash: Template hash from request

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Example:
        >>> approved, code, detail, triggered = rule_b1_template_hash_required("")
        >>> assert approved is False
        >>> assert code == ReasonCode.TEMPLATE_HASH_MISSING
    """
    if not template_hash or not template_hash.startswith("sha256:"):
        return (
            False,
            ReasonCode.TEMPLATE_HASH_MISSING,
            "Template hash missing or invalid format (must be 'sha256:...')",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Template hash valid", False)


def rule_b2_template_in_allowlist(
    template_name: str,
    allowlist: list[str]
) -> RuleResult:
    """
    B2: Template name must be in allowlist.

    Args:
        template_name: Template name from request
        allowlist: List of allowed template names

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Example:
        >>> allowed = ["worker_base", "analyst_base"]
        >>> approved, code, detail, triggered = rule_b2_template_in_allowlist("hacker", allowed)
        >>> assert approved is False
        >>> assert code == ReasonCode.TEMPLATE_NOT_IN_ALLOWLIST
    """
    if template_name not in allowlist:
        return (
            False,
            ReasonCode.TEMPLATE_NOT_IN_ALLOWLIST,
            f"Template '{template_name}' not in allowlist: {allowlist}",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Template in allowlist", False)


# ============================================================================
# Group C: DNA Constraints
# ============================================================================

def rule_c1_ethics_human_override_immutable(dna: Dict[str, Any]) -> RuleResult:
    """
    C1: ethics_flags.human_override must be 'always_allowed' (IMMUTABLE).

    Args:
        dna: Agent DNA dictionary

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Note:
        This is enforced by Pydantic validators, but we check again (Defense in Depth).

    Example:
        >>> dna = {"ethics_flags": {"human_override": "never"}}
        >>> approved, code, detail, triggered = rule_c1_ethics_human_override_immutable(dna)
        >>> assert approved is False
    """
    human_override = dna.get("ethics_flags", {}).get("human_override", "")

    if human_override != "always_allowed":
        return (
            False,
            ReasonCode.CAPABILITY_ESCALATION_DENIED,
            f"ethics_flags.human_override must be 'always_allowed' (IMMUTABLE), got: {human_override}",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Ethics human_override valid", False)


def rule_c2_network_access_cap(
    dna: Dict[str, Any],
    agent_type: AgentType
) -> RuleResult:
    """
    C2: network_access must not exceed AgentType cap.

    Args:
        dna: Agent DNA dictionary
        agent_type: Agent type

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Network Access Hierarchy:
        none < restricted < full

    Example:
        >>> dna = {"capabilities": {"network_access": "full"}}
        >>> approved, code, detail, triggered = rule_c2_network_access_cap(dna, AgentType.WORKER)
        >>> assert approved is False  # Worker cap is 'restricted'
    """
    caps = get_agent_type_caps(agent_type)
    cap_network = caps["network_access"]
    dna_network = dna.get("capabilities", {}).get("network_access", "restricted")

    # Network access hierarchy
    hierarchy = {"none": 0, "restricted": 1, "full": 2}

    if hierarchy[dna_network] > hierarchy[cap_network]:
        return (
            False,
            ReasonCode.CAPABILITY_ESCALATION_DENIED,
            f"network_access '{dna_network}' exceeds cap '{cap_network}' for {agent_type}",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Network access within cap", False)


def rule_c3_autonomy_level_cap(
    dna: Dict[str, Any],
    agent_type: AgentType
) -> RuleResult:
    """
    C3: autonomy_level must not exceed AgentType cap.

    Args:
        dna: Agent DNA dictionary
        agent_type: Agent type

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Example:
        >>> dna = {"traits": {"autonomy_level": 5}}
        >>> approved, code, detail, triggered = rule_c3_autonomy_level_cap(dna, AgentType.WORKER)
        >>> assert approved is False  # Worker cap is 3
    """
    caps = get_agent_type_caps(agent_type)
    cap_autonomy = caps["autonomy_level"]
    dna_autonomy = dna.get("traits", {}).get("autonomy_level", 1)

    if dna_autonomy > cap_autonomy:
        return (
            False,
            ReasonCode.CAPABILITY_ESCALATION_DENIED,
            f"autonomy_level {dna_autonomy} exceeds cap {cap_autonomy} for {agent_type}",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Autonomy level within cap", False)


# ============================================================================
# Group D: Budget & Population Limits
# ============================================================================

def rule_d1_creation_cost_affordable(
    available_credits: int,
    creation_cost: int,
    reserve_ratio: float
) -> RuleResult:
    """
    D1: Creation cost must be affordable (with reserve protection).

    Args:
        available_credits: Available credits in budget
        creation_cost: Estimated creation cost
        reserve_ratio: Reserve ratio (e.g., 0.2 = 20%)

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Example:
        >>> approved, code, detail, triggered = rule_d1_creation_cost_affordable(
        ...     available_credits=100,
        ...     creation_cost=90,
        ...     reserve_ratio=0.2
        ... )
        >>> assert approved is False  # Usable = 80, cost = 90
    """
    reserve = int(available_credits * reserve_ratio)
    usable = available_credits - reserve

    if creation_cost > usable:
        return (
            False,
            ReasonCode.BUDGET_INSUFFICIENT,
            f"Creation cost {creation_cost} exceeds usable budget {usable} "
            f"(available={available_credits}, reserve={reserve})",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Creation cost affordable", False)


def rule_d2_population_limit(
    agent_type: AgentType,
    current_population: int,
    max_population: Dict[AgentType, int]
) -> RuleResult:
    """
    D2: Population limit per AgentType must not be exceeded.

    Args:
        agent_type: Agent type
        current_population: Current count of this AgentType
        max_population: Max population per AgentType

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Example:
        >>> max_pop = {AgentType.GENESIS: 1}
        >>> approved, code, detail, triggered = rule_d2_population_limit(
        ...     AgentType.GENESIS,
        ...     current_population=1,
        ...     max_population=max_pop
        ... )
        >>> assert approved is False  # Already at limit
    """
    limit = max_population.get(agent_type, float('inf'))

    if current_population >= limit:
        return (
            False,
            ReasonCode.POPULATION_LIMIT_EXCEEDED,
            f"Population limit for {agent_type} exceeded: {current_population}/{limit}",
            True
        )

    return (True, ReasonCode.APPROVED_DEFAULT, "Population within limit", False)


# ============================================================================
# Group E: Risk & Quarantine
# ============================================================================

def rule_e1_critical_agents_quarantined(agent_type: AgentType) -> Tuple[bool, str]:
    """
    E1: CRITICAL agents (Genesis, Governor, Supervisor, Ligase, KARMA) must be quarantined.

    Args:
        agent_type: Agent type

    Returns:
        (quarantine, reason)

    Note:
        This rule doesn't reject, it sets quarantine=True.

    Example:
        >>> quarantine, reason = rule_e1_critical_agents_quarantined(AgentType.GENESIS)
        >>> assert quarantine is True
    """
    critical_types = {
        AgentType.GENESIS,
        AgentType.GOVERNOR,
        AgentType.SUPERVISOR,
        AgentType.LIGASE,
        AgentType.KARMA
    }

    if agent_type in critical_types:
        return (True, f"CRITICAL agent type ({agent_type}) requires quarantine")

    return (False, "Not a critical agent type")


def rule_e2_customizations_increase_risk(has_customizations: bool) -> Tuple[str, str]:
    """
    E2: Customizations increase risk tier to at least MEDIUM.

    Args:
        has_customizations: Whether request has customizations

    Returns:
        (risk_tier, reason)

    Note:
        This rule doesn't reject, it sets risk tier.

    Example:
        >>> risk_tier, reason = rule_e2_customizations_increase_risk(True)
        >>> assert risk_tier == "MEDIUM"
    """
    if has_customizations:
        return ("MEDIUM", "Customizations present, risk tier elevated to MEDIUM")

    return ("LOW", "No customizations")


def rule_e3_capability_escalation_reject(
    customization_fields: list[str]
) -> RuleResult:
    """
    E3: Capability escalations are REJECTED in Phase 2a.

    Args:
        customization_fields: List of customized field paths

    Returns:
        (approved, reason_code, reason_detail, triggered)

    Forbidden customizations:
    - capabilities.*
    - resource_limits.* (increases)
    - traits.autonomy_level (increases)
    - runtime.* (increases)

    Example:
        >>> approved, code, detail, triggered = rule_e3_capability_escalation_reject(
        ...     ["capabilities.network_access"]
        ... )
        >>> assert approved is False
    """
    forbidden_prefixes = [
        "capabilities.",
        "resource_limits.",
        "traits.autonomy_level",
        "runtime."
    ]

    for field in customization_fields:
        for prefix in forbidden_prefixes:
            if field.startswith(prefix):
                return (
                    False,
                    ReasonCode.CAPABILITY_ESCALATION_DENIED,
                    f"Capability escalation via '{field}' is DENIED in Phase 2a",
                    True
                )

    return (True, ReasonCode.APPROVED_DEFAULT, "No capability escalations", False)


# ============================================================================
# Rule Registry
# ============================================================================

# All rules with metadata
RULE_REGISTRY = {
    "A1": {
        "name": "Require SYSTEM_ADMIN role",
        "group": "A",
        "function": rule_a1_require_system_admin,
        "description": "Agent creation requires SYSTEM_ADMIN role"
    },
    "A2": {
        "name": "Kill switch check",
        "group": "A",
        "function": rule_a2_killswitch_check,
        "description": "Kill switch must not be active (Defense in Depth)"
    },
    "B1": {
        "name": "Template hash required",
        "group": "B",
        "function": rule_b1_template_hash_required,
        "description": "Template hash must exist and be valid"
    },
    "B2": {
        "name": "Template in allowlist",
        "group": "B",
        "function": rule_b2_template_in_allowlist,
        "description": "Template name must be in allowlist"
    },
    "C1": {
        "name": "Ethics human_override immutable",
        "group": "C",
        "function": rule_c1_ethics_human_override_immutable,
        "description": "ethics_flags.human_override must be 'always_allowed'"
    },
    "C2": {
        "name": "Network access cap",
        "group": "C",
        "function": rule_c2_network_access_cap,
        "description": "network_access must not exceed AgentType cap"
    },
    "C3": {
        "name": "Autonomy level cap",
        "group": "C",
        "function": rule_c3_autonomy_level_cap,
        "description": "autonomy_level must not exceed AgentType cap"
    },
    "D1": {
        "name": "Creation cost affordable",
        "group": "D",
        "function": rule_d1_creation_cost_affordable,
        "description": "Creation cost must be affordable (with reserve protection)"
    },
    "D2": {
        "name": "Population limit",
        "group": "D",
        "function": rule_d2_population_limit,
        "description": "Population limit per AgentType must not be exceeded"
    },
    "E1": {
        "name": "Critical agents quarantined",
        "group": "E",
        "function": rule_e1_critical_agents_quarantined,
        "description": "CRITICAL agents must be quarantined"
    },
    "E2": {
        "name": "Customizations increase risk",
        "group": "E",
        "function": rule_e2_customizations_increase_risk,
        "description": "Customizations elevate risk tier to at least MEDIUM"
    },
    "E3": {
        "name": "Capability escalation rejected",
        "group": "E",
        "function": rule_e3_capability_escalation_reject,
        "description": "Capability escalations are DENIED in Phase 2a"
    },
}
