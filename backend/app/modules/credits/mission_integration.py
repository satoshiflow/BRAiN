"""
Mission System Integration for Credits.

Automatically consumes/refunds credits based on mission lifecycle:
- Mission Start → Consume credits
- Mission Complete → No action (credits already consumed)
- Mission Failed → Refund credits
- Mission Cancelled → Refund credits

Usage:
    from app.modules.credits.mission_integration import (
        MissionCreditHooks,
        register_mission_hooks,
    )

    # Register hooks on app startup
    await register_mission_hooks()

    # Mission lifecycle automatically triggers credit operations
"""

from __future__ import annotations

from typing import Dict, Optional

from loguru import logger

from app.modules.credits.service import (
    consume_agent_credits,
    refund_agent_credits,
    get_agent_balance,
    EVENTSOURCING_AVAILABLE,
)


class MissionCreditHooks:
    """
    Hooks for mission lifecycle events.

    Automatically manages credits based on mission state transitions.
    """

    @staticmethod
    async def on_mission_start(
        mission_id: str,
        agent_id: str,
        estimated_cost: float,
        mission_type: str = "general",
    ) -> Dict:
        """
        Hook called when mission starts.

        Consumes credits from agent based on estimated cost.

        Args:
            mission_id: Mission identifier
            agent_id: Agent executing mission
            estimated_cost: Estimated credits for mission
            mission_type: Type of mission

        Returns:
            Dict with consumed credits and balance_after

        Raises:
            ValueError: If insufficient credits or Event Sourcing unavailable
        """
        if not EVENTSOURCING_AVAILABLE:
            logger.warning(
                "Event Sourcing unavailable, skipping mission credit consumption",
                mission_id=mission_id,
            )
            return {
                "consumed": 0.0,
                "balance_after": 0.0,
                "event_sourcing_available": False,
            }

        try:
            # Check current balance
            balance_info = await get_agent_balance(agent_id)
            current_balance = balance_info["balance"]

            if current_balance < estimated_cost:
                raise ValueError(
                    f"Insufficient credits: {agent_id} has {current_balance}, "
                    f"needs {estimated_cost} for mission {mission_id}"
                )

            # Consume credits
            result = await consume_agent_credits(
                agent_id=agent_id,
                amount=estimated_cost,
                reason=f"Mission start: {mission_type}",
                mission_id=mission_id,
                actor_id="mission_system",
            )

            logger.info(
                f"Credits consumed for mission start",
                mission_id=mission_id,
                agent_id=agent_id,
                amount=estimated_cost,
                balance_after=result["balance_after"],
            )

            return {
                "consumed": result["amount"],
                "balance_after": result["balance_after"],
                "event_sourcing_available": True,
            }

        except Exception as e:
            logger.error(
                f"Failed to consume credits for mission start: {e}",
                mission_id=mission_id,
                agent_id=agent_id,
                exc_info=True,
            )
            raise

    @staticmethod
    async def on_mission_complete(
        mission_id: str,
        agent_id: str,
        actual_cost: float,
        estimated_cost: float,
    ) -> Dict:
        """
        Hook called when mission completes successfully.

        If actual cost < estimated cost, refund the difference.

        Args:
            mission_id: Mission identifier
            agent_id: Agent who executed mission
            actual_cost: Actual credits consumed
            estimated_cost: Original estimate

        Returns:
            Dict with refund amount and balance_after
        """
        if not EVENTSOURCING_AVAILABLE:
            return {
                "refunded": 0.0,
                "balance_after": 0.0,
                "event_sourcing_available": False,
            }

        try:
            refund_amount = estimated_cost - actual_cost

            if refund_amount > 0:
                result = await refund_agent_credits(
                    agent_id=agent_id,
                    amount=refund_amount,
                    reason=f"Mission complete: refund difference",
                    mission_id=mission_id,
                    actor_id="mission_system",
                )

                logger.info(
                    f"Credits refunded for mission completion",
                    mission_id=mission_id,
                    agent_id=agent_id,
                    refund_amount=refund_amount,
                    balance_after=result["balance_after"],
                )

                return {
                    "refunded": result["amount"],
                    "balance_after": result["balance_after"],
                    "event_sourcing_available": True,
                }

            # No refund needed
            return {
                "refunded": 0.0,
                "balance_after": 0.0,
                "event_sourcing_available": True,
            }

        except Exception as e:
            logger.error(
                f"Failed to refund credits for mission completion: {e}",
                mission_id=mission_id,
                agent_id=agent_id,
                exc_info=True,
            )
            # Non-critical error (mission already completed)
            return {
                "refunded": 0.0,
                "balance_after": 0.0,
                "error": str(e),
            }

    @staticmethod
    async def on_mission_failed(
        mission_id: str,
        agent_id: str,
        consumed_credits: float,
        refund_percentage: float = 1.0,
    ) -> Dict:
        """
        Hook called when mission fails.

        Refunds credits (default: 100%, configurable).

        Args:
            mission_id: Mission identifier
            agent_id: Agent who executed mission
            consumed_credits: Credits that were consumed
            refund_percentage: Percentage to refund (0.0 - 1.0)

        Returns:
            Dict with refund amount and balance_after
        """
        if not EVENTSOURCING_AVAILABLE:
            return {
                "refunded": 0.0,
                "balance_after": 0.0,
                "event_sourcing_available": False,
            }

        try:
            refund_amount = consumed_credits * refund_percentage

            result = await refund_agent_credits(
                agent_id=agent_id,
                amount=refund_amount,
                reason=f"Mission failed: {refund_percentage * 100}% refund",
                mission_id=mission_id,
                actor_id="mission_system",
            )

            logger.info(
                f"Credits refunded for mission failure",
                mission_id=mission_id,
                agent_id=agent_id,
                refund_amount=refund_amount,
                balance_after=result["balance_after"],
            )

            return {
                "refunded": result["amount"],
                "balance_after": result["balance_after"],
                "event_sourcing_available": True,
            }

        except Exception as e:
            logger.error(
                f"Failed to refund credits for mission failure: {e}",
                mission_id=mission_id,
                agent_id=agent_id,
                exc_info=True,
            )
            # Non-critical error
            return {
                "refunded": 0.0,
                "balance_after": 0.0,
                "error": str(e),
            }

    @staticmethod
    async def on_mission_cancelled(
        mission_id: str,
        agent_id: str,
        consumed_credits: float,
    ) -> Dict:
        """
        Hook called when mission is cancelled.

        Refunds all consumed credits.

        Args:
            mission_id: Mission identifier
            agent_id: Agent assigned to mission
            consumed_credits: Credits that were consumed

        Returns:
            Dict with refund amount and balance_after
        """
        return await MissionCreditHooks.on_mission_failed(
            mission_id=mission_id,
            agent_id=agent_id,
            consumed_credits=consumed_credits,
            refund_percentage=1.0,
        )


