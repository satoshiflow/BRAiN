"""
Integration tests for Credit System

Tests the complete credit system including:
- Credit Ledger (append-only)
- Credit Calculator (deterministic)
- Entity Lifecycle (existence tax)
- Agent Registry (lifecycle tracking)
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.modules.credits.calculator import CalculationContext, CreditCalculator
from backend.app.modules.credits.ledger import CreditLedgerService, NegativeBalanceError
from backend.app.modules.credits.lifecycle import EntityLifecycleManager
from backend.app.modules.credits.models import (
    AgentRegistry,
    AgentStatus,
    Base,
    CreditLedger,
    CreditType,
    EntityType,
    TransactionType,
)
from backend.app.modules.credits.service import CreditsService


@pytest.fixture
async def db_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=NullPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
def ledger_service(db_session):
    """Create credit ledger service."""
    return CreditLedgerService(db_session, signing_key="test_key")


@pytest.fixture
def calculator():
    """Create credit calculator."""
    return CreditCalculator()


@pytest.fixture
def lifecycle_manager(db_session, ledger_service, calculator):
    """Create entity lifecycle manager."""
    return EntityLifecycleManager(db_session, ledger_service, calculator)


@pytest.fixture
def credits_service(db_session):
    """Create credits service."""
    return CreditsService(db_session, signing_key="test_key")


class TestCreditLedgerIntegration:
    """Test credit ledger functionality."""

    @pytest.mark.asyncio
    async def test_mint_credits(self, ledger_service, db_session):
        """Test minting credits."""
        entity_id = str(uuid4())

        tx = await ledger_service.mint_credits(
            entity_id=entity_id,
            entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("1000.0"),
            reason="Test mint",
        )

        assert tx.amount == Decimal("1000.0")
        assert tx.balance_after == Decimal("1000.0")
        assert tx.transaction_type == TransactionType.MINT

        # Verify balance
        balance = await ledger_service.get_balance(entity_id, CreditType.COMPUTE_CREDITS)
        assert balance == Decimal("1000.0")

    @pytest.mark.asyncio
    async def test_burn_credits(self, ledger_service, db_session):
        """Test burning credits."""
        entity_id = str(uuid4())

        # Mint first
        await ledger_service.mint_credits(
            entity_id=entity_id,
            entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("1000.0"),
            reason="Initial mint",
        )

        # Burn
        tx = await ledger_service.burn_credits(
            entity_id=entity_id,
            entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("50.0"),
            reason="Test burn",
        )

        assert tx.amount == Decimal("-50.0")
        assert tx.balance_after == Decimal("950.0")

        # Verify balance
        balance = await ledger_service.get_balance(entity_id, CreditType.COMPUTE_CREDITS)
        assert balance == Decimal("950.0")

    @pytest.mark.asyncio
    async def test_insufficient_credits_prevented(self, ledger_service, db_session):
        """Test that negative balance is prevented."""
        entity_id = str(uuid4())

        # Mint 100
        await ledger_service.mint_credits(
            entity_id=entity_id,
            entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("100.0"),
            reason="Initial mint",
        )

        # Try to burn 200 (should fail)
        with pytest.raises(NegativeBalanceError):
            await ledger_service.burn_credits(
                entity_id=entity_id,
                entity_type=EntityType.AGENT,
                credit_type=CreditType.COMPUTE_CREDITS,
                amount=Decimal("200.0"),
                reason="Excessive burn",
            )

        # Balance should still be 100
        balance = await ledger_service.get_balance(entity_id, CreditType.COMPUTE_CREDITS)
        assert balance == Decimal("100.0")

    @pytest.mark.asyncio
    async def test_transfer_credits(self, ledger_service, db_session):
        """Test transferring credits between entities."""
        from_id = str(uuid4())
        to_id = str(uuid4())

        # Mint to source
        await ledger_service.mint_credits(
            entity_id=from_id,
            entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("1000.0"),
            reason="Initial mint",
        )

        # Transfer
        burn_tx, mint_tx = await ledger_service.transfer_credits(
            from_entity_id=from_id,
            from_entity_type=EntityType.AGENT,
            to_entity_id=to_id,
            to_entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("300.0"),
            reason="Test transfer",
        )

        # Verify balances
        from_balance = await ledger_service.get_balance(from_id, CreditType.COMPUTE_CREDITS)
        to_balance = await ledger_service.get_balance(to_id, CreditType.COMPUTE_CREDITS)

        assert from_balance == Decimal("700.0")
        assert to_balance == Decimal("300.0")


class TestEntityLifecycleIntegration:
    """Test entity lifecycle management."""

    @pytest.mark.asyncio
    async def test_create_agent_with_credits(self, lifecycle_manager, db_session):
        """Test creating agent with initial credit allocation."""
        agent = await lifecycle_manager.create_agent(
            agent_name="test_agent_001",
            agent_type="CODER",
        )

        assert agent.agent_name == "test_agent_001"
        assert agent.status == AgentStatus.ACTIVE.value
        assert agent.credit_balance_cc == Decimal("1000.0")  # Initial mint
        assert agent.total_credits_earned == Decimal("1000.0")

    @pytest.mark.asyncio
    async def test_collect_existence_tax(self, lifecycle_manager, db_session):
        """Test existence tax collection."""
        # Create agent
        agent = await lifecycle_manager.create_agent(
            agent_name="test_agent_002",
            agent_type="OPS",
        )

        # Collect tax
        result = await lifecycle_manager.collect_existence_tax_for_agent(agent.agent_id)

        assert result is not None
        cc_tax, sc_tax = result

        # Tax should be deducted
        assert cc_tax > Decimal("0.0")
        assert sc_tax >= Decimal("0.0")

    @pytest.mark.asyncio
    async def test_auto_suspend_on_low_credits(self, lifecycle_manager, db_session):
        """Test that agent is suspended when credits run out."""
        # Create agent
        agent = await lifecycle_manager.create_agent(
            agent_name="test_agent_003",
            agent_type="GENERIC",
        )

        # Burn almost all credits
        await lifecycle_manager.ledger.burn_credits(
            entity_id=str(agent.agent_id),
            entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("995.0"),
            reason="Drain credits",
        )

        # Attempt to collect tax (should suspend)
        result = await lifecycle_manager.collect_existence_tax_for_agent(agent.agent_id)

        # Should return None (suspended)
        assert result is None

        # Verify agent is suspended
        await db_session.refresh(agent)
        assert agent.status == AgentStatus.SUSPENDED.value


class TestCreditsServiceIntegration:
    """Test high-level credits service."""

    @pytest.mark.asyncio
    async def test_get_balance(self, credits_service, db_session):
        """Test getting entity balance."""
        # Create agent
        agent = await credits_service.create_agent(
            agent_name="test_agent_004",
            agent_type="SUPERVISOR",
        )

        # Get balance
        balance = await credits_service.get_balance(str(agent.agent_id))

        assert balance.entity_id == str(agent.agent_id)
        assert balance.entity_type == EntityType.AGENT
        assert balance.compute_credits == Decimal("1000.0")
        assert balance.total_earned == Decimal("1000.0")

    @pytest.mark.asyncio
    async def test_spend_credits(self, credits_service, db_session):
        """Test spending credits."""
        # Create agent
        agent = await credits_service.create_agent(
            agent_name="test_agent_005",
            agent_type="FLEET",
        )

        # Spend credits
        tx = await credits_service.spend_credits(
            entity_id=str(agent.agent_id),
            entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("50.0"),
            reason="Test spend",
        )

        assert tx.amount == Decimal("-50.0")
        assert tx.balance_after == Decimal("950.0")

    @pytest.mark.asyncio
    async def test_transfer_between_agents(self, credits_service, db_session):
        """Test transferring credits between agents."""
        # Create two agents
        agent1 = await credits_service.create_agent(
            agent_name="test_agent_006",
            agent_type="CODER",
        )

        agent2 = await credits_service.create_agent(
            agent_name="test_agent_007",
            agent_type="OPS",
        )

        # Transfer from agent1 to agent2
        burn_tx, mint_tx = await credits_service.transfer_credits(
            from_entity_id=str(agent1.agent_id),
            from_entity_type=EntityType.AGENT,
            to_entity_id=str(agent2.agent_id),
            to_entity_type=EntityType.AGENT,
            credit_type=CreditType.COMPUTE_CREDITS,
            amount=Decimal("200.0"),
            reason="Test transfer",
        )

        # Verify balances
        balance1 = await credits_service.get_balance(str(agent1.agent_id))
        balance2 = await credits_service.get_balance(str(agent2.agent_id))

        assert balance1.compute_credits == Decimal("800.0")
        assert balance2.compute_credits == Decimal("1200.0")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
