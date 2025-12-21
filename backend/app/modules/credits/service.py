"""
Credits Service

High-level service orchestrating credit system components.

Integrates:
- Credit Ledger (append-only transactions)
- Credit Calculator (deterministic calculations)
- Entity Lifecycle Manager (lifecycle + existence tax)
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .calculator import CreditCalculator
from .ledger import CreditLedgerService
from .lifecycle import EntityLifecycleManager
from .models import (
    AgentRegistry,
    AgentRegistryEntry,
    CreditBalance,
    CreditLedger,
    CreditTransaction,
    CreditType,
    EntityType,
)
from .schemas import CreditsHealth, CreditsInfo

MODULE_NAME = "brain.credits.v2"
MODULE_VERSION = "2.0.0"


async def get_health() -> CreditsHealth:
    """Get module health status."""
    return CreditsHealth(status="ok", timestamp=datetime.now(timezone.utc))


async def get_info() -> CreditsInfo:
    """Get module information."""
    return CreditsInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config={
            "features": [
                "append_only_ledger",
                "deterministic_calculator",
                "existence_tax",
                "auto_suspension",
                "audit_trail",
            ],
            "spec_version": "1.0.0",
        },
    )


class CreditsService:
    """
    High-level credits service.

    Orchestrates credit system components and provides
    business logic layer for API endpoints.
    """

    def __init__(self, session: AsyncSession, signing_key: str = "CHANGE_ME_IN_PRODUCTION"):
        """
        Initialize credits service.

        Args:
            session: Database session
            signing_key: Secret key for transaction signatures
        """
        self.session = session
        self.ledger = CreditLedgerService(session, signing_key)
        self.calculator = CreditCalculator()
        self.lifecycle = EntityLifecycleManager(session, self.ledger, self.calculator)

    async def get_balance(
        self, entity_id: str, entity_type: Optional[EntityType] = None
    ) -> CreditBalance:
        """
        Get complete credit balance for an entity.

        Args:
            entity_id: Entity ID
            entity_type: Optional entity type (auto-detected if not provided)

        Returns:
            Credit balance with all credit types
        """
        # Get balances for all credit types
        cc_balance = await self.ledger.get_balance(entity_id, CreditType.COMPUTE_CREDITS)
        lc_balance = await self.ledger.get_balance(entity_id, CreditType.LLM_CREDITS)
        sc_balance = await self.ledger.get_balance(entity_id, CreditType.STORAGE_CREDITS)
        nc_balance = await self.ledger.get_balance(entity_id, CreditType.NETWORK_CREDITS)

        # Get lifetime stats from agent registry if available
        total_earned = Decimal("0.0")
        total_spent = Decimal("0.0")

        try:
            entity_uuid = UUID(entity_id)
            stmt = select(AgentRegistry).where(AgentRegistry.agent_id == entity_uuid)
            result = await self.session.execute(stmt)
            agent = result.scalar_one_or_none()

            if agent:
                total_earned = agent.total_credits_earned
                total_spent = agent.total_credits_spent
                if entity_type is None:
                    entity_type = EntityType.AGENT
        except (ValueError, AttributeError):
            # Not a valid UUID or not an agent
            if entity_type is None:
                entity_type = EntityType.SYSTEM

        return CreditBalance(
            entity_id=entity_id,
            entity_type=entity_type,
            compute_credits=cc_balance,
            llm_credits=lc_balance,
            storage_credits=sc_balance,
            network_credits=nc_balance,
            total_earned=total_earned,
            total_spent=total_spent,
            last_updated=datetime.now(timezone.utc),
        )

    async def get_transaction_history(
        self,
        entity_id: str,
        credit_type: Optional[CreditType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CreditTransaction]:
        """
        Get transaction history for an entity.

        Args:
            entity_id: Entity ID
            credit_type: Optional filter by credit type
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of transactions
        """
        from sqlalchemy import desc

        stmt = (
            select(CreditLedger)
            .where(CreditLedger.entity_id == entity_id)
            .order_by(desc(CreditLedger.sequence_number))
            .limit(limit)
            .offset(offset)
        )

        if credit_type:
            stmt = stmt.where(CreditLedger.credit_type == credit_type.value)

        result = await self.session.execute(stmt)
        entries = result.scalars().all()

        return [
            CreditTransaction(
                id=entry.id,
                sequence_number=entry.sequence_number,
                timestamp=entry.timestamp,
                entity_id=entry.entity_id,
                entity_type=EntityType(entry.entity_type),
                credit_type=CreditType(entry.credit_type),
                amount=entry.amount,
                balance_after=entry.balance_after,
                transaction_type=entry.transaction_type,
                reason=entry.reason,
                metadata=entry.metadata,
                signature=entry.signature,
            )
            for entry in entries
        ]

    async def create_agent(
        self, agent_name: str, agent_type: str, metadata: Optional[dict] = None
    ) -> AgentRegistryEntry:
        """
        Create a new agent with initial credit allocation.

        Args:
            agent_name: Unique agent name
            agent_type: Agent type
            metadata: Additional metadata

        Returns:
            Agent registry entry

        Raises:
            ValueError: If agent name exists
        """
        agent = await self.lifecycle.create_agent(agent_name, agent_type, metadata)
        return AgentRegistryEntry.model_validate(agent)

    async def spend_credits(
        self,
        entity_id: str,
        entity_type: EntityType,
        credit_type: CreditType,
        amount: Decimal,
        reason: str,
        metadata: Optional[dict] = None,
    ) -> CreditTransaction:
        """
        Spend credits from an entity.

        Args:
            entity_id: Entity ID
            entity_type: Entity type
            credit_type: Credit type
            amount: Amount to spend
            reason: Reason
            metadata: Additional context

        Returns:
            Transaction record
        """
        return await self.ledger.burn_credits(
            entity_id=entity_id,
            entity_type=entity_type,
            credit_type=credit_type,
            amount=amount,
            reason=reason,
            metadata=metadata,
        )

    async def transfer_credits(
        self,
        from_entity_id: str,
        from_entity_type: EntityType,
        to_entity_id: str,
        to_entity_type: EntityType,
        credit_type: CreditType,
        amount: Decimal,
        reason: str,
        metadata: Optional[dict] = None,
    ) -> tuple[CreditTransaction, CreditTransaction]:
        """
        Transfer credits between entities.

        Args:
            from_entity_id: Source entity ID
            from_entity_type: Source entity type
            to_entity_id: Destination entity ID
            to_entity_type: Destination entity type
            credit_type: Credit type
            amount: Amount
            reason: Reason
            metadata: Additional context

        Returns:
            Tuple of (burn_tx, mint_tx)
        """
        return await self.ledger.transfer_credits(
            from_entity_id=from_entity_id,
            from_entity_type=from_entity_type,
            to_entity_id=to_entity_id,
            to_entity_type=to_entity_type,
            credit_type=credit_type,
            amount=amount,
            reason=reason,
            metadata=metadata,
        )

    async def collect_existence_tax(self) -> dict:
        """
        Collect existence tax from all active agents.

        Returns:
            Statistics
        """
        return await self.lifecycle.collect_existence_tax_batch()

    async def check_auto_terminate(self) -> dict:
        """
        Check and terminate suspended agents.

        Returns:
            Statistics
        """
        return await self.lifecycle.check_auto_terminate()
