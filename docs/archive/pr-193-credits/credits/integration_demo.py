"""
Event Sourcing Integration Demo.

This module demonstrates how to use the Event Sourcing infrastructure
for credit operations in the BRAiN system.

Usage Example:
    >>> from app.modules.credits.integration_demo import CreditSystemDemo
    >>>
    >>> # Initialize system
    >>> demo = CreditSystemDemo()
    >>> await demo.initialize()
    >>>
    >>> # Create agent with credits
    >>> await demo.create_agent("agent_123", skill_level=0.8)
    >>>
    >>> # Consume credits for mission
    >>> await demo.consume_credits("agent_123", 30.0, "Mission execution")
    >>>
    >>> # Get current balance
    >>> balance = await demo.get_balance("agent_123")
    >>> print(f"Balance: {balance}")
    >>>
    >>> # Get transaction history
    >>> history = await demo.get_history("agent_123", limit=10)
"""

from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger

from app.modules.credits.event_sourcing import (
    # Core components
    EventBus,
    ProjectionManager,
    ReplayEngine,
    get_event_bus,
    get_projection_manager,
    get_replay_engine,
    # Event creators
    create_credit_allocated_event,
    create_credit_consumed_event,
    create_credit_refunded_event,
    # Data models
    LedgerEntry,
)