# ============================================================================
# Hook Registration
# ============================================================================

async def register_mission_hooks() -> None:
    """
    Register mission hooks with mission system.

    Note:
        - Requires mission system to support hooks
        - Gracefully handles missing mission system
    """
    if not EVENTSOURCING_AVAILABLE:
        logger.info("Event Sourcing unavailable, mission hooks not registered")
        return

    try:
        # Try to import mission system
        try:
            from backend.modules.mission_system import register_hooks
        except ImportError:
            logger.warning("Mission system not available, hooks not registered")
            return

        # Register hooks
        await register_hooks(
            on_start=MissionCreditHooks.on_mission_start,
            on_complete=MissionCreditHooks.on_mission_complete,
            on_failed=MissionCreditHooks.on_mission_failed,
            on_cancelled=MissionCreditHooks.on_mission_cancelled,
        )

        logger.info("Mission credit hooks registered successfully")

    except Exception as e:
        logger.error(f"Failed to register mission hooks: {e}", exc_info=True)


# ============================================================================
# Cost Estimation
# ============================================================================

def estimate_mission_cost(
    mission_type: str,
    complexity: str = "medium",
    agent_skill_level: float = 0.5,
) -> float:
    """
    Estimate credit cost for mission.

    Formula:
        base_cost * complexity_multiplier * skill_adjustment

    Args:
        mission_type: Type of mission
        complexity: Complexity level (low, medium, high)
        agent_skill_level: Agent skill (0.0 - 1.0)

    Returns:
        Estimated credits needed
    """
    # Base costs by mission type
    base_costs = {
        "general": 10.0,
        "code_review": 15.0,
        "deployment": 20.0,
        "research": 25.0,
        "architecture": 30.0,
    }

    # Complexity multipliers
    complexity_multipliers = {
        "low": 0.5,
        "medium": 1.0,
        "high": 2.0,
    }

    # Skill adjustment (higher skill = lower cost)
    skill_adjustment = 1.0 - (agent_skill_level * 0.3)

    base_cost = base_costs.get(mission_type, 10.0)
    complexity_mult = complexity_multipliers.get(complexity, 1.0)

    estimated_cost = base_cost * complexity_mult * skill_adjustment

    return round(estimated_cost, 1)
