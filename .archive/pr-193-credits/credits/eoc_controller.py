"""Edge-of-Chaos Controller - Dynamic system regulation.

Implements Myzel-Hybrid-Charta principles:
- Passive regulation (no active intervention)
- Credit flow modulation based on system state
- Fail-closed mechanisms
- Human approval for structural changes
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class SystemState(str, Enum):
    """System state based on Edge-of-Chaos score."""

    TOO_ORDERED = "too_ordered"      # Score < 0.5: System too rigid
    OPTIMAL = "optimal"               # Score 0.5-0.7: Optimal range
    TOO_CHAOTIC = "too_chaotic"       # Score > 0.7: System too unstable
    UNKNOWN = "unknown"               # Score unavailable


class RegulationAction(str, Enum):
    """Regulation actions (passive, non-interventionist)."""

    NONE = "none"                     # No action needed (optimal state)
    REDUCE_REGENERATION = "reduce_regeneration"  # Reduce credit flow
    INCREASE_REGENERATION = "increase_regeneration"  # Increase credit flow
    ENABLE_BACKPRESSURE = "enable_backpressure"  # Queue limiting
    THROTTLE_MISSIONS = "throttle_missions"  # Slow down mission execution
    HUMAN_REVIEW_REQUIRED = "human_review_required"  # Structural change needed


class EdgeOfChaosController:
    """Dynamic system regulation based on Edge-of-Chaos metrics.

    Myzel-Hybrid Principles:
    - Passive regulation (modulate credit flow, don't force changes)
    - Fail-closed (reduce activity when uncertain)
    - Human approval for structural changes (agent creation/deletion)
    - Transparent decision-making

    Regulation Strategy:
    - TOO_ORDERED (< 0.5): Increase credit regeneration, encourage activity
    - OPTIMAL (0.5-0.7): Maintain current settings
    - TOO_CHAOTIC (> 0.7): Reduce regeneration, enable backpressure
    """

    # Edge-of-Chaos thresholds
    EOC_OPTIMAL_MIN = 0.5
    EOC_OPTIMAL_MAX = 0.7
    EOC_CRITICAL_HIGH = 0.85  # Critical chaos level
    EOC_CRITICAL_LOW = 0.3    # Critical order level

    # Regeneration rate multipliers
    REGEN_MULTIPLIER_MIN = 0.5  # Minimum regeneration (too chaotic)
    REGEN_MULTIPLIER_MAX = 1.5  # Maximum regeneration (too ordered)
    REGEN_MULTIPLIER_OPTIMAL = 1.0  # Optimal regeneration

    def __init__(self):
        self.regulation_history: List[Dict] = []
        self.current_regen_multiplier = 1.0
        self.backpressure_enabled = False
        self.last_regulation_time: Optional[datetime] = None

        logger.info("[EdgeOfChaosController] Initialized")

    async def regulate(
        self,
        edge_of_chaos_score: Optional[float],
        system_metrics: Optional[Dict] = None,
    ) -> Dict:
        """Regulate system based on Edge-of-Chaos score.

        Args:
            edge_of_chaos_score: Current Edge-of-Chaos score (0.0-1.0)
            system_metrics: Additional system metrics

        Returns:
            Regulation decision with recommended actions
        """
        decision = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "eoc_score": edge_of_chaos_score,
            "system_state": SystemState.UNKNOWN,
            "actions": [],
            "regen_multiplier": self.current_regen_multiplier,
            "reasoning": "",
            "human_approval_required": False,
        }

        # Handle missing score (fail-closed)
        if edge_of_chaos_score is None:
            decision["system_state"] = SystemState.UNKNOWN
            decision["actions"].append(RegulationAction.REDUCE_REGENERATION)
            decision["reasoning"] = "Edge-of-Chaos score unavailable - fail-closed (reduce activity)"
            decision["regen_multiplier"] = 0.8

            await self._apply_regulation(decision)
            return decision

        # Determine system state
        if edge_of_chaos_score < self.EOC_OPTIMAL_MIN:
            decision["system_state"] = SystemState.TOO_ORDERED
        elif edge_of_chaos_score > self.EOC_OPTIMAL_MAX:
            decision["system_state"] = SystemState.TOO_CHAOTIC
        else:
            decision["system_state"] = SystemState.OPTIMAL

        # Regulation logic
        if decision["system_state"] == SystemState.OPTIMAL:
            # Optimal range: no intervention needed
            decision["actions"].append(RegulationAction.NONE)
            decision["reasoning"] = f"System in optimal range ({edge_of_chaos_score:.3f})"
            decision["regen_multiplier"] = self.REGEN_MULTIPLIER_OPTIMAL

        elif decision["system_state"] == SystemState.TOO_ORDERED:
            # Too rigid: increase activity
            if edge_of_chaos_score < self.EOC_CRITICAL_LOW:
                # Critical: structural change may be needed
                decision["actions"].append(RegulationAction.INCREASE_REGENERATION)
                decision["actions"].append(RegulationAction.HUMAN_REVIEW_REQUIRED)
                decision["reasoning"] = (
                    f"System critically too ordered ({edge_of_chaos_score:.3f} < {self.EOC_CRITICAL_LOW}). "
                    f"Increasing regeneration + human review for structural changes (e.g., add agents)"
                )
                decision["regen_multiplier"] = self.REGEN_MULTIPLIER_MAX
                decision["human_approval_required"] = True
            else:
                # Mild: just increase regeneration
                decision["actions"].append(RegulationAction.INCREASE_REGENERATION)
                decision["reasoning"] = (
                    f"System too ordered ({edge_of_chaos_score:.3f} < {self.EOC_OPTIMAL_MIN}). "
                    f"Increasing credit regeneration to encourage activity"
                )
                # Linear interpolation between optimal and max
                distance_from_optimal = self.EOC_OPTIMAL_MIN - edge_of_chaos_score
                max_distance = self.EOC_OPTIMAL_MIN - self.EOC_CRITICAL_LOW
                multiplier_increase = (distance_from_optimal / max_distance) * (
                    self.REGEN_MULTIPLIER_MAX - self.REGEN_MULTIPLIER_OPTIMAL
                )
                decision["regen_multiplier"] = self.REGEN_MULTIPLIER_OPTIMAL + multiplier_increase

        elif decision["system_state"] == SystemState.TOO_CHAOTIC:
            # Too unstable: reduce activity
            if edge_of_chaos_score > self.EOC_CRITICAL_HIGH:
                # Critical: emergency measures
                decision["actions"].append(RegulationAction.REDUCE_REGENERATION)
                decision["actions"].append(RegulationAction.ENABLE_BACKPRESSURE)
                decision["actions"].append(RegulationAction.THROTTLE_MISSIONS)
                decision["actions"].append(RegulationAction.HUMAN_REVIEW_REQUIRED)
                decision["reasoning"] = (
                    f"System critically too chaotic ({edge_of_chaos_score:.3f} > {self.EOC_CRITICAL_HIGH}). "
                    f"Emergency: reducing regeneration + backpressure + throttling + human review"
                )
                decision["regen_multiplier"] = self.REGEN_MULTIPLIER_MIN
                decision["human_approval_required"] = True
            else:
                # Mild: reduce regeneration and enable backpressure
                decision["actions"].append(RegulationAction.REDUCE_REGENERATION)
                decision["actions"].append(RegulationAction.ENABLE_BACKPRESSURE)
                decision["reasoning"] = (
                    f"System too chaotic ({edge_of_chaos_score:.3f} > {self.EOC_OPTIMAL_MAX}). "
                    f"Reducing credit regeneration and enabling backpressure"
                )
                # Linear interpolation between optimal and min
                distance_from_optimal = edge_of_chaos_score - self.EOC_OPTIMAL_MAX
                max_distance = self.EOC_CRITICAL_HIGH - self.EOC_OPTIMAL_MAX
                multiplier_decrease = (distance_from_optimal / max_distance) * (
                    self.REGEN_MULTIPLIER_OPTIMAL - self.REGEN_MULTIPLIER_MIN
                )
                decision["regen_multiplier"] = self.REGEN_MULTIPLIER_OPTIMAL - multiplier_decrease

        # Apply regulation
        await self._apply_regulation(decision)

        # Log decision
        logger.info(
            f"[EdgeOfChaosController] Regulation: {decision['system_state']} "
            f"(score: {edge_of_chaos_score:.3f}, multiplier: {decision['regen_multiplier']:.2f}) "
            f"- Actions: {[a.value for a in decision['actions']]}"
        )

        # Record in history
        self.regulation_history.append(decision)
        self.last_regulation_time = datetime.now(timezone.utc)

        return decision

    async def _apply_regulation(self, decision: Dict):
        """Apply regulation decision to system.

        Args:
            decision: Regulation decision dictionary
        """
        # Update regeneration multiplier
        self.current_regen_multiplier = decision["regen_multiplier"]

        # Apply backpressure if needed
        if RegulationAction.ENABLE_BACKPRESSURE in decision["actions"]:
            if not self.backpressure_enabled:
                self.backpressure_enabled = True
                logger.warning("[EdgeOfChaosController] Backpressure enabled")

                # Notify ImmuneService (optional integration)
                try:
                    from backend.app.modules.immune.core.service import get_immune_service
                    immune = get_immune_service()
                    await immune._enable_backpressure()
                except Exception as e:
                    logger.debug(f"[EdgeOfChaosController] ImmuneService integration failed: {e}")
        else:
            # Disable backpressure if not in chaotic state
            if self.backpressure_enabled and decision["system_state"] != SystemState.TOO_CHAOTIC:
                self.backpressure_enabled = False
                logger.info("[EdgeOfChaosController] Backpressure disabled")

    def get_current_multiplier(self) -> float:
        """Get current regeneration multiplier.

        Returns:
            Current regeneration rate multiplier
        """
        return self.current_regen_multiplier

    def get_regulation_status(self) -> Dict:
        """Get current regulation status.

        Returns:
            Status dictionary
        """
        return {
            "current_regen_multiplier": self.current_regen_multiplier,
            "backpressure_enabled": self.backpressure_enabled,
            "last_regulation_time": self.last_regulation_time.isoformat() if self.last_regulation_time else None,
            "regulation_history_count": len(self.regulation_history),
        }

    def get_regulation_history(self, limit: int = 50) -> List[Dict]:
        """Get recent regulation history.

        Args:
            limit: Maximum number of entries

        Returns:
            List of regulation decisions (newest first)
        """
        return list(reversed(self.regulation_history[-limit:]))

    async def request_human_approval(
        self,
        action_type: str,
        reason: str,
        context: Dict,
    ) -> Dict:
        """Request human approval for structural changes.

        Myzel-Hybrid: Human-in-the-loop for irreversible actions.

        Args:
            action_type: Type of structural change (e.g., "add_agent", "remove_agent")
            reason: Reason for change
            context: Additional context

        Returns:
            Approval request with token
        """
        approval_token = f"APPROVAL_{datetime.now(timezone.utc).timestamp():.0f}"

        request = {
            "approval_token": approval_token,
            "action_type": action_type,
            "reason": reason,
            "context": context,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
        }

        logger.warning(
            f"[EdgeOfChaosController] Human approval required: {action_type} - {reason} "
            f"(token: {approval_token})"
        )

        # TODO: Integration with approval system (Policy Engine, Supervisor, Control Deck UI)

        return request


# Global controller instance
_controller: Optional[EdgeOfChaosController] = None


def get_eoc_controller() -> EdgeOfChaosController:
    """Get global Edge-of-Chaos controller instance.

    Returns:
        EdgeOfChaosController instance
    """
    global _controller
    if _controller is None:
        _controller = EdgeOfChaosController()
    return _controller
