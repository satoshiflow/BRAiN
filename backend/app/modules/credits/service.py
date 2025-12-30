"""Credit Service - Main credit system orchestration.

Implements Myzel-Hybrid-Charta v2.0:
- Append-only ledger with HMAC-SHA256
- Deterministic skill-based allocation
- Edge-of-Chaos regulated regeneration
- Immune System integration (Entzug)
- Synergie-Mechanik (reuse, cooperation)
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict
import logging

from .schemas import CreditsHealth, CreditsInfo
from .ledger import get_ledger, LedgerEntry, TransactionType
from .calculator import get_calculator
from .lifecycle import get_lifecycle_manager, EntityState

logger = logging.getLogger(__name__)

MODULE_NAME = "brain.credits"
MODULE_VERSION = "2.0.0"  # v2.0: Full credit system with Myzel-Hybrid-Charta

# Optional EventStream import (Sprint 5: EventStream Integration)
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Module-level EventStream (Sprint 5: EventStream Integration)
_event_stream: Optional["EventStream"] = None


def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for Credits module (Sprint 5)."""
    global _event_stream
    _event_stream = stream


async def _emit_event_safe(event_type: str, payload: dict) -> None:
    """Emit Credits event with error handling (non-blocking).

    Args:
        event_type: Event type (e.g., "credits.health_checked")
        payload: Event payload dictionary

    Note:
        - Never raises exceptions
        - Logs failures at ERROR level
        - Gracefully handles missing EventStream
    """
    global _event_stream
    if _event_stream is None or Event is None:
        logger.debug("[CreditsService] EventStream not available, skipping event")
        return

    try:
        event = Event(
            type=event_type,
            source="credits_service",
            target=None,
            payload=payload
        )
        await _event_stream.publish(event)
    except Exception as e:
        logger.error(f"[CreditsService] Event publishing failed: {e}", exc_info=True)


# ============================================================================
# Core Credit Operations
# ============================================================================

