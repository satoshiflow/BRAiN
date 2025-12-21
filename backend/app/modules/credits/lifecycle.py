"""
Entity Lifecycle Management

Manages the complete lifecycle of entities (agents, missions) with
integrated credit accounting and existence tax.

Lifecycle States:
- CREATED: Entity exists but not yet active
- ACTIVE: Entity operational and consuming resources (existence tax applies)
- SUSPENDED: Temporarily inactive (low credits or admin action)
- TERMINATED: Permanently shut down

Philosophy:
- Existence tax prevents resource hoarding
- Automatic suspension prevents negative balances
- Complete audit trail for all state transitions
- Fail-closed: ambiguous states result in suspension
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .calculator import CalculationContext, CalculationRule, CreditCalculator
from .ledger import CreditLedgerService, NegativeBalanceError
from .models import (
    AgentRegistry,
    AgentStatus,
    AuditEvent,
    AuditResult,
    AuditTrail,
    CreditType,
    EntityType,
)


class LifecycleError(Exception):
    """Base exception for lifecycle operations."""

    pass


class InvalidStateTransitionError(LifecycleError):
    """Raised when attempting an invalid state transition."""

    pass


class EntityLifecycleManager:
    """
    Manages entity lifecycle with credit integration.

    Responsibilities:
    - Create and initialize entities
    - Manage state transitions
    - Collect existence tax
    - Auto-suspend on low credits
    - Auto-terminate after prolonged suspension
    """

    # State transition rules
    VALID_TRANSITIONS = {
        AgentStatus.ACTIVE: {AgentStatus.SUSPENDED, AgentStatus.TERMINATED},
        AgentStatus.SUSPENDED: {AgentStatus.ACTIVE, AgentStatus.TERMINATED},
        AgentStatus.TERMINATED: set(),  # Terminal state
    }

    # Existence tax configuration
    EXISTENCE_TAX_INTERVAL = timedelta(hours=1)
    AGENT_TAX_RATE_CC = Decimal("5.0")  # 5 CC per hour
    AGENT_TAX_RATE_SC = Decimal("0.1")  # 0.1 SC per hour

    # Auto-suspension configuration
    MIN_BALANCE_CC = Decimal("10.0")
    GRACE_PERIOD = timedelta(hours=1)

    # Auto-termination configuration
    AUTO_TERMINATE_ENABLED = True
    SUSPENSION_THRESHOLD = timedelta(days=7)

    def __init__(
        self,
        session: AsyncSession,
        ledger: CreditLedgerService,
        calculator: CreditCalculator,
    ):
        """
        Initialize lifecycle manager.

        Args:
            session: Database session
            ledger: Credit ledger service
            calculator: Credit calculator
        """
        self.session = session
        self.ledger = ledger
        self.calculator = calculator

    async def create_agent(
        self,
        agent_name: str,
        agent_type: str,
        metadata: Optional[dict] = None,
    ) -> AgentRegistry:
        """
        Create a new agent with initial credit allocation.

        Args:
            agent_name: Unique agent name
            agent_type: Agent type (CODER, OPS, SUPERVISOR, etc.)
            metadata: Additional metadata

        Returns:
            Created agent registry entry

        Raises:
            ValueError: If agent_name already exists
        """
        # Check if agent name exists
        stmt = select(AgentRegistry).where(AgentRegistry.agent_name == agent_name)
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            raise ValueError(f"Agent with name '{agent_name}' already exists")

        now = datetime.now(timezone.utc)

        # Create agent registry entry
        agent = AgentRegistry(
            agent_name=agent_name,
            agent_type=agent_type,
            status=AgentStatus.ACTIVE.value,
            created_at=now,
            activated_at=now,
            last_activity_at=now,
            metadata=metadata or {},
        )

        self.session.add(agent)
        await self.session.flush()
        await self.session.refresh(agent)

        logger.info(f"Created agent: {agent_name} (ID: {agent.agent_id})")

        # Calculate and mint initial credits
        context = CalculationContext(
            entity_id=str(agent.agent_id),
            entity_type=EntityType.AGENT,
            timestamp=now,
        )

        creation_result = self.calculator.calculate_agent_creation(context)

        # Mint initial credits
        await self.ledger.mint_credits(
            entity_id=str(agent.agent_id),
            entity_type=EntityType.AGENT,
            credit_type=creation_result.credit_type,
            amount=creation_result.amount,
            reason=creation_result.reason,
            metadata=creation_result.metadata,
        )

        # Update cached balance
        agent.credit_balance_cc = creation_result.amount
        agent.total_credits_earned = creation_result.amount

        await self.session.commit()

        # Create audit trail
        await self._audit_event(
            event_type="AGENT_CREATE",
            entity_id=str(agent.agent_id),
            entity_type=EntityType.AGENT,
            actor_id="SYSTEM",
            action=f"Created agent {agent_name} with {creation_result.amount} CC",
            result=AuditResult.SUCCESS,
            metadata={
                "agent_name": agent_name,
                "agent_type": agent_type,
                "initial_credits": str(creation_result.amount),
            },
        )

        logger.info(
            f"Agent {agent_name} initialized with {creation_result.amount} CC"
        )

        return agent

    async def transition_state(
        self,
        agent_id: UUID,
        new_status: AgentStatus,
        reason: str,
        actor_id: str = "SYSTEM",
    ) -> AgentRegistry:
        """
        Transition agent to a new status.

        Args:
            agent_id: Agent ID
            new_status: New status
            reason: Reason for transition
            actor_id: Who/what initiated the transition

        Returns:
            Updated agent

        Raises:
            InvalidStateTransitionError: If transition is invalid
            ValueError: If agent not found
        """
        # Fetch agent
        stmt = select(AgentRegistry).where(AgentRegistry.agent_id == agent_id)
        result = await self.session.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        current_status = AgentStatus(agent.status)

        # Check if transition is valid
        if new_status not in self.VALID_TRANSITIONS.get(current_status, set()):
            raise InvalidStateTransitionError(
                f"Invalid transition from {current_status.value} to {new_status.value}"
            )

        now = datetime.now(timezone.utc)

        # Update status and timestamp
        old_status = agent.status
        agent.status = new_status.value

        if new_status == AgentStatus.ACTIVE:
            agent.activated_at = now
        elif new_status == AgentStatus.SUSPENDED:
            agent.suspended_at = now
        elif new_status == AgentStatus.TERMINATED:
            agent.terminated_at = now

        agent.last_activity_at = now

        await self.session.commit()

        # Audit trail
        await self._audit_event(
            event_type="AGENT_STATUS_CHANGE",
            entity_id=str(agent_id),
            entity_type=EntityType.AGENT,
            actor_id=actor_id,
            action=f"Status changed from {old_status} to {new_status.value}: {reason}",
            result=AuditResult.SUCCESS,
            metadata={
                "old_status": old_status,
                "new_status": new_status.value,
                "reason": reason,
            },
        )

        logger.info(
            f"Agent {agent.agent_name} transitioned: {old_status} → {new_status.value}"
        )

        return agent

    async def collect_existence_tax_for_agent(
        self, agent_id: UUID
    ) -> Optional[tuple[Decimal, Decimal]]:
        """
        Collect existence tax for a single agent.

        Args:
            agent_id: Agent ID

        Returns:
            Tuple of (CC_tax, SC_tax) if successful, None if suspended

        Raises:
            ValueError: If agent not found
        """
        # Fetch agent
        stmt = select(AgentRegistry).where(AgentRegistry.agent_id == agent_id)
        result = await self.session.execute(stmt)
        agent = result.scalar_one_or_none()

        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # Only collect tax for ACTIVE agents
        if agent.status != AgentStatus.ACTIVE.value:
            logger.debug(f"Skipping tax for non-active agent: {agent.agent_name}")
            return None

        now = datetime.now(timezone.utc)

        # Calculate hours active since last activity
        hours_active = Decimal("1.0")  # Default to 1 hour
        if agent.last_activity_at:
            delta = now - agent.last_activity_at
            hours_active = Decimal(str(delta.total_seconds() / 3600))

        # Calculate tax
        context = CalculationContext(
            entity_id=str(agent_id),
            entity_type=EntityType.AGENT,
            timestamp=now,
            agent_status=AgentStatus.ACTIVE,
            hours_active=hours_active,
        )

        tax_result = self.calculator.calculate_existence_tax(context)

        # Attempt to collect CC tax
        try:
            cc_tx = await self.ledger.collect_existence_tax(
                entity_id=str(agent_id),
                entity_type=EntityType.AGENT,
                credit_type=CreditType.COMPUTE_CREDITS,
                tax_amount=tax_result.amount,
                metadata=tax_result.metadata,
            )

            if cc_tx is None:
                # Insufficient credits - suspend agent
                await self.transition_state(
                    agent_id=agent_id,
                    new_status=AgentStatus.SUSPENDED,
                    reason="Insufficient credits for existence tax",
                )
                logger.warning(
                    f"Agent {agent.agent_name} suspended due to insufficient credits"
                )
                return None

            # Update cached balance
            agent.credit_balance_cc = cc_tx.balance_after
            agent.total_credits_spent += tax_result.amount

        except NegativeBalanceError:
            # Suspend agent
            await self.transition_state(
                agent_id=agent_id,
                new_status=AgentStatus.SUSPENDED,
                reason="Insufficient credits for existence tax",
            )
            logger.warning(
                f"Agent {agent.agent_name} suspended due to insufficient credits"
            )
            return None

        # Collect SC tax (storage)
        sc_tax = self.AGENT_TAX_RATE_SC * hours_active

        try:
            sc_tx = await self.ledger.collect_existence_tax(
                entity_id=str(agent_id),
                entity_type=EntityType.AGENT,
                credit_type=CreditType.STORAGE_CREDITS,
                tax_amount=sc_tax,
                metadata={"hours_active": str(hours_active)},
            )

            if sc_tx:
                agent.credit_balance_sc = sc_tx.balance_after
                agent.total_credits_spent += sc_tax
        except NegativeBalanceError:
            # SC deficit is not critical, just log
            logger.warning(f"Agent {agent.agent_name} has negative SC balance")

        agent.last_activity_at = now
        await self.session.commit()

        logger.info(
            f"Collected existence tax from {agent.agent_name}: "
            f"{tax_result.amount} CC + {sc_tax} SC"
        )

        return (tax_result.amount, sc_tax)

    async def collect_existence_tax_batch(self) -> dict:
        """
        Collect existence tax from all ACTIVE agents.

        Returns:
            Statistics about tax collection
        """
        # Fetch all ACTIVE agents
        stmt = select(AgentRegistry).where(AgentRegistry.status == AgentStatus.ACTIVE.value)
        result = await self.session.execute(stmt)
        active_agents = result.scalars().all()

        stats = {
            "total_agents": len(active_agents),
            "collected": 0,
            "suspended": 0,
            "errors": 0,
            "total_cc": Decimal("0.0"),
            "total_sc": Decimal("0.0"),
        }

        for agent in active_agents:
            try:
                tax_result = await self.collect_existence_tax_for_agent(agent.agent_id)

                if tax_result:
                    cc_tax, sc_tax = tax_result
                    stats["collected"] += 1
                    stats["total_cc"] += cc_tax
                    stats["total_sc"] += sc_tax
                else:
                    stats["suspended"] += 1

            except Exception as e:
                logger.error(
                    f"Error collecting tax from agent {agent.agent_name}: {e}"
                )
                stats["errors"] += 1

        logger.info(
            f"Existence tax collection complete: "
            f"{stats['collected']} collected, "
            f"{stats['suspended']} suspended, "
            f"{stats['errors']} errors"
        )

        return stats

    async def check_auto_terminate(self) -> dict:
        """
        Check for agents that should be auto-terminated.

        Terminates agents suspended for longer than SUSPENSION_THRESHOLD.

        Returns:
            Statistics about terminations
        """
        if not self.AUTO_TERMINATE_ENABLED:
            return {"enabled": False}

        now = datetime.now(timezone.utc)
        threshold_time = now - self.SUSPENSION_THRESHOLD

        # Find agents suspended for too long
        stmt = select(AgentRegistry).where(
            and_(
                AgentRegistry.status == AgentStatus.SUSPENDED.value,
                AgentRegistry.suspended_at <= threshold_time,
            )
        )

        result = await self.session.execute(stmt)
        suspended_agents = result.scalars().all()

        stats = {
            "enabled": True,
            "candidates": len(suspended_agents),
            "terminated": 0,
            "errors": 0,
        }

        for agent in suspended_agents:
            try:
                await self.transition_state(
                    agent_id=agent.agent_id,
                    new_status=AgentStatus.TERMINATED,
                    reason=f"Auto-terminated after {self.SUSPENSION_THRESHOLD.days} days of suspension",
                )
                stats["terminated"] += 1

            except Exception as e:
                logger.error(f"Error terminating agent {agent.agent_name}: {e}")
                stats["errors"] += 1

        logger.info(
            f"Auto-termination complete: {stats['terminated']} agents terminated"
        )

        return stats

    async def _audit_event(
        self,
        event_type: str,
        entity_id: str,
        entity_type: EntityType,
        actor_id: str,
        action: str,
        result: AuditResult,
        metadata: Optional[dict] = None,
    ) -> None:
        """
        Create audit trail entry.

        Args:
            event_type: Type of event
            entity_id: Entity ID
            entity_type: Type of entity
            actor_id: Who/what triggered the event
            action: Human-readable description
            result: Event result
            metadata: Additional context
        """
        # Compute signature
        timestamp = datetime.now(timezone.utc)
        message = f"{event_type}:{entity_id}:{action}:{timestamp.isoformat()}"
        signature = f"sha256:{hashlib.sha256(message.encode()).hexdigest()}"

        audit = AuditTrail(
            timestamp=timestamp,
            event_type=event_type,
            entity_id=entity_id,
            entity_type=entity_type.value,
            actor_id=actor_id,
            action=action,
            result=result.value,
            metadata=metadata or {},
            signature=signature,
        )

        self.session.add(audit)
        await self.session.flush()


import hashlib  # Needed for audit signature
