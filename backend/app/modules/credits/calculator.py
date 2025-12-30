"""Credit Calculator - Deterministic skill-based credit computation.

Implements Myzel-Hybrid-Charta principles:
- Deterministic formulas (no arbitrary rewards)
- Skill-based allocation (KARMA integration)
- Cooperation incentives (not competition)
- Edge-of-Chaos regulation integration
"""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)


class CreditCalculator:
    """Deterministic credit calculator for Myzel-Hybrid system.

    Credit allocation follows deterministic formulas based on:
    - Entity type (agent, mission)
    - Skill levels (KARMA integration)
    - System health (Edge-of-Chaos score)
    - Cooperation metrics (not competition)
    """

    # Base credit allocations (Myzel-Hybrid: sufficient for operation)
    BASE_AGENT_CREDITS = 100.0  # Initial agent allocation
    BASE_MISSION_CREDITS = 50.0  # Mission execution budget

    # Regeneration rates (per hour)
    BASE_REGENERATION_RATE = 5.0  # Base regeneration per hour

    # Skill multipliers (KARMA integration)
    SKILL_MULTIPLIER_MIN = 0.8  # Novice agents
    SKILL_MULTIPLIER_MAX = 1.5  # Expert agents

    # Edge-of-Chaos multipliers (0.5-0.7 is optimal)
    EOC_OPTIMAL_MIN = 0.5
    EOC_OPTIMAL_MAX = 0.7
    EOC_PENALTY_FACTOR = 0.5  # Reduce regeneration if outside optimal range

    # Consumption rates
    MISSION_BASE_COST = 10.0  # Base cost per mission
    MISSION_COMPLEXITY_FACTOR = 2.0  # Multiplier per complexity point

    def calculate_agent_allocation(
        self,
        agent_id: str,
        skill_level: Optional[float] = None,
    ) -> float:
        """Calculate initial credit allocation for new agent.

        Args:
            agent_id: Agent identifier
            skill_level: Skill level (0.0-1.0), None = default (0.5)

        Returns:
            Initial credit allocation
        """
        # Default skill level (average)
        if skill_level is None:
            skill_level = 0.5

        # Clamp skill level
        skill_level = max(0.0, min(1.0, skill_level))

        # Skill multiplier (linear interpolation)
        skill_multiplier = (
            self.SKILL_MULTIPLIER_MIN +
            (self.SKILL_MULTIPLIER_MAX - self.SKILL_MULTIPLIER_MIN) * skill_level
        )

        allocation = self.BASE_AGENT_CREDITS * skill_multiplier

        logger.info(
            f"[CreditCalculator] Agent {agent_id} allocation: "
            f"{allocation:.2f} credits (skill: {skill_level:.2f}, "
            f"multiplier: {skill_multiplier:.2f})"
        )

        return allocation

    def calculate_mission_allocation(
        self,
        mission_id: str,
        complexity: float = 1.0,
        estimated_duration_hours: float = 1.0,
    ) -> float:
        """Calculate credit allocation for mission execution.

        Args:
            mission_id: Mission identifier
            complexity: Mission complexity (0.5-5.0)
            estimated_duration_hours: Estimated duration in hours

        Returns:
            Mission credit allocation
        """
        # Clamp complexity
        complexity = max(0.5, min(5.0, complexity))

        # Base cost + complexity factor + duration factor
        allocation = (
            self.MISSION_BASE_COST +
            (self.MISSION_COMPLEXITY_FACTOR * complexity) +
            (self.BASE_REGENERATION_RATE * estimated_duration_hours * 0.5)
        )

        logger.info(
            f"[CreditCalculator] Mission {mission_id} allocation: "
            f"{allocation:.2f} credits (complexity: {complexity:.1f}, "
            f"duration: {estimated_duration_hours:.1f}h)"
        )

        return allocation

    def calculate_regeneration(
        self,
        entity_id: str,
        current_balance: float,
        hours_elapsed: float,
        edge_of_chaos_score: Optional[float] = None,
    ) -> float:
        """Calculate credit regeneration amount.

        Myzel-Hybrid: Regeneration is regulated by Edge-of-Chaos score.
        - Optimal range (0.5-0.7): Full regeneration
        - Outside optimal: Reduced regeneration (system self-regulation)

        Args:
            entity_id: Entity identifier
            current_balance: Current credit balance
            hours_elapsed: Time elapsed since last regeneration
            edge_of_chaos_score: Current Edge-of-Chaos score (0.0-1.0)

        Returns:
            Credit regeneration amount
        """
        # Base regeneration
        base_regen = self.BASE_REGENERATION_RATE * hours_elapsed

        # Edge-of-Chaos regulation
        eoc_multiplier = 1.0
        if edge_of_chaos_score is not None:
            if self.EOC_OPTIMAL_MIN <= edge_of_chaos_score <= self.EOC_OPTIMAL_MAX:
                # Optimal range: full regeneration
                eoc_multiplier = 1.0
            else:
                # Outside optimal: penalty (system self-regulation)
                distance_from_optimal = min(
                    abs(edge_of_chaos_score - self.EOC_OPTIMAL_MIN),
                    abs(edge_of_chaos_score - self.EOC_OPTIMAL_MAX),
                )
                eoc_multiplier = 1.0 - (distance_from_optimal * self.EOC_PENALTY_FACTOR)
                eoc_multiplier = max(0.2, eoc_multiplier)  # Minimum 20% regeneration

        regeneration = base_regen * eoc_multiplier

        logger.debug(
            f"[CreditCalculator] {entity_id} regeneration: "
            f"{regeneration:.2f} credits ({hours_elapsed:.2f}h, "
            f"EoC: {edge_of_chaos_score:.3f if edge_of_chaos_score else 'N/A'}, "
            f"multiplier: {eoc_multiplier:.2f})"
        )

        return regeneration

    def calculate_mission_cost(
        self,
        mission_id: str,
        complexity: float = 1.0,
        actual_duration_hours: Optional[float] = None,
    ) -> float:
        """Calculate actual mission execution cost.

        Args:
            mission_id: Mission identifier
            complexity: Mission complexity (0.5-5.0)
            actual_duration_hours: Actual execution time (None = use estimate)

        Returns:
            Mission execution cost
        """
        # Use same formula as allocation (deterministic)
        if actual_duration_hours is None:
            actual_duration_hours = 1.0

        return self.calculate_mission_allocation(
            mission_id=mission_id,
            complexity=complexity,
            estimated_duration_hours=actual_duration_hours,
        )

    def calculate_refund(
        self,
        original_allocation: float,
        work_completed_percentage: float,
    ) -> float:
        """Calculate refund for cancelled/reused mission.

        Myzel-Hybrid: Synergie-Mechanik (reuse bonus)

        Args:
            original_allocation: Original credit allocation
            work_completed_percentage: Percentage of work completed (0.0-1.0)

        Returns:
            Refund amount
        """
        # Refund unused portion
        work_completed_percentage = max(0.0, min(1.0, work_completed_percentage))
        unused_portion = 1.0 - work_completed_percentage

        refund = original_allocation * unused_portion

        logger.info(
            f"[CreditCalculator] Refund: {refund:.2f} credits "
            f"({unused_portion * 100:.0f}% of {original_allocation:.2f})"
        )

        return refund

    def calculate_cooperation_bonus(
        self,
        entity_id: str,
        collaborations_count: int,
        shared_resources_count: int,
    ) -> float:
        """Calculate cooperation bonus (Myzel-Hybrid incentive).

        Myzel-Hybrid: Reward cooperation, not competition.

        Args:
            entity_id: Entity identifier
            collaborations_count: Number of collaborations
            shared_resources_count: Number of resources shared

        Returns:
            Cooperation bonus credits
        """
        # Cooperation bonus formula
        collaboration_bonus = collaborations_count * 2.0
        sharing_bonus = shared_resources_count * 1.5

        total_bonus = collaboration_bonus + sharing_bonus

        if total_bonus > 0:
            logger.info(
                f"[CreditCalculator] {entity_id} cooperation bonus: "
                f"{total_bonus:.2f} credits "
                f"({collaborations_count} collaborations, "
                f"{shared_resources_count} shared resources)"
            )

        return total_bonus

    def calculate_withdrawal_amount(
        self,
        entity_id: str,
        current_balance: float,
        severity: str,
    ) -> float:
        """Calculate credit withdrawal amount (Immune System Entzug).

        Myzel-Hybrid: Credit withdrawal as governance mechanism.

        Args:
            entity_id: Entity identifier
            current_balance: Current credit balance
            severity: Severity level ("low", "medium", "high", "critical")

        Returns:
            Withdrawal amount (positive)
        """
        # Severity-based withdrawal percentages
        withdrawal_percentages = {
            "low": 0.10,  # 10% withdrawal
            "medium": 0.25,  # 25% withdrawal
            "high": 0.50,  # 50% withdrawal
            "critical": 0.75,  # 75% withdrawal
        }

        percentage = withdrawal_percentages.get(severity, 0.25)
        withdrawal = current_balance * percentage

        logger.warning(
            f"[CreditCalculator] {entity_id} withdrawal: "
            f"{withdrawal:.2f} credits ({severity} severity, "
            f"{percentage * 100:.0f}% of {current_balance:.2f})"
        )

        return withdrawal


# Global calculator instance
_calculator: Optional[CreditCalculator] = None


def get_calculator() -> CreditCalculator:
    """Get global credit calculator instance.

    Returns:
        CreditCalculator instance
    """
    global _calculator
    if _calculator is None:
        _calculator = CreditCalculator()
    return _calculator
