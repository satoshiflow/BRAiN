"""Credit Ledger - Append-only transaction log with HMAC-SHA256 integrity.

Implements Myzel-Hybrid-Charta principles:
- Immutable transaction history
- Cryptographic integrity verification
- Cooperation-based resource allocation (not rewards)
- Transparent audit trail
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Ledger secret key (should be in settings in production)
LEDGER_SECRET = "brain-ledger-secret-key-v1"  # TODO: Move to settings


class TransactionType(str):
    """Transaction types in Myzel-Hybrid system."""

    # Resource allocation (cooperation-based)
    ALLOCATION = "allocation"  # Initial credit allocation to entity
    REGENERATION = "regeneration"  # Periodic credit regeneration

    # Resource consumption (mission execution)
    CONSUMPTION = "consumption"  # Credit consumed by mission
    REFUND = "refund"  # Credit refunded (reuse, cancellation)

    # Governance actions
    WITHDRAWAL = "withdrawal"  # ImmuneService credit withdrawal (Entzug)
    TRANSFER = "transfer"  # Credit transfer between entities

    # System actions
    ADJUSTMENT = "adjustment"  # Manual adjustment (human oversight)


class LedgerEntry(BaseModel):
    """Immutable ledger entry with cryptographic integrity."""

    # Identity
    id: str = Field(default_factory=lambda: f"txn_{uuid4().hex[:16]}")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Transaction details
    transaction_type: str
    entity_id: str  # Agent ID or Mission ID
    entity_type: str  # "agent" or "mission"

    # Amounts
    amount: float  # Can be negative for consumption/withdrawal
    balance_before: float
    balance_after: float

    # Context
    reason: str
    metadata: dict = Field(default_factory=dict)

    # Integrity
    previous_hash: Optional[str] = None  # Hash of previous entry (blockchain-style)
    signature: Optional[str] = None  # HMAC-SHA256 signature

    class Config:
        frozen = True  # Immutable


class CreditLedger:
    """Append-only credit transaction ledger with cryptographic integrity.

    Implements:
    - Immutable transaction log
    - HMAC-SHA256 signatures
    - Blockchain-style hash chain
    - Balance verification
    """

    def __init__(self):
        self.entries: List[LedgerEntry] = []
        self.balances: dict[str, float] = {}  # entity_id -> current balance

    def _compute_signature(self, entry: LedgerEntry) -> str:
        """Compute HMAC-SHA256 signature for entry.

        Args:
            entry: Ledger entry to sign

        Returns:
            Hex-encoded HMAC signature
        """
        # Create canonical representation (exclude signature field)
        data = {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "transaction_type": entry.transaction_type,
            "entity_id": entry.entity_id,
            "entity_type": entry.entity_type,
            "amount": entry.amount,
            "balance_before": entry.balance_before,
            "balance_after": entry.balance_after,
            "reason": entry.reason,
            "metadata": entry.metadata,
            "previous_hash": entry.previous_hash,
        }

        canonical = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            LEDGER_SECRET.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    def _compute_entry_hash(self, entry: LedgerEntry) -> str:
        """Compute hash of entry including signature.

        Args:
            entry: Ledger entry

        Returns:
            SHA256 hash (hex-encoded)
        """
        data = {
            "id": entry.id,
            "signature": entry.signature,
            "balance_after": entry.balance_after,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()

    def append(
        self,
        transaction_type: str,
        entity_id: str,
        entity_type: str,
        amount: float,
        reason: str,
        metadata: Optional[dict] = None,
    ) -> LedgerEntry:
        """Append new transaction to ledger.

        Args:
            transaction_type: Type of transaction
            entity_id: Agent or mission ID
            entity_type: "agent" or "mission"
            amount: Credit amount (positive or negative)
            reason: Human-readable reason
            metadata: Additional context

        Returns:
            Immutable ledger entry

        Raises:
            ValueError: If balance would go negative (except for withdrawal)
        """
        # Get current balance
        balance_before = self.balances.get(entity_id, 0.0)
        balance_after = balance_before + amount

        # Validate balance (Myzel-Hybrid: no debt allowed, except immune withdrawal)
        if balance_after < 0 and transaction_type != TransactionType.WITHDRAWAL:
            raise ValueError(
                f"Insufficient credits: {entity_id} has {balance_before}, "
                f"cannot consume {abs(amount)}"
            )

        # Get previous hash for blockchain chain
        previous_hash = None
        if self.entries:
            previous_hash = self._compute_entry_hash(self.entries[-1])

        # Create entry (without signature first)
        entry = LedgerEntry(
            transaction_type=transaction_type,
            entity_id=entity_id,
            entity_type=entity_type,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reason=reason,
            metadata=metadata or {},
            previous_hash=previous_hash,
        )

        # Compute and add signature
        signature = self._compute_signature(entry)
        entry = entry.model_copy(update={"signature": signature})

        # Append to ledger
        self.entries.append(entry)
        self.balances[entity_id] = balance_after

        logger.info(
            f"[CreditLedger] {transaction_type.upper()}: {entity_type} {entity_id} "
            f"{amount:+.2f} credits (balance: {balance_before:.2f} -> {balance_after:.2f}) "
            f"- {reason}"
        )

        return entry

    def verify_integrity(self) -> tuple[bool, Optional[str]]:
        """Verify ledger integrity (signatures and hash chain).

        Returns:
            (is_valid, error_message)
        """
        if not self.entries:
            return True, None

        previous_hash = None
        for i, entry in enumerate(self.entries):
            # Verify signature
            expected_signature = self._compute_signature(entry)
            if entry.signature != expected_signature:
                return False, f"Entry {i} ({entry.id}): Invalid signature"

            # Verify hash chain
            if entry.previous_hash != previous_hash:
                return False, f"Entry {i} ({entry.id}): Broken hash chain"

            # Verify balance calculation
            expected_balance = entry.balance_before + entry.amount
            if abs(entry.balance_after - expected_balance) > 0.001:  # Float precision
                return False, f"Entry {i} ({entry.id}): Invalid balance calculation"

            previous_hash = self._compute_entry_hash(entry)

        return True, None

    def get_balance(self, entity_id: str) -> float:
        """Get current balance for entity.

        Args:
            entity_id: Agent or mission ID

        Returns:
            Current credit balance
        """
        return self.balances.get(entity_id, 0.0)

    def get_history(
        self,
        entity_id: Optional[str] = None,
        transaction_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[LedgerEntry]:
        """Get transaction history with optional filters.

        Args:
            entity_id: Filter by entity ID
            transaction_type: Filter by transaction type
            limit: Maximum entries to return

        Returns:
            List of ledger entries (newest first)
        """
        filtered = self.entries

        if entity_id:
            filtered = [e for e in filtered if e.entity_id == entity_id]

        if transaction_type:
            filtered = [e for e in filtered if e.transaction_type == transaction_type]

        # Return newest first
        return list(reversed(filtered[-limit:]))

    def get_statistics(self) -> dict:
        """Get ledger statistics.

        Returns:
            Statistics dictionary
        """
        if not self.entries:
            return {
                "total_entries": 0,
                "total_entities": 0,
                "total_credits_allocated": 0.0,
                "total_credits_consumed": 0.0,
                "total_credits_withdrawn": 0.0,
            }

        allocated = sum(
            e.amount for e in self.entries
            if e.transaction_type in [TransactionType.ALLOCATION, TransactionType.REGENERATION]
        )

        consumed = sum(
            abs(e.amount) for e in self.entries
            if e.transaction_type == TransactionType.CONSUMPTION
        )

        withdrawn = sum(
            abs(e.amount) for e in self.entries
            if e.transaction_type == TransactionType.WITHDRAWAL
        )

        return {
            "total_entries": len(self.entries),
            "total_entities": len(self.balances),
            "total_credits_allocated": allocated,
            "total_credits_consumed": consumed,
            "total_credits_withdrawn": withdrawn,
            "integrity_verified": self.verify_integrity()[0],
        }


# Global ledger instance (in production, use database persistence)
_ledger: Optional[CreditLedger] = None


def get_ledger() -> CreditLedger:
    """Get global credit ledger instance.

    Returns:
        CreditLedger instance
    """
    global _ledger
    if _ledger is None:
        _ledger = CreditLedger()
    return _ledger