class CreditSystemDemo:
    """
    Demonstration of Event Sourcing for Credit System.

    Features:
    - Agent credit allocation based on skill level
    - Credit consumption for missions
    - Credit refunds for failed missions
    - Balance queries
    - Transaction history

    Example:
        >>> demo = CreditSystemDemo()
        >>> await demo.initialize()
        >>>
        >>> # Allocate credits to agent
        >>> await demo.create_agent("agent_A", skill_level=0.8)
        >>> # Balance: 80.0 (skill_level * 100)
        >>>
        >>> # Consume credits
        >>> await demo.consume_credits("agent_A", 30.0, "Mission 1")
        >>> # Balance: 50.0
        >>>
        >>> # Refund credits
        >>> await demo.refund_credits("agent_A", 10.0, "Mission 1 failed")
        >>> # Balance: 60.0
    """

    def __init__(self):
        self.event_bus: Optional[EventBus] = None
        self.projections: Optional[ProjectionManager] = None
        self.replay_engine: Optional[ReplayEngine] = None
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize the credit system.

        Steps:
        1. Get EventBus, ProjectionManager, ReplayEngine singletons
        2. Subscribe projections to EventBus
        3. Replay existing events (crash recovery)
        """
        if self._initialized:
            logger.warning("CreditSystemDemo already initialized")
            return

        logger.info("Initializing CreditSystemDemo...")

        # Get singleton instances
        self.event_bus = await get_event_bus()
        self.projections = get_projection_manager()
        self.replay_engine = await get_replay_engine()

        # Subscribe projections to EventBus
        await self.projections.subscribe_all(self.event_bus)

        # Replay existing events (crash recovery)
        metrics = await self.replay_engine.replay_all()
        logger.info(
            f"Replayed {metrics['total_events']} events in {metrics['replay_duration_seconds']}s"
        )

        self._initialized = True
        logger.info("CreditSystemDemo initialized successfully")

    async def create_agent(
        self,
        agent_id: str,
        skill_level: float,
        actor_id: str = "system",
    ) -> float:
        """
        Create agent and allocate initial credits.

        Args:
            agent_id: Unique agent identifier
            skill_level: Skill level (0.0 - 1.0)
            actor_id: Who created the agent

        Returns:
            Initial balance allocated

        Formula:
            initial_credits = skill_level * 100.0
        """
        self._check_initialized()

        # Calculate initial credits based on skill level
        initial_credits = skill_level * 100.0

        # Create and publish CREDIT_ALLOCATED event
        event = create_credit_allocated_event(
            entity_id=agent_id,
            entity_type="agent",
            amount=initial_credits,
            reason=f"Agent creation (skill_level={skill_level})",
            balance_after=initial_credits,
            actor_id=actor_id,
        )

        published = await self.event_bus.publish(event)

        if published:
            logger.info(
                f"Agent created: {agent_id}, credits: {initial_credits}",
                agent_id=agent_id,
                initial_credits=initial_credits,
            )
        else:
            logger.warning(
                f"Agent creation skipped (duplicate): {agent_id}",
                agent_id=agent_id,
            )

        return initial_credits

    async def consume_credits(
        self,
        agent_id: str,
        amount: float,
        reason: str,
        mission_id: Optional[str] = None,
        actor_id: str = "system",
        idempotency_key: Optional[str] = None,
    ) -> float:
        """
        Consume credits for agent.

        Args:
            agent_id: Agent consuming credits
            amount: Credits to consume (must be > 0)
            reason: Why credits are consumed
            mission_id: Related mission (optional)
            actor_id: Who initiated consumption
            idempotency_key: Optional idempotency key for deduplication (for testing)

        Returns:
            Balance after consumption

        Raises:
            ValueError: If insufficient credits
        """
        self._check_initialized()

        # Get current balance
        current_balance = self.projections.balance.get_balance(agent_id)

        # Check sufficient credits
        if current_balance < amount:
            raise ValueError(
                f"Insufficient credits: {agent_id} has {current_balance}, needs {amount}"
            )

        # Calculate new balance
        new_balance = current_balance - amount

        # Create and publish CREDIT_CONSUMED event
        event = create_credit_consumed_event(
            entity_id=agent_id,
            entity_type="agent",
            amount=amount,
            reason=reason,
            balance_after=new_balance,
            mission_id=mission_id,
            actor_id=actor_id,
        )

        await self.event_bus.publish(event)

        logger.info(
            f"Credits consumed: {agent_id}, amount: {amount}, balance: {new_balance}",
            agent_id=agent_id,
            amount=amount,
            balance=new_balance,
        )

        return new_balance

    async def refund_credits(
        self,
        agent_id: str,
        amount: float,
        reason: str,
        mission_id: Optional[str] = None,
        actor_id: str = "system",
    ) -> float:
        """
        Refund credits to agent.

        Args:
            agent_id: Agent receiving refund
            amount: Credits to refund (must be > 0)
            reason: Why credits are refunded
            mission_id: Related mission (optional)
            actor_id: Who initiated refund

        Returns:
            Balance after refund
        """
        self._check_initialized()

        # Get current balance
        current_balance = self.projections.balance.get_balance(agent_id)

        # Calculate new balance
        new_balance = current_balance + amount

        # Create and publish CREDIT_REFUNDED event
        event = create_credit_refunded_event(
            entity_id=agent_id,
            entity_type="agent",
            amount=amount,
            reason=reason,
            balance_after=new_balance,
            mission_id=mission_id,
            actor_id=actor_id,
        )

        await self.event_bus.publish(event)

        logger.info(
            f"Credits refunded: {agent_id}, amount: {amount}, balance: {new_balance}",
            agent_id=agent_id,
            amount=amount,
            balance=new_balance,
        )

        return new_balance

    async def add_credits(
        self,
        agent_id: str,
        amount: float,
        reason: str,
        actor_id: str = "system",
    ) -> float:
        """
        Add credits to existing agent.

        This method is semantically clearer than using refund for budget top-ups.
        Uses CREDIT_ALLOCATED event to represent credit addition.

        Args:
            agent_id: Agent receiving credits
            amount: Credits to add (must be > 0)
            reason: Why credits are added
            actor_id: Who initiated addition

        Returns:
            Balance after addition

        Example:
            >>> await demo.add_credits("agent_001", 100.0, "Monthly budget top-up")
            150.0
        """
        self._check_initialized()

        # Get current balance
        current_balance = self.projections.balance.get_balance(agent_id)

        # Calculate new balance
        new_balance = current_balance + amount

        # Create and publish CREDIT_ALLOCATED event
        # Using ALLOCATED (not REFUNDED) for semantic clarity
        event = create_credit_allocated_event(
            entity_id=agent_id,
            entity_type="agent",
            amount=amount,
            reason=reason,
            balance_after=new_balance,
            actor_id=actor_id,
        )

        await self.event_bus.publish(event)

        logger.info(
            f"Credits added: {agent_id}, amount: {amount}, balance: {new_balance}",
            agent_id=agent_id,
            amount=amount,
            balance=new_balance,
        )

        return new_balance

    async def get_balance(self, agent_id: str) -> float:
        """
        Get current balance for agent.

        Args:
            agent_id: Agent ID

        Returns:
            Current balance (0.0 if agent not found)
        """
        self._check_initialized()
        return self.projections.balance.get_balance(agent_id)

    async def get_all_balances(self) -> Dict[str, float]:
        """
        Get all agent balances.

        Returns:
            Dict of agent_id → balance
        """
        self._check_initialized()
        return self.projections.balance.get_all_balances()

    async def get_history(
        self,
        agent_id: str,
        limit: Optional[int] = None,
    ) -> List[LedgerEntry]:
        """
        Get transaction history for agent.

        Args:
            agent_id: Agent ID
            limit: Max number of entries (most recent first)

        Returns:
            List of LedgerEntry (ordered by timestamp, newest first)
        """
        self._check_initialized()
        return self.projections.ledger.get_history(agent_id, limit=limit)

    async def get_metrics(self) -> Dict:
        """
        Get system metrics.

        Returns:
            Dict with metrics:
            - journal: EventJournal metrics
            - event_bus: EventBus metrics
            - replay: ReplayEngine metrics
        """
        self._check_initialized()

        journal = self.event_bus.journal

        return {
            "journal": journal.get_metrics(),
            "event_bus": self.event_bus.get_metrics(),
            "replay": self.replay_engine.get_metrics(),
        }

    def _check_initialized(self) -> None:
        """Check if system is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "CreditSystemDemo not initialized. Call await demo.initialize() first."
            )


# === Singleton Pattern ===

_demo_instance: Optional[CreditSystemDemo] = None


async def get_credit_system_demo() -> CreditSystemDemo:
    """
    Get singleton CreditSystemDemo instance.

    Returns:
        CreditSystemDemo instance (initialized)
    """
    global _demo_instance

    if _demo_instance is None:
        _demo_instance = CreditSystemDemo()
        await _demo_instance.initialize()

    return _demo_instance
