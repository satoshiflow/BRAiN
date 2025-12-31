"""
Resource Pools for Shared Credit Pools.

Provides team/department-level credit pooling:
- Shared pools for collaborative work
- Pool allocation and consumption
- Pool member management
- Usage tracking and analytics

Usage:
    from backend.app.modules.credits.resource_pools import ResourcePoolManager

    pool_mgr = ResourcePoolManager()
    await pool_mgr.initialize()

    # Create pool
    pool = await pool_mgr.create_pool(
        pool_id="team_alpha",
        name="Team Alpha Pool",
        initial_credits=1000.0,
        owner_id="admin"
    )

    # Add members
    await pool_mgr.add_member(pool_id="team_alpha", agent_id="agent_001")

    # Consume from pool
    await pool_mgr.consume_from_pool(
        pool_id="team_alpha",
        agent_id="agent_001",
        amount=50.0,
        reason="Mission execution"
    )
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from loguru import logger
from pydantic import BaseModel, Field

from backend.app.modules.credits.integration_demo import get_credit_system_demo


# ============================================================================
# Data Models
# ============================================================================


class ResourcePool(BaseModel):
    """Shared credit pool for team/department."""
    pool_id: str = Field(..., description="Unique pool identifier")
    name: str = Field(..., description="Human-readable name")
    balance: float = Field(0.0, ge=0, description="Current pool balance")
    initial_credits: float = Field(..., ge=0, description="Initial allocation")
    owner_id: str = Field(..., description="Pool owner (admin/manager)")
    members: Set[str] = Field(default_factory=set, description="Agent IDs with access")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict = Field(default_factory=dict, description="Custom metadata")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            set: lambda v: list(v),
        }


class PoolTransaction(BaseModel):
    """Transaction record for pool operations."""
    transaction_id: str
    pool_id: str
    agent_id: Optional[str] = None
    operation: str  # "allocate", "consume", "refund", "transfer"
    amount: float
    balance_after: float
    reason: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mission_id: Optional[str] = None


class PoolStats(BaseModel):
    """Statistics for a resource pool."""
    pool_id: str
    total_allocated: float
    total_consumed: float
    total_refunded: float
    balance: float
    utilization_rate: float  # consumed / allocated
    member_count: int
    transaction_count: int


# ============================================================================
# Resource Pool Manager
# ============================================================================


class ResourcePoolManager:
    """
    Manager for shared credit pools.

    Features:
    - Create and manage pools
    - Member management
    - Pool consumption and refunds
    - Inter-pool transfers
    - Usage analytics
    """

    def __init__(self):
        self.credit_system = None
        self._pools: Dict[str, ResourcePool] = {}
        self._transactions: List[PoolTransaction] = []

    async def initialize(self) -> None:
        """Initialize pool manager."""
        try:
            self.credit_system = await get_credit_system_demo()
            logger.info("Resource Pool Manager initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Resource Pool Manager: {e}")
            raise

    # ========================================================================
    # Pool Management
    # ========================================================================

    async def create_pool(
        self,
        pool_id: str,
        name: str,
        initial_credits: float,
        owner_id: str,
        metadata: Optional[Dict] = None,
    ) -> ResourcePool:
        """
        Create a new resource pool.

        Args:
            pool_id: Unique identifier
            name: Human-readable name
            initial_credits: Initial credit allocation
            owner_id: Pool owner/manager ID
            metadata: Optional custom metadata

        Returns:
            Created ResourcePool

        Raises:
            ValueError: If pool_id already exists or invalid parameters
        """
        if pool_id in self._pools:
            raise ValueError(f"Pool {pool_id} already exists")

        if initial_credits < 0:
            raise ValueError("initial_credits must be >= 0")

        pool = ResourcePool(
            pool_id=pool_id,
            name=name,
            balance=initial_credits,
            initial_credits=initial_credits,
            owner_id=owner_id,
            metadata=metadata or {},
        )

        self._pools[pool_id] = pool

        # Record allocation transaction
        await self._record_transaction(
            pool_id=pool_id,
            operation="allocate",
            amount=initial_credits,
            balance_after=initial_credits,
            reason=f"Pool creation: {name}",
            agent_id=owner_id,
        )

        logger.info(
            f"Created pool {pool_id} with {initial_credits} credits",
            pool_id=pool_id,
            owner_id=owner_id,
        )

        return pool

    async def get_pool(self, pool_id: str) -> Optional[ResourcePool]:
        """Get pool by ID."""
        return self._pools.get(pool_id)

    async def list_pools(self) -> List[ResourcePool]:
        """List all pools."""
        return list(self._pools.values())

    async def delete_pool(self, pool_id: str, refund_to: Optional[str] = None) -> bool:
        """
        Delete a pool.

        Args:
            pool_id: Pool to delete
            refund_to: Optional agent ID to refund remaining balance

        Returns:
            True if deleted, False if pool not found
        """
        pool = self._pools.get(pool_id)
        if not pool:
            return False

        # Refund remaining balance if requested
        if refund_to and pool.balance > 0:
            try:
                await self.credit_system.refund_credits(
                    agent_id=refund_to,
                    amount=pool.balance,
                    reason=f"Pool deletion: {pool.name}",
                    actor_id="pool_manager",
                )
            except Exception as e:
                logger.warning(f"Failed to refund pool balance: {e}")

        del self._pools[pool_id]
        logger.info(f"Deleted pool {pool_id}")
        return True

    # ========================================================================
    # Member Management
    # ========================================================================

    async def add_member(self, pool_id: str, agent_id: str) -> bool:
        """
        Add member to pool.

        Args:
            pool_id: Pool ID
            agent_id: Agent to add

        Returns:
            True if added, False if pool not found

        Raises:
            ValueError: If agent already a member
        """
        pool = self._pools.get(pool_id)
        if not pool:
            return False

        if agent_id in pool.members:
            raise ValueError(f"Agent {agent_id} already member of pool {pool_id}")

        pool.members.add(agent_id)
        pool.updated_at = datetime.utcnow()

        logger.info(f"Added {agent_id} to pool {pool_id}")
        return True

    async def remove_member(self, pool_id: str, agent_id: str) -> bool:
        """
        Remove member from pool.

        Args:
            pool_id: Pool ID
            agent_id: Agent to remove

        Returns:
            True if removed, False if pool not found or agent not member
        """
        pool = self._pools.get(pool_id)
        if not pool or agent_id not in pool.members:
            return False

        pool.members.remove(agent_id)
        pool.updated_at = datetime.utcnow()

        logger.info(f"Removed {agent_id} from pool {pool_id}")
        return True

    async def is_member(self, pool_id: str, agent_id: str) -> bool:
        """Check if agent is pool member."""
        pool = self._pools.get(pool_id)
        return pool is not None and agent_id in pool.members

    # ========================================================================
    # Pool Operations
    # ========================================================================

    async def allocate_to_pool(
        self,
        pool_id: str,
        amount: float,
        reason: str,
        actor_id: str = "system",
    ) -> float:
        """
        Allocate additional credits to pool.

        Args:
            pool_id: Pool ID
            amount: Credits to allocate
            reason: Allocation reason
            actor_id: Who allocated

        Returns:
            New pool balance

        Raises:
            ValueError: If pool not found or amount invalid
        """
        pool = self._pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")

        if amount <= 0:
            raise ValueError("amount must be > 0")

        pool.balance += amount
        pool.updated_at = datetime.utcnow()

        await self._record_transaction(
            pool_id=pool_id,
            operation="allocate",
            amount=amount,
            balance_after=pool.balance,
            reason=reason,
            agent_id=actor_id,
        )

        logger.info(
            f"Allocated {amount} to pool {pool_id}",
            balance_after=pool.balance,
        )

        return pool.balance

    async def consume_from_pool(
        self,
        pool_id: str,
        agent_id: str,
        amount: float,
        reason: str,
        mission_id: Optional[str] = None,
    ) -> float:
        """
        Consume credits from pool.

        Args:
            pool_id: Pool ID
            agent_id: Agent consuming credits
            amount: Credits to consume
            reason: Consumption reason
            mission_id: Related mission (optional)

        Returns:
            New pool balance

        Raises:
            ValueError: If pool not found, insufficient credits, or not member
        """
        pool = self._pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")

        if agent_id not in pool.members:
            raise ValueError(f"Agent {agent_id} not member of pool {pool_id}")

        if amount <= 0:
            raise ValueError("amount must be > 0")

        if pool.balance < amount:
            raise ValueError(
                f"Insufficient pool credits: {pool.balance} < {amount}"
            )

        pool.balance -= amount
        pool.updated_at = datetime.utcnow()

        await self._record_transaction(
            pool_id=pool_id,
            operation="consume",
            amount=amount,
            balance_after=pool.balance,
            reason=reason,
            agent_id=agent_id,
            mission_id=mission_id,
        )

        logger.info(
            f"Consumed {amount} from pool {pool_id} by {agent_id}",
            balance_after=pool.balance,
        )

        return pool.balance

    async def refund_to_pool(
        self,
        pool_id: str,
        agent_id: str,
        amount: float,
        reason: str,
        mission_id: Optional[str] = None,
    ) -> float:
        """
        Refund credits to pool.

        Args:
            pool_id: Pool ID
            agent_id: Agent refunding credits
            amount: Credits to refund
            reason: Refund reason
            mission_id: Related mission (optional)

        Returns:
            New pool balance

        Raises:
            ValueError: If pool not found or amount invalid
        """
        pool = self._pools.get(pool_id)
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")

        if amount <= 0:
            raise ValueError("amount must be > 0")

        pool.balance += amount
        pool.updated_at = datetime.utcnow()

        await self._record_transaction(
            pool_id=pool_id,
            operation="refund",
            amount=amount,
            balance_after=pool.balance,
            reason=reason,
            agent_id=agent_id,
            mission_id=mission_id,
        )

        logger.info(
            f"Refunded {amount} to pool {pool_id} by {agent_id}",
            balance_after=pool.balance,
        )

        return pool.balance

    async def transfer_between_pools(
        self,
        from_pool_id: str,
        to_pool_id: str,
        amount: float,
        reason: str,
        actor_id: str = "system",
    ) -> Dict[str, float]:
        """
        Transfer credits between pools.

        Args:
            from_pool_id: Source pool
            to_pool_id: Destination pool
            amount: Credits to transfer
            reason: Transfer reason
            actor_id: Who initiated transfer

        Returns:
            Dict with from_balance and to_balance

        Raises:
            ValueError: If pools not found or insufficient credits
        """
        from_pool = self._pools.get(from_pool_id)
        to_pool = self._pools.get(to_pool_id)

        if not from_pool:
            raise ValueError(f"Source pool {from_pool_id} not found")
        if not to_pool:
            raise ValueError(f"Destination pool {to_pool_id} not found")

        if amount <= 0:
            raise ValueError("amount must be > 0")

        if from_pool.balance < amount:
            raise ValueError(
                f"Insufficient credits in source pool: {from_pool.balance} < {amount}"
            )

        # Deduct from source
        from_pool.balance -= amount
        from_pool.updated_at = datetime.utcnow()

        # Add to destination
        to_pool.balance += amount
        to_pool.updated_at = datetime.utcnow()

        # Record transactions
        await self._record_transaction(
            pool_id=from_pool_id,
            operation="transfer_out",
            amount=amount,
            balance_after=from_pool.balance,
            reason=f"Transfer to {to_pool_id}: {reason}",
            agent_id=actor_id,
        )

        await self._record_transaction(
            pool_id=to_pool_id,
            operation="transfer_in",
            amount=amount,
            balance_after=to_pool.balance,
            reason=f"Transfer from {from_pool_id}: {reason}",
            agent_id=actor_id,
        )

        logger.info(
            f"Transferred {amount} from {from_pool_id} to {to_pool_id}",
            from_balance=from_pool.balance,
            to_balance=to_pool.balance,
        )

        return {
            "from_balance": from_pool.balance,
            "to_balance": to_pool.balance,
        }

    # ========================================================================
    # Analytics
    # ========================================================================

    async def get_pool_stats(self, pool_id: str) -> Optional[PoolStats]:
        """
        Get statistics for pool.

        Args:
            pool_id: Pool ID

        Returns:
            PoolStats or None if pool not found
        """
        pool = self._pools.get(pool_id)
        if not pool:
            return None

        # Calculate stats from transactions
        total_allocated = 0.0
        total_consumed = 0.0
        total_refunded = 0.0
        transaction_count = 0

        for txn in self._transactions:
            if txn.pool_id == pool_id:
                transaction_count += 1
                if txn.operation in ("allocate", "transfer_in"):
                    total_allocated += txn.amount
                elif txn.operation == "consume":
                    total_consumed += txn.amount
                elif txn.operation in ("refund", "transfer_out"):
                    total_refunded += txn.amount

        utilization_rate = (
            (total_consumed / total_allocated * 100) if total_allocated > 0 else 0.0
        )

        return PoolStats(
            pool_id=pool_id,
            total_allocated=round(total_allocated, 2),
            total_consumed=round(total_consumed, 2),
            total_refunded=round(total_refunded, 2),
            balance=round(pool.balance, 2),
            utilization_rate=round(utilization_rate, 2),
            member_count=len(pool.members),
            transaction_count=transaction_count,
        )

    async def get_pool_transactions(
        self,
        pool_id: str,
        limit: Optional[int] = 50,
    ) -> List[PoolTransaction]:
        """
        Get transaction history for pool.

        Args:
            pool_id: Pool ID
            limit: Max transactions (most recent first)

        Returns:
            List of transactions
        """
        pool_txns = [txn for txn in self._transactions if txn.pool_id == pool_id]
        pool_txns.sort(key=lambda t: t.timestamp, reverse=True)

        if limit:
            pool_txns = pool_txns[:limit]

        return pool_txns

    async def get_member_usage(
        self,
        pool_id: str,
        days: int = 30,
    ) -> Dict[str, Dict]:
        """
        Get usage breakdown by member.

        Args:
            pool_id: Pool ID
            days: Period to analyze

        Returns:
            Dict mapping agent_id to usage stats
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        usage = defaultdict(lambda: {"consumed": 0.0, "refunded": 0.0, "count": 0})

        for txn in self._transactions:
            if txn.pool_id == pool_id and txn.timestamp > cutoff and txn.agent_id:
                if txn.operation == "consume":
                    usage[txn.agent_id]["consumed"] += txn.amount
                    usage[txn.agent_id]["count"] += 1
                elif txn.operation == "refund":
                    usage[txn.agent_id]["refunded"] += txn.amount

        # Calculate net for each member
        for agent_id, stats in usage.items():
            stats["net"] = round(stats["consumed"] - stats["refunded"], 2)
            stats["consumed"] = round(stats["consumed"], 2)
            stats["refunded"] = round(stats["refunded"], 2)

        return dict(usage)

    # ========================================================================
    # Internal Helpers
    # ========================================================================

    async def _record_transaction(
        self,
        pool_id: str,
        operation: str,
        amount: float,
        balance_after: float,
        reason: str,
        agent_id: Optional[str] = None,
        mission_id: Optional[str] = None,
    ) -> None:
        """Record pool transaction."""
        import uuid

        txn = PoolTransaction(
            transaction_id=str(uuid.uuid4()),
            pool_id=pool_id,
            agent_id=agent_id,
            operation=operation,
            amount=amount,
            balance_after=balance_after,
            reason=reason,
            mission_id=mission_id,
        )

        self._transactions.append(txn)


# ============================================================================
# Singleton Pattern
# ============================================================================

_pool_manager_instance: Optional[ResourcePoolManager] = None


async def get_pool_manager() -> ResourcePoolManager:
    """
    Get singleton ResourcePoolManager instance.

    Returns:
        ResourcePoolManager instance (initialized)
    """
    global _pool_manager_instance

    if _pool_manager_instance is None:
        _pool_manager_instance = ResourcePoolManager()
        await _pool_manager_instance.initialize()

    return _pool_manager_instance