async def create_agent_account(
    agent_id: str,
    skill_level: Optional[float] = None,
) -> Dict:
    """Create credit account for new agent.

    Args:
        agent_id: Agent identifier
        skill_level: Skill level (0.0-1.0)

    Returns:
        Account info with initial balance

    Events:
        - credits.agent_created
    """
    lifecycle = get_lifecycle_manager()

    balance = await lifecycle.create_agent(
        agent_id=agent_id,
        skill_level=skill_level,
    )

    await _emit_event_safe("credits.agent_created", {
        "agent_id": agent_id,
        "balance": balance,
        "skill_level": skill_level,
    })

    return {
        "agent_id": agent_id,
        "balance": balance,
        "skill_level": skill_level,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def create_mission_budget(
    mission_id: str,
    complexity: float = 1.0,
    estimated_duration_hours: float = 1.0,
) -> Dict:
    """Create credit budget for new mission.

    Args:
        mission_id: Mission identifier
        complexity: Mission complexity
        estimated_duration_hours: Estimated duration

    Returns:
        Budget info

    Events:
        - credits.mission_created
    """
    lifecycle = get_lifecycle_manager()

    balance = await lifecycle.create_mission(
        mission_id=mission_id,
        complexity=complexity,
        estimated_duration_hours=estimated_duration_hours,
    )

    await _emit_event_safe("credits.mission_created", {
        "mission_id": mission_id,
        "balance": balance,
        "complexity": complexity,
        "estimated_duration_hours": estimated_duration_hours,
    })

    return {
        "mission_id": mission_id,
        "balance": balance,
        "complexity": complexity,
        "estimated_duration_hours": estimated_duration_hours,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


async def consume_credits(
    entity_id: str,
    amount: float,
    reason: str,
    metadata: Optional[dict] = None,
) -> Dict:
    """Consume credits from entity.

    Args:
        entity_id: Entity identifier
        amount: Credit amount to consume
        reason: Consumption reason
        metadata: Additional context

    Returns:
        Consumption result

    Events:
        - credits.consumed

    Raises:
        ValueError: If insufficient credits
    """
    lifecycle = get_lifecycle_manager()

    new_balance = await lifecycle.consume_credits(
        entity_id=entity_id,
        amount=amount,
        reason=reason,
        metadata=metadata,
    )

    await _emit_event_safe("credits.consumed", {
        "entity_id": entity_id,
        "amount": amount,
        "new_balance": new_balance,
        "reason": reason,
    })

    return {
        "entity_id": entity_id,
        "amount_consumed": amount,
        "new_balance": new_balance,
        "reason": reason,
    }


async def check_sufficient_credits(entity_id: str, required_amount: float) -> bool:
    """Check if entity has sufficient credits.

    Args:
        entity_id: Entity identifier
        required_amount: Required credit amount

    Returns:
        True if sufficient credits, False otherwise
    """
    ledger = get_ledger()
    current_balance = ledger.get_balance(entity_id)
    return current_balance >= required_amount


async def withdraw_credits(
    entity_id: str,
    severity: str,
    reason: str,
    metadata: Optional[dict] = None,
) -> Dict:
    """Withdraw credits (ImmuneService Entzug).

    Args:
        entity_id: Entity identifier
        severity: Severity level ("low", "medium", "high", "critical")
        reason: Withdrawal reason
        metadata: Additional context

    Returns:
        Withdrawal result

    Events:
        - credits.withdrawn
    """
    lifecycle = get_lifecycle_manager()

    withdrawal_amount = await lifecycle.withdraw_credits(
        entity_id=entity_id,
        severity=severity,
        reason=reason,
        metadata=metadata,
    )

    await _emit_event_safe("credits.withdrawn", {
        "entity_id": entity_id,
        "amount": withdrawal_amount,
        "severity": severity,
        "reason": reason,
    })

    return {
        "entity_id": entity_id,
        "amount_withdrawn": withdrawal_amount,
        "severity": severity,
        "reason": reason,
    }


async def refund_credits(
    entity_id: str,
    original_allocation: float,
    work_completed_percentage: float,
    reason: str,
) -> Dict:
    """Refund credits (Synergie-Mechanik).

    Args:
        entity_id: Entity identifier
        original_allocation: Original allocation
        work_completed_percentage: Work completion (0.0-1.0)
        reason: Refund reason

    Returns:
        Refund result

    Events:
        - credits.refunded
    """
    lifecycle = get_lifecycle_manager()

    refund_amount = await lifecycle.refund_credits(
        entity_id=entity_id,
        original_allocation=original_allocation,
        work_completed_percentage=work_completed_percentage,
        reason=reason,
    )

    await _emit_event_safe("credits.refunded", {
        "entity_id": entity_id,
        "amount": refund_amount,
        "reason": reason,
    })

    return {
        "entity_id": entity_id,
        "amount_refunded": refund_amount,
        "reason": reason,
    }


# ============================================================================
# Query Operations
# ============================================================================

async def get_balance(entity_id: str) -> float:
    """Get current credit balance for entity.

    Args:
        entity_id: Entity identifier

    Returns:
        Current balance
    """
    ledger = get_ledger()
    return ledger.get_balance(entity_id)


async def get_transaction_history(
    entity_id: Optional[str] = None,
    transaction_type: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    """Get transaction history.

    Args:
        entity_id: Filter by entity ID
        transaction_type: Filter by transaction type
        limit: Maximum entries

    Returns:
        List of transactions
    """
    ledger = get_ledger()
    entries = ledger.get_history(
        entity_id=entity_id,
        transaction_type=transaction_type,
        limit=limit,
    )

    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "transaction_type": e.transaction_type,
            "entity_id": e.entity_id,
            "entity_type": e.entity_type,
            "amount": e.amount,
            "balance_before": e.balance_before,
            "balance_after": e.balance_after,
            "reason": e.reason,
            "metadata": e.metadata,
        }
        for e in entries
    ]


async def get_ledger_statistics() -> Dict:
    """Get ledger statistics.

    Returns:
        Statistics dictionary
    """
    ledger = get_ledger()
    return ledger.get_statistics()


async def verify_ledger_integrity() -> Dict:
    """Verify ledger integrity.

    Returns:
        Verification result
    """
    ledger = get_ledger()
    is_valid, error_message = ledger.verify_integrity()

    return {
        "is_valid": is_valid,
        "error_message": error_message,
        "total_entries": len(ledger.entries),
    }


# ============================================================================
# Lifecycle Management
# ============================================================================

async def start_regeneration() -> Dict:
    """Start background credit regeneration.

    Returns:
        Start confirmation
    """
    lifecycle = get_lifecycle_manager()
    await lifecycle.start_regeneration_loop()

    return {
        "status": "started",
        "interval_seconds": lifecycle.regeneration_interval_seconds,
    }


async def stop_regeneration() -> Dict:
    """Stop background credit regeneration.

    Returns:
        Stop confirmation
    """
    lifecycle = get_lifecycle_manager()
    await lifecycle.stop_regeneration_loop()

    return {"status": "stopped"}


# ============================================================================
# Health & Info (Legacy compatibility)
# ============================================================================

async def get_health() -> CreditsHealth:
    """Get Credits module health status.

    Returns:
        CreditsHealth: Health status object

    Events:
        - credits.health_checked (optional): Health check performed
    """
    result = CreditsHealth(status="ok", timestamp=datetime.now(timezone.utc))

    # EVENT: credits.health_checked (optional - Sprint 5)
    await _emit_event_safe("credits.health_checked", {
        "status": result.status,
        "checked_at": result.timestamp.timestamp(),
    })

    return result


async def get_info() -> CreditsInfo:
    """Get Credits module information.

    Returns:
        CreditsInfo: Module information object
    """
    return CreditsInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config={},
    )
