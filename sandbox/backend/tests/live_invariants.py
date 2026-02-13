"""
BRAiN Credit System Invariants Checker.

Validates critical system invariants after each test scenario:
- Ledger invariants (balance == sum(deltas), no NaN/Inf)
- Idempotency (no duplicate events)
- Approval safety (serialized decisions)
- Projection consistency (event count matches read models)

Usage:
    from live_invariants import InvariantsChecker

    checker = InvariantsChecker(credit_system)
    all_ok = await checker.check_all()
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from loguru import logger


class InvariantViolation(Exception):
    """Raised when a critical invariant is violated."""
    pass


class InvariantsChecker:
    """
    Checks critical invariants for Credit System Event Sourcing.

    Hard invariants (MUST hold):
    1. balance(agent) == sum(event_deltas)
    2. No NaN or Inf in balances
    3. No negative credits (if enforced)
    4. No duplicate idempotency keys
    5. Approval decisions serialized (max 1 final state)

    Soft invariants (SHOULD hold, warnings):
    - Event count matches projection count
    - Audit log completeness
    """

    def __init__(self, credit_system: Any):
        self.credit_system = credit_system
        self.violations: List[str] = []

    async def check_all(self, fail_fast: bool = False) -> bool:
        """
        Check all invariants.

        Args:
            fail_fast: Raise exception on first violation

        Returns:
            True if all invariants pass, False otherwise

        Raises:
            InvariantViolation: If fail_fast=True and violation detected
        """
        logger.info("🔍 Checking all invariants...")

        self.violations = []

        # Run all checks
        checks = [
            self.check_ledger_invariants(),
            self.check_no_nan_inf(),
            self.check_no_negative_credits(),
            self.check_idempotency(),
            self.check_projection_consistency(),
        ]

        all_ok = True
        for check in checks:
            try:
                ok = await check
                if not ok:
                    all_ok = False
                    if fail_fast:
                        raise InvariantViolation(
                            f"Invariant violated: {self.violations[-1]}"
                        )
            except Exception as e:
                logger.error(f"Invariant check failed: {e}")
                self.violations.append(str(e))
                all_ok = False
                if fail_fast:
                    raise

        if all_ok:
            logger.info("✅ All invariants PASS")
        else:
            logger.warning(f"⚠️ {len(self.violations)} invariant violations detected")
            for v in self.violations:
                logger.warning(f"  - {v}")

        return all_ok

    # ========================================================================
    # Ledger Invariants
    # ========================================================================

    async def check_ledger_invariants(self) -> bool:
        """
        Check: balance(agent) == sum(event_deltas)

        For each agent, the current balance must equal the sum of all
        credit allocations minus all consumptions.
        """
        logger.debug("Checking ledger invariants (balance == sum(deltas))...")

        try:
            # Get all balances
            balances = await self._get_all_balances()

            # Get all event deltas
            deltas = await self._calculate_deltas_from_events()

            # Compare
            all_ok = True
            for agent_id, balance in balances.items():
                expected_balance = deltas.get(agent_id, 0.0)

                # Floating-point tolerance
                if abs(balance - expected_balance) > 0.01:
                    violation = (
                        f"Ledger invariant violated for {agent_id}: "
                        f"balance={balance:.2f}, expected={expected_balance:.2f}, "
                        f"drift={abs(balance - expected_balance):.2f}"
                    )
                    self.violations.append(violation)
                    logger.error(violation)
                    all_ok = False

            if all_ok:
                logger.debug(f"✅ Ledger invariants OK ({len(balances)} agents)")

            return all_ok

        except Exception as e:
            logger.error(f"Failed to check ledger invariants: {e}")
            self.violations.append(f"Ledger check error: {e}")
            return False

    # ========================================================================
    # NaN / Inf Check
    # ========================================================================

    async def check_no_nan_inf(self) -> bool:
        """
        Check: No NaN or Inf in balances.

        All balances must be finite, valid floats.
        """
        logger.debug("Checking for NaN/Inf in balances...")

        try:
            balances = await self._get_all_balances()

            all_ok = True
            for agent_id, balance in balances.items():
                if math.isnan(balance):
                    violation = f"NaN detected in balance for {agent_id}"
                    self.violations.append(violation)
                    logger.error(violation)
                    all_ok = False

                if math.isinf(balance):
                    violation = f"Inf detected in balance for {agent_id}"
                    self.violations.append(violation)
                    logger.error(violation)
                    all_ok = False

            if all_ok:
                logger.debug(f"✅ No NaN/Inf ({len(balances)} agents)")

            return all_ok

        except Exception as e:
            logger.error(f"Failed to check NaN/Inf: {e}")
            self.violations.append(f"NaN/Inf check error: {e}")
            return False

    # ========================================================================
    # Negative Credits Check
    # ========================================================================

    async def check_no_negative_credits(self) -> bool:
        """
        Check: No negative credits (if enforced).

        All agent balances must be >= 0.
        Note: This is a business rule, not a mathematical invariant.
        """
        logger.debug("Checking for negative credits...")

        try:
            balances = await self._get_all_balances()

            all_ok = True
            for agent_id, balance in balances.items():
                if balance < 0:
                    violation = f"Negative balance for {agent_id}: {balance:.2f}"
                    self.violations.append(violation)
                    logger.error(violation)
                    all_ok = False

            if all_ok:
                logger.debug(f"✅ No negative credits ({len(balances)} agents)")

            return all_ok

        except Exception as e:
            logger.error(f"Failed to check negative credits: {e}")
            self.violations.append(f"Negative credits check error: {e}")
            return False

    # ========================================================================
    # Idempotency Check
    # ========================================================================

    async def check_idempotency(self) -> bool:
        """
        Check: No duplicate idempotency keys.

        All events in the journal must have unique idempotency keys.
        """
        logger.debug("Checking idempotency (no duplicate events)...")

        try:
            journal = self.credit_system.journal
            seen_keys = set()
            duplicates = []

            # Read all events
            async for event in journal.read_events():
                if event.idempotency_key in seen_keys:
                    duplicates.append(event.idempotency_key)
                seen_keys.add(event.idempotency_key)

            if duplicates:
                violation = f"Duplicate idempotency keys: {len(duplicates)} duplicates"
                self.violations.append(violation)
                logger.error(violation)
                for key in duplicates[:10]:  # Show first 10
                    logger.error(f"  - {key}")
                return False

            logger.debug(f"✅ Idempotency OK ({len(seen_keys)} unique events)")
            return True

        except Exception as e:
            logger.error(f"Failed to check idempotency: {e}")
            self.violations.append(f"Idempotency check error: {e}")
            return False

    # ========================================================================
    # Projection Consistency
    # ========================================================================

    async def check_projection_consistency(self) -> bool:
        """
        Check: Event count matches projection count.

        Soft invariant - warns if projections are lagging.
        """
        logger.debug("Checking projection consistency...")

        try:
            # Count events in journal
            event_count = 0
            async for _ in self.credit_system.journal.read_events():
                event_count += 1

            # Count entries in projections
            projection_manager = self.credit_system.projections
            balance_count = len(projection_manager.balance._balances)
            ledger_count = len(projection_manager.ledger._ledger)

            logger.debug(
                f"Event count: {event_count}, "
                f"Balance entries: {balance_count}, "
                f"Ledger entries: {ledger_count}"
            )

            # Soft check: projection count should be reasonable
            # (Not necessarily equal, as some events don't create projections)
            if balance_count == 0 and event_count > 0:
                violation = "Balance projection empty but events exist"
                self.violations.append(violation)
                logger.warning(violation)
                return False

            logger.debug("✅ Projection consistency OK")
            return True

        except Exception as e:
            logger.error(f"Failed to check projection consistency: {e}")
            self.violations.append(f"Projection consistency check error: {e}")
            return False

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _get_all_balances(self) -> Dict[str, float]:
        """Get all agent balances from projection."""
        try:
            projection_manager = self.credit_system.projections
            return dict(projection_manager.balance._balances)
        except Exception as e:
            logger.error(f"Failed to get balances: {e}")
            return {}

    async def _calculate_deltas_from_events(self) -> Dict[str, float]:
        """
        Calculate expected balances from event log.

        Replay logic:
        - CREDIT_ALLOCATED: +amount
        - CREDIT_CONSUMED: -amount
        - CREDIT_REFUNDED: +amount
        """
        deltas = {}

        try:
            async for event in self.credit_system.journal.read_events():
                entity_id = event.payload.get("entity_id")
                if not entity_id:
                    continue

                # Get amount
                amount = event.payload.get("amount", 0.0)

                # Apply delta based on event type
                if event.event_type.value == "CREDIT_ALLOCATED":
                    deltas[entity_id] = deltas.get(entity_id, 0.0) + amount
                elif event.event_type.value == "CREDIT_CONSUMED":
                    deltas[entity_id] = deltas.get(entity_id, 0.0) - amount
                elif event.event_type.value == "CREDIT_REFUNDED":
                    deltas[entity_id] = deltas.get(entity_id, 0.0) + amount

            return deltas

        except Exception as e:
            logger.error(f"Failed to calculate deltas: {e}")
            return {}

    # ========================================================================
    # Approval Safety (Optional)
    # ========================================================================

    async def check_approval_safety(self) -> bool:
        """
        Check: Approval decisions are serialized (max 1 final state per request).

        Looks for APPROVAL_APPROVED / APPROVAL_DENIED events and verifies
        that each approval request has at most one final decision.
        """
        logger.debug("Checking approval safety...")

        try:
            approval_counts = {}

            async for event in self.credit_system.journal.read_events():
                if event.event_type.value in ["APPROVAL_APPROVED", "APPROVAL_DENIED"]:
                    approval_id = event.payload.get("approval_id", "unknown")
                    approval_counts[approval_id] = approval_counts.get(approval_id, 0) + 1

            # Check for duplicates
            all_ok = True
            for approval_id, count in approval_counts.items():
                if count > 1:
                    violation = f"Approval {approval_id} has {count} final decisions"
                    self.violations.append(violation)
                    logger.error(violation)
                    all_ok = False

            if all_ok:
                logger.debug(f"✅ Approval safety OK ({len(approval_counts)} approvals)")

            return all_ok

        except Exception as e:
            logger.error(f"Failed to check approval safety: {e}")
            self.violations.append(f"Approval safety check error: {e}")
            return False

    # ========================================================================
    # Audit Log Completeness (Optional)
    # ========================================================================

    async def check_audit_log_completeness(self) -> bool:
        """
        Check: All critical events are in audit log.

        Soft check - verifies that event log has correlation/causation IDs.
        """
        logger.debug("Checking audit log completeness...")

        try:
            missing_correlation = 0
            total_events = 0

            async for event in self.credit_system.journal.read_events():
                total_events += 1
                if not event.correlation_id:
                    missing_correlation += 1

            if missing_correlation > 0:
                violation = (
                    f"Audit log incomplete: {missing_correlation}/{total_events} "
                    f"events missing correlation_id"
                )
                self.violations.append(violation)
                logger.warning(violation)
                return False

            logger.debug(f"✅ Audit log complete ({total_events} events)")
            return True

        except Exception as e:
            logger.error(f"Failed to check audit log: {e}")
            self.violations.append(f"Audit log check error: {e}")
            return False

    # ========================================================================
    # Summary Report
    # ========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of invariant checks."""
        return {
            "total_violations": len(self.violations),
            "violations": self.violations,
            "status": "PASS" if len(self.violations) == 0 else "FAIL",
        }


# ============================================================================
# Standalone CLI
# ============================================================================


async def main():
    """Standalone CLI for invariants checker."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from app.modules.credits.integration_demo import get_credit_system_demo

    logger.info("Initializing credit system...")
    credit_system = await get_credit_system_demo()

    logger.info("Running invariants checks...")
    checker = InvariantsChecker(credit_system)
    all_ok = await checker.check_all()

    summary = checker.get_summary()
    print("\n" + "=" * 80)
    print(f"Status: {summary['status']}")
    print(f"Violations: {summary['total_violations']}")
    print("=" * 80)

    if not all_ok:
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
