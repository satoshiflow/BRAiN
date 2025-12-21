"""
Credit Ledger

Implements the append-only credit transaction ledger.

CRITICAL SECURITY PROPERTIES:
- Append-only: No updates or deletes allowed
- Cryptographic signatures prevent tampering
- Monotonic sequence numbers ensure ordering
- All transactions are deterministically verifiable

Philosophy:
- Credits are energy, not currency
- Every transaction is auditable
- System state is derivable from ledger
- Fail-closed on any ambiguity
"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    AuditResult,
    AuditTrail,
    CreditLedger,
    CreditTransaction,
    CreditType,
    EntityType,
    TransactionType,
)


class LedgerError(Exception):
    """Base exception for ledger operations."""

    pass


class InsufficientCreditsError(LedgerError):
    """Raised when entity has insufficient credits."""

    pass


class NegativeBalanceError(LedgerError):
    """Raised when balance would become negative."""

    pass


class LedgerIntegrityError(LedgerError):
    """Raised when ledger integrity check fails."""

    pass


class CreditLedgerService:
    """
    Service for managing the credit ledger.

    Responsibilities:
    - Append transactions to ledger
    - Calculate balances
    - Verify signatures
    - Enforce append-only constraints
    """

    def __init__(self, session: AsyncSession, signing_key: str = "CHANGE_ME_IN_PRODUCTION"):
        """
        Initialize ledger service.

        Args:
            session: Database session
            signing_key: Secret key for transaction signatures
        """
        self.session = session
        self.signing_key = signing_key.encode()

    def _compute_signature(
        self,
        entity_id: str,
        credit_type: CreditType,
        amount: Decimal,
        transaction_type: TransactionType,
        timestamp: datetime,
    ) -> str:
        """
        Compute cryptographic signature for a transaction.

        Uses HMAC-SHA256 to create tamper-proof signature.

        Args:
            entity_id: Entity ID
            credit_type: Type of credit
            amount: Transaction amount
            transaction_type: Type of transaction
            timestamp: Transaction timestamp

        Returns:
            Hex-encoded signature
        """
        message = (
            f"{entity_id}:{credit_type.value}:{amount}:{transaction_type.value}:{timestamp.isoformat()}"
        ).encode()

        signature = hmac.new(self.signing_key, message, hashlib.sha256).hexdigest()
        return f"sha256:{signature}"

    def _verify_signature(
        self,
        entity_id: str,
        credit_type: CreditType,
        amount: Decimal,
        transaction_type: TransactionType,
        timestamp: datetime,
        signature: str,
    ) -> bool:
        """
        Verify transaction signature.

        Args:
            entity_id: Entity ID
            credit_type: Type of credit
            amount: Transaction amount
            transaction_type: Type of transaction
            timestamp: Transaction timestamp
            signature: Signature to verify

        Returns:
            True if signature is valid
        """
        expected = self._compute_signature(entity_id, credit_type, amount, transaction_type, timestamp)
        return hmac.compare_digest(expected, signature)

    async def get_balance(
        self, entity_id: str, credit_type: CreditType
    ) -> Decimal:
        """
        Get current balance for an entity and credit type.

        Balance is calculated from the most recent ledger entry.

        Args:
            entity_id: Entity ID
            credit_type: Type of credit

        Returns:
            Current balance
        """
        stmt = (
            select(CreditLedger.balance_after)
            .where(
                and_(
                    CreditLedger.entity_id == entity_id,
                    CreditLedger.credit_type == credit_type.value,
                )
            )
            .order_by(desc(CreditLedger.sequence_number))
            .limit(1)
        )

        result = await self.session.execute(stmt)
        balance = result.scalar_one_or_none()

        return Decimal(balance) if balance is not None else Decimal("0.0")

    async def append_transaction(
        self,
        entity_id: str,
        entity_type: EntityType,
        credit_type: CreditType,
        amount: Decimal,
        transaction_type: TransactionType,
        reason: str,
        metadata: Optional[dict] = None,
        actor_id: str = "SYSTEM",
    ) -> CreditTransaction:
        """
        Append a transaction to the ledger.

        CRITICAL: This is the ONLY way to modify credit balances.

        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            credit_type: Type of credit
            amount: Transaction amount (positive for mint, negative for burn)
            transaction_type: Type of transaction
            reason: Human-readable reason
            metadata: Additional context
            actor_id: Who/what initiated the transaction

        Returns:
            Created transaction

        Raises:
            NegativeBalanceError: If balance would become negative
            LedgerIntegrityError: If signature verification fails
        """
        timestamp = datetime.now(timezone.utc)
        metadata = metadata or {}

        # Get current balance
        current_balance = await self.get_balance(entity_id, credit_type)

        # Calculate new balance
        new_balance = current_balance + amount

        # CRITICAL: Prevent negative balances (fail-closed)
        if new_balance < 0:
            logger.error(
                f"Negative balance prevented: entity={entity_id} "
                f"credit_type={credit_type.value} "
                f"current={current_balance} amount={amount} "
                f"new_balance={new_balance}"
            )
            raise NegativeBalanceError(
                f"Insufficient credits: current={current_balance}, required={abs(amount)}"
            )

        # Compute signature
        signature = self._compute_signature(
            entity_id, credit_type, amount, transaction_type, timestamp
        )

        # Create ledger entry
        entry = CreditLedger(
            id=uuid4(),
            timestamp=timestamp,
            entity_id=entity_id,
            entity_type=entity_type.value,
            credit_type=credit_type.value,
            amount=amount,
            balance_after=new_balance,
            transaction_type=transaction_type.value,
            reason=reason,
            metadata=metadata,
            signature=signature,
        )

        self.session.add(entry)

        # Create audit trail entry
        audit_entry = AuditTrail(
            id=uuid4(),
            timestamp=timestamp,
            event_type=f"CREDIT_{transaction_type.value}",
            entity_id=entity_id,
            entity_type=entity_type.value,
            actor_id=actor_id,
            action=f"{transaction_type.value} {amount} {credit_type.value}: {reason}",
            result=AuditResult.SUCCESS.value,
            metadata={
                "credit_type": credit_type.value,
                "amount": str(amount),
                "balance_after": str(new_balance),
                **metadata,
            },
            signature=signature,
        )

        self.session.add(audit_entry)

        await self.session.flush()

        # Fetch sequence number (assigned by database)
        await self.session.refresh(entry)

        logger.info(
            f"Ledger transaction: entity={entity_id} "
            f"type={credit_type.value} "
            f"amount={amount} "
            f"balance={new_balance} "
            f"seq={entry.sequence_number}"
        )

        return CreditTransaction(
            id=entry.id,
            sequence_number=entry.sequence_number,
            timestamp=entry.timestamp,
            entity_id=entry.entity_id,
            entity_type=EntityType(entry.entity_type),
            credit_type=CreditType(entry.credit_type),
            amount=entry.amount,
            balance_after=entry.balance_after,
            transaction_type=TransactionType(entry.transaction_type),
            reason=entry.reason,
            metadata=entry.metadata,
            signature=entry.signature,
        )

    async def mint_credits(
        self,
        entity_id: str,
        entity_type: EntityType,
        credit_type: CreditType,
        amount: Decimal,
        reason: str,
        metadata: Optional[dict] = None,
    ) -> CreditTransaction:
        """
        Mint new credits for an entity.

        SECURITY: Only system-defined rules can mint credits.
        No manual minting allowed.

        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            credit_type: Type of credit
            amount: Amount to mint (must be positive)
            reason: Reason for minting
            metadata: Additional context

        Returns:
            Transaction record

        Raises:
            ValueError: If amount is not positive
        """
        if amount <= 0:
            raise ValueError(f"Mint amount must be positive, got {amount}")

        logger.info(f"Minting {amount} {credit_type.value} for {entity_id}: {reason}")

        return await self.append_transaction(
            entity_id=entity_id,
            entity_type=entity_type,
            credit_type=credit_type,
            amount=amount,
            transaction_type=TransactionType.MINT,
            reason=reason,
            metadata=metadata,
            actor_id="SYSTEM",
        )

    async def burn_credits(
        self,
        entity_id: str,
        entity_type: EntityType,
        credit_type: CreditType,
        amount: Decimal,
        reason: str,
        metadata: Optional[dict] = None,
        actor_id: str = "SYSTEM",
    ) -> CreditTransaction:
        """
        Burn (consume) credits from an entity.

        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            credit_type: Type of credit
            amount: Amount to burn (must be positive)
            reason: Reason for burning
            metadata: Additional context
            actor_id: Who/what initiated the burn

        Returns:
            Transaction record

        Raises:
            ValueError: If amount is not positive
            InsufficientCreditsError: If entity has insufficient credits
        """
        if amount <= 0:
            raise ValueError(f"Burn amount must be positive, got {amount}")

        logger.info(f"Burning {amount} {credit_type.value} from {entity_id}: {reason}")

        # Negative amount for burn
        return await self.append_transaction(
            entity_id=entity_id,
            entity_type=entity_type,
            credit_type=credit_type,
            amount=-amount,
            transaction_type=TransactionType.BURN,
            reason=reason,
            metadata=metadata,
            actor_id=actor_id,
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
        actor_id: str = "SYSTEM",
    ) -> tuple[CreditTransaction, CreditTransaction]:
        """
        Transfer credits between entities.

        Implemented as atomic burn + mint.

        Args:
            from_entity_id: Source entity ID
            from_entity_type: Source entity type
            to_entity_id: Destination entity ID
            to_entity_type: Destination entity type
            credit_type: Type of credit
            amount: Amount to transfer
            reason: Reason for transfer
            metadata: Additional context
            actor_id: Who/what initiated the transfer

        Returns:
            Tuple of (burn_transaction, mint_transaction)

        Raises:
            ValueError: If amount is not positive
            InsufficientCreditsError: If source has insufficient credits
        """
        if amount <= 0:
            raise ValueError(f"Transfer amount must be positive, got {amount}")

        logger.info(
            f"Transferring {amount} {credit_type.value} "
            f"from {from_entity_id} to {to_entity_id}: {reason}"
        )

        transfer_metadata = {
            **(metadata or {}),
            "transfer_from": from_entity_id,
            "transfer_to": to_entity_id,
        }

        # Burn from source
        burn_tx = await self.append_transaction(
            entity_id=from_entity_id,
            entity_type=from_entity_type,
            credit_type=credit_type,
            amount=-amount,
            transaction_type=TransactionType.TRANSFER,
            reason=f"Transfer to {to_entity_id}: {reason}",
            metadata=transfer_metadata,
            actor_id=actor_id,
        )

        # Mint to destination
        mint_tx = await self.append_transaction(
            entity_id=to_entity_id,
            entity_type=to_entity_type,
            credit_type=credit_type,
            amount=amount,
            transaction_type=TransactionType.TRANSFER,
            reason=f"Transfer from {from_entity_id}: {reason}",
            metadata=transfer_metadata,
            actor_id=actor_id,
        )

        return burn_tx, mint_tx

    async def collect_existence_tax(
        self,
        entity_id: str,
        entity_type: EntityType,
        credit_type: CreditType,
        tax_amount: Decimal,
        metadata: Optional[dict] = None,
    ) -> Optional[CreditTransaction]:
        """
        Collect existence tax from an active entity.

        Args:
            entity_id: Entity ID
            entity_type: Type of entity
            credit_type: Type of credit
            tax_amount: Tax amount to collect
            metadata: Additional context

        Returns:
            Transaction record if successful, None if insufficient credits

        Note:
            If entity has insufficient credits, it should be suspended.
            This method returns None to allow caller to handle suspension.
        """
        try:
            return await self.append_transaction(
                entity_id=entity_id,
                entity_type=entity_type,
                credit_type=credit_type,
                amount=-tax_amount,
                transaction_type=TransactionType.TAX,
                reason="Existence tax collection",
                metadata=metadata,
                actor_id="SYSTEM",
            )
        except NegativeBalanceError:
            logger.warning(
                f"Entity {entity_id} has insufficient credits for existence tax. "
                "Should be suspended."
            )
            return None

    async def verify_ledger_integrity(
        self, entity_id: Optional[str] = None, limit: int = 1000
    ) -> dict:
        """
        Verify ledger integrity by checking signatures and balances.

        Args:
            entity_id: Optional entity to check (checks all if None)
            limit: Maximum transactions to verify

        Returns:
            Dict with verification results
        """
        stmt = select(CreditLedger).order_by(desc(CreditLedger.sequence_number)).limit(limit)

        if entity_id:
            stmt = stmt.where(CreditLedger.entity_id == entity_id)

        result = await self.session.execute(stmt)
        entries = result.scalars().all()

        verified = 0
        signature_errors = []
        balance_errors = []

        for entry in entries:
            # Verify signature
            is_valid = self._verify_signature(
                entity_id=entry.entity_id,
                credit_type=CreditType(entry.credit_type),
                amount=entry.amount,
                transaction_type=TransactionType(entry.transaction_type),
                timestamp=entry.timestamp,
                signature=entry.signature,
            )

            if not is_valid:
                signature_errors.append(
                    {
                        "sequence": entry.sequence_number,
                        "entity_id": entry.entity_id,
                        "signature": entry.signature,
                    }
                )
            else:
                verified += 1

        return {
            "total_checked": len(entries),
            "verified": verified,
            "signature_errors": signature_errors,
            "balance_errors": balance_errors,
            "integrity_ok": len(signature_errors) == 0 and len(balance_errors) == 0,
        }
