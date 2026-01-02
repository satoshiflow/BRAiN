"""
Reduction Rules (Phase 2b)

Condition-based rules for applying constraint reductions.

These are pure functions that evaluate conditions and return whether
a specific reduction should be applied.

Rule Groups:
- Customization Rules: Apply when agent has customizations
- Risk Rules: Apply when agent is high risk
- Environment Rules: Apply based on deployment environment
- Population Rules: Apply based on agent population pressure

Author: Governor v1 System (Phase 2b)
Version: 2b.1
Created: 2026-01-02
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.brain.agents.genesis_agent.dna_schema import AgentType
from backend.brain.governor.decision.models import RiskTier
from backend.brain.governor.manifests.schema import ReductionSections


# ============================================================================
# Reduction Condition Evaluation
# ============================================================================

def should_apply_customization_reduction(
    has_customizations: bool,
    customization_fields: list[str]
) -> bool:
    """
    Determine if customization reduction should be applied.

    Args:
        has_customizations: Whether request has customizations
        customization_fields: List of customized field paths

    Returns:
        True if reduction should be applied

    Example:
        >>> should_apply_customization_reduction(True, ["metadata.name"])
        True
        >>> should_apply_customization_reduction(False, [])
        False
    """
    return has_customizations and len(customization_fields) > 0


def should_apply_high_risk_reduction(
    risk_tier: RiskTier
) -> bool:
    """
    Determine if high-risk reduction should be applied.

    Args:
        risk_tier: Current risk tier (LOW, MEDIUM, HIGH, CRITICAL)

    Returns:
        True if reduction should be applied

    Note:
        Applies to HIGH and CRITICAL risk tiers only.

    Example:
        >>> should_apply_high_risk_reduction(RiskTier.HIGH)
        True
        >>> should_apply_high_risk_reduction(RiskTier.MEDIUM)
        False
    """
    return risk_tier in [RiskTier.HIGH, RiskTier.CRITICAL]


def should_apply_production_reduction(
    environment: Optional[str],
    agent_dna: Dict[str, Any]
) -> bool:
    """
    Determine if production environment reduction should be applied.

    Args:
        environment: Deployment environment (from context)
        agent_dna: Agent DNA dictionary (check for production markers)

    Returns:
        True if reduction should be applied

    Note:
        Checks both explicit environment field and DNA metadata for production markers.

    Example:
        >>> should_apply_production_reduction("production", {})
        True
        >>> should_apply_production_reduction("development", {})
        False
    """
    # Check explicit environment
    if environment and environment.lower() == "production":
        return True

    # Check DNA metadata for production markers
    metadata = agent_dna.get("metadata", {})
    tags = metadata.get("tags", [])

    if "production" in tags or "prod" in tags:
        return True

    # Check if deployment target is production
    deployment_target = metadata.get("deployment_target", "")
    if deployment_target and deployment_target.lower() == "production":
        return True

    return False


def should_apply_population_pressure_reduction(
    agent_type: AgentType,
    current_population: int,
    max_population: Dict[AgentType, int],
    threshold: float = 0.8
) -> bool:
    """
    Determine if population pressure reduction should be applied.

    Args:
        agent_type: Agent type being created
        current_population: Current count of this AgentType
        max_population: Max population per AgentType
        threshold: Pressure threshold (default: 0.8 = 80%)

    Returns:
        True if reduction should be applied

    Note:
        Applies when current population exceeds threshold% of max population.

    Example:
        >>> max_pop = {AgentType.WORKER: 100}
        >>> should_apply_population_pressure_reduction(AgentType.WORKER, 85, max_pop, 0.8)
        True  # 85/100 = 85% > 80%
        >>> should_apply_population_pressure_reduction(AgentType.WORKER, 75, max_pop, 0.8)
        False  # 75/100 = 75% < 80%
    """
    limit = max_population.get(agent_type, float('inf'))

    # If no limit, no pressure
    if limit == float('inf'):
        return False

    # Calculate population ratio
    population_ratio = current_population / limit

    # Apply reduction if over threshold
    return population_ratio >= threshold


# ============================================================================
# Reduction Application Order
# ============================================================================

class ReductionContext:
    """
    Context for evaluating which reductions to apply.

    Aggregates all information needed to determine which reduction rules
    should be applied.
    """

    def __init__(
        self,
        has_customizations: bool,
        customization_fields: list[str],
        risk_tier: RiskTier,
        agent_type: AgentType,
        agent_dna: Dict[str, Any],
        current_population: int,
        max_population: Dict[AgentType, int],
        environment: Optional[str] = None
    ):
        self.has_customizations = has_customizations
        self.customization_fields = customization_fields
        self.risk_tier = risk_tier
        self.agent_type = agent_type
        self.agent_dna = agent_dna
        self.current_population = current_population
        self.max_population = max_population
        self.environment = environment


def get_applicable_reductions(
    context: ReductionContext,
    reduction_sections: ReductionSections
) -> list[tuple[str, Any]]:
    """
    Determine which reductions should be applied based on context.

    Args:
        context: ReductionContext with all evaluation inputs
        reduction_sections: ReductionSections from manifest

    Returns:
        List of (section_name, ReductionSpec) tuples in application order

    Note:
        Reductions are returned in priority order:
        1. on_customization
        2. on_high_risk
        3. on_production
        4. on_population_pressure

        Later reductions may further reduce already-reduced constraints.

    Example:
        >>> applicable = get_applicable_reductions(context, reduction_sections)
        >>> for section_name, spec in applicable:
        ...     print(f"Applying {section_name}")
        Applying on_customization
        Applying on_high_risk
    """
    applicable = []

    # 1. Customization reductions
    if should_apply_customization_reduction(
        context.has_customizations,
        context.customization_fields
    ):
        if reduction_sections.on_customization:
            applicable.append(("on_customization", reduction_sections.on_customization))

    # 2. High-risk reductions
    if should_apply_high_risk_reduction(context.risk_tier):
        if reduction_sections.on_high_risk:
            applicable.append(("on_high_risk", reduction_sections.on_high_risk))

    # 3. Production environment reductions
    if should_apply_production_reduction(context.environment, context.agent_dna):
        if reduction_sections.on_production:
            applicable.append(("on_production", reduction_sections.on_production))

    # 4. Population pressure reductions
    if should_apply_population_pressure_reduction(
        context.agent_type,
        context.current_population,
        context.max_population
    ):
        if reduction_sections.on_population_pressure:
            applicable.append(("on_population_pressure", reduction_sections.on_population_pressure))

    return applicable


# ============================================================================
# Rule Metadata Registry
# ============================================================================

REDUCTION_RULES = {
    "on_customization": {
        "name": "Customization Reduction",
        "description": "Apply when agent has DNA customizations",
        "function": should_apply_customization_reduction,
        "priority": 1
    },
    "on_high_risk": {
        "name": "High Risk Reduction",
        "description": "Apply when agent is HIGH or CRITICAL risk",
        "function": should_apply_high_risk_reduction,
        "priority": 2
    },
    "on_production": {
        "name": "Production Environment Reduction",
        "description": "Apply when agent is deployed to production",
        "function": should_apply_production_reduction,
        "priority": 3
    },
    "on_population_pressure": {
        "name": "Population Pressure Reduction",
        "description": "Apply when agent population exceeds 80% of limit",
        "function": should_apply_population_pressure_reduction,
        "priority": 4
    },
}
