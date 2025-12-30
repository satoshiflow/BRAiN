"""Entity Lifecycle Manager - Credit lifecycle for agents and missions.

Implements Myzel-Hybrid-Charta principles:
- Automatic credit allocation on creation
- Periodic regeneration based on system health
- Credit withdrawal on violations
- Transparent lifecycle events
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from dataclasses import dataclass

from .ledger import get_ledger, TransactionType
from .calculator import get_calculator

logger = logging.getLogger(__name__)


@dataclass
class EntityState:
    """Entity lifecycle state."""

    entity_id: str
    entity_type: str  # "agent" or "mission"
    created_at: datetime
    last_regeneration: datetime
    skill_level: Optional[float] = None
    is_active: bool = True


class EntityLifecycleManager:
    """Manages credit lifecycle for agents and missions.

    Responsibilities:
    - Initial credit allocation
    - Periodic regeneration (background task)
    - Credit consumption tracking
    - Entity deactivation
    """

    def __init__(self):
        self.ledger = get_ledger()
        self.calculator = get_calculator()
        self.entities: Dict[str, EntityState] = {}
        self.regeneration_task: Optional[asyncio.Task] = None
        self.regeneration_interval_seconds = 300  # 5 minutes (0.083 hours)

    async def create_agent(
        self,
        agent_id: str,
        skill_level: Optional[float] = None,
    ) -> float:
        """Create new agent with initial credit allocation.

        Args:
            agent_id: Agent identifier
            skill_level: Skill level (0.0-1.0)

        Returns:
            Initial credit balance
        """
        if agent_id in self.entities:
            raise ValueError(f"Agent {agent_id} already exists")

        # Calculate initial allocation
        allocation = self.calculator.calculate_agent_allocation(
            agent_id=agent_id,
            skill_level=skill_level,
        )

        # Record in ledger
        entry = self.ledger.append(
            transaction_type=TransactionType.ALLOCATION,
            entity_id=agent_id,
            entity_type="agent",
            amount=allocation,
            reason="Initial agent allocation",
            metadata={"skill_level": skill_level},
        )

        # Track entity state
        now = datetime.now(timezone.utc)
        self.entities[agent_id] = EntityState(
            entity_id=agent_id,
            entity_type="agent",
            created_at=now,
            last_regeneration=now,
            skill_level=skill_level,
            is_active=True,
        )

        logger.info(
            f"[EntityLifecycle] Agent {agent_id} created with "
            f"{allocation:.2f} credits (skill: {skill_level})"
        )

        return entry.balance_after

    async def create_mission(
        self,
        mission_id: str,
        complexity: float = 1.0,
        estimated_duration_hours: float = 1.0,
    ) -> float:
        """Create new mission with credit allocation.

        Args:
            mission_id: Mission identifier
            complexity: Mission complexity
            estimated_duration_hours: Estimated duration

        Returns:
            Mission credit allocation
        """
        if mission_id in self.entities:
            raise ValueError(f"Mission {mission_id} already exists")

        # Calculate mission allocation
        allocation = self.calculator.calculate_mission_allocation(
            mission_id=mission_id,
            complexity=complexity,
            estimated_duration_hours=estimated_duration_hours,
        )

        # Record in ledger
        entry = self.ledger.append(
            transaction_type=TransactionType.ALLOCATION,
            entity_id=mission_id,
            entity_type="mission",
            amount=allocation,
            reason="Mission credit allocation",
            metadata={
                "complexity": complexity,
                "estimated_duration_hours": estimated_duration_hours,
            },
        )

        # Track entity state
        now = datetime.now(timezone.utc)
        self.entities[mission_id] = EntityState(
            entity_id=mission_id,
            entity_type="mission",
            created_at=now,
            last_regeneration=now,
            is_active=True,
        )

        logger.info(
            f"[EntityLifecycle] Mission {mission_id} created with "
            f"{allocation:.2f} credits (complexity: {complexity}, "
            f"duration: {estimated_duration_hours}h)"
        )

        return entry.balance_after

    async def consume_credits(
        self,
        entity_id: str,
        amount: float,
        reason: str,
        metadata: Optional[dict] = None,
    ) -> float:
        """Consume credits from entity.

        Args:
            entity_id: Entity identifier
            amount: Credit amount to consume (positive)
            reason: Consumption reason
            metadata: Additional context

        Returns:
            New balance after consumption

        Raises:
            ValueError: If insufficient credits
        """
        if entity_id not in self.entities:
            raise ValueError(f"Entity {entity_id} not found")

        state = self.entities[entity_id]

        # Record consumption (negative amount)
        entry = self.ledger.append(
            transaction_type=TransactionType.CONSUMPTION,
            entity_id=entity_id,
            entity_type=state.entity_type,
            amount=-amount,
            reason=reason,
            metadata=metadata or {},
        )

        logger.info(
            f"[EntityLifecycle] {state.entity_type} {entity_id} consumed "
            f"{amount:.2f} credits: {reason}"
        )

        return entry.balance_after

    async def regenerate_credits(
        self,
        entity_id: str,
        edge_of_chaos_score: Optional[float] = None,
    ) -> float:
        """Regenerate credits for entity.

        Args:
            entity_id: Entity identifier
            edge_of_chaos_score: Current Edge-of-Chaos score

        Returns:
            Regeneration amount
        """
        if entity_id not in self.entities:
            raise ValueError(f"Entity {entity_id} not found")

        state = self.entities[entity_id]
        now = datetime.now(timezone.utc)

        # Calculate hours elapsed since last regeneration
        hours_elapsed = (now - state.last_regeneration).total_seconds() / 3600.0

        if hours_elapsed < 0.01:  # Minimum 0.6 minutes
            return 0.0

        # Get current balance
        current_balance = self.ledger.get_balance(entity_id)

        # Calculate regeneration
        regeneration = self.calculator.calculate_regeneration(
            entity_id=entity_id,
            current_balance=current_balance,
            hours_elapsed=hours_elapsed,
            edge_of_chaos_score=edge_of_chaos_score,
        )

        if regeneration <= 0:
            return 0.0

        # Record regeneration
        entry = self.ledger.append(
            transaction_type=TransactionType.REGENERATION,
            entity_id=entity_id,
            entity_type=state.entity_type,
            amount=regeneration,
            reason="Periodic credit regeneration",
            metadata={
                "hours_elapsed": hours_elapsed,
                "edge_of_chaos_score": edge_of_chaos_score,
            },
        )

        # Update last regeneration time
        state.last_regeneration = now

        logger.debug(
            f"[EntityLifecycle] {state.entity_type} {entity_id} regenerated "
            f"{regeneration:.2f} credits ({hours_elapsed:.2f}h elapsed)"
        )

        return regeneration

    async def withdraw_credits(
        self,
        entity_id: str,
        severity: str,
        reason: str,
        metadata: Optional[dict] = None,
    ) -> float:
        """Withdraw credits (ImmuneService Entzug).

        Args:
            entity_id: Entity identifier
            severity: Severity level ("low", "medium", "high", "critical")
            reason: Withdrawal reason
            metadata: Additional context

        Returns:
            Withdrawal amount (positive)
        """
        if entity_id not in self.entities:
            raise ValueError(f"Entity {entity_id} not found")

        state = self.entities[entity_id]

        # Get current balance
        current_balance = self.ledger.get_balance(entity_id)

        # Calculate withdrawal
        withdrawal = self.calculator.calculate_withdrawal_amount(
            entity_id=entity_id,
            current_balance=current_balance,
            severity=severity,
        )

        # Record withdrawal (negative amount, allows negative balance)
        entry = self.ledger.append(
            transaction_type=TransactionType.WITHDRAWAL,
            entity_id=entity_id,
            entity_type=state.entity_type,
            amount=-withdrawal,
            reason=reason,
            metadata={
                "severity": severity,
                **(metadata or {}),
            },
        )

        logger.warning(
            f"[EntityLifecycle] {state.entity_type} {entity_id} credits withdrawn: "
            f"{withdrawal:.2f} ({severity} severity) - {reason}"
        )

        return withdrawal

    async def refund_credits(
        self,
        entity_id: str,
        original_allocation: float,
        work_completed_percentage: float,
        reason: str,
    ) -> float:
        """Refund credits (Synergie-Mechanik).

        Args:
            entity_id: Entity identifier
            original_allocation: Original allocation amount
            work_completed_percentage: Work completion (0.0-1.0)
            reason: Refund reason

        Returns:
            Refund amount
        """
        if entity_id not in self.entities:
            raise ValueError(f"Entity {entity_id} not found")

        state = self.entities[entity_id]

        # Calculate refund
        refund = self.calculator.calculate_refund(
            original_allocation=original_allocation,
            work_completed_percentage=work_completed_percentage,
        )

        if refund <= 0:
            return 0.0

        # Record refund
        entry = self.ledger.append(
            transaction_type=TransactionType.REFUND,
            entity_id=entity_id,
            entity_type=state.entity_type,
            amount=refund,
            reason=reason,
            metadata={
                "original_allocation": original_allocation,
                "work_completed_percentage": work_completed_percentage,
            },
        )

        logger.info(
            f"[EntityLifecycle] {state.entity_type} {entity_id} refunded "
            f"{refund:.2f} credits: {reason}"
        )

        return refund

    async def deactivate_entity(self, entity_id: str, reason: str):
        """Deactivate entity (stop regeneration).

        Args:
            entity_id: Entity identifier
            reason: Deactivation reason
        """
        if entity_id not in self.entities:
            raise ValueError(f"Entity {entity_id} not found")

        state = self.entities[entity_id]
        state.is_active = False

        logger.info(
            f"[EntityLifecycle] {state.entity_type} {entity_id} deactivated: {reason}"
        )

    async def start_regeneration_loop(self):
        """Start background regeneration task."""
        if self.regeneration_task is not None:
            logger.warning("[EntityLifecycle] Regeneration loop already running")
            return

        logger.info(
            f"[EntityLifecycle] Starting regeneration loop "
            f"(interval: {self.regeneration_interval_seconds}s)"
        )

        self.regeneration_task = asyncio.create_task(self._regeneration_loop())

    async def stop_regeneration_loop(self):
        """Stop background regeneration task."""
        if self.regeneration_task is None:
            return

        logger.info("[EntityLifecycle] Stopping regeneration loop")
        self.regeneration_task.cancel()

        try:
            await self.regeneration_task
        except asyncio.CancelledError:
            pass

        self.regeneration_task = None

    async def _regeneration_loop(self):
        """Background task for periodic credit regeneration."""
        while True:
            try:
                await asyncio.sleep(self.regeneration_interval_seconds)

                # Get Edge-of-Chaos score (if RuntimeAuditor available)
                eoc_score = await self._get_edge_of_chaos_score()

                # Regenerate for all active entities
                regenerated_count = 0
                for entity_id, state in self.entities.items():
                    if not state.is_active:
                        continue

                    try:
                        regen = await self.regenerate_credits(
                            entity_id=entity_id,
                            edge_of_chaos_score=eoc_score,
                        )
                        if regen > 0:
                            regenerated_count += 1
                    except Exception as e:
                        logger.error(
                            f"[EntityLifecycle] Regeneration failed for {entity_id}: {e}"
                        )

                if regenerated_count > 0:
                    logger.info(
                        f"[EntityLifecycle] Regeneration cycle: "
                        f"{regenerated_count} entities regenerated "
                        f"(EoC: {eoc_score:.3f if eoc_score else 'N/A'})"
                    )

            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"[EntityLifecycle] Regeneration loop error: {e}")

    async def _get_edge_of_chaos_score(self) -> Optional[float]:
        """Get current Edge-of-Chaos score from RuntimeAuditor.

        Returns:
            Edge-of-Chaos score (0.0-1.0) or None if unavailable
        """
        try:
            from backend.app.modules.runtime_auditor.service import get_auditor

            auditor = get_auditor()
            metrics = await auditor.get_current_metrics()

            if metrics.edge_of_chaos and metrics.edge_of_chaos.score is not None:
                return metrics.edge_of_chaos.score

        except Exception as e:
            logger.debug(f"[EntityLifecycle] Failed to get EoC score: {e}")

        return None

    def get_entity_state(self, entity_id: str) -> Optional[EntityState]:
        """Get entity state.

        Args:
            entity_id: Entity identifier

        Returns:
            EntityState or None if not found
        """
        return self.entities.get(entity_id)

    def get_all_entities(self) -> Dict[str, EntityState]:
        """Get all entity states.

        Returns:
            Dictionary of entity_id -> EntityState
        """
        return self.entities.copy()


# Global lifecycle manager instance
_lifecycle_manager: Optional[EntityLifecycleManager] = None


def get_lifecycle_manager() -> EntityLifecycleManager:
    """Get global entity lifecycle manager instance.

    Returns:
        EntityLifecycleManager instance
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = EntityLifecycleManager()
    return _lifecycle_manager
