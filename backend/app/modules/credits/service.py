from datetime import datetime, timezone
from typing import Optional, Dict, List
import time
import logging

from .schemas import CreditsHealth, CreditsInfo

logger = logging.getLogger(__name__)

MODULE_NAME = "brain.credits"
MODULE_VERSION = "2.0.0"  # Updated for Event Sourcing

# Optional EventStream import (Sprint 5: EventStream Integration)
try:
    from backend.app.core.event_stream import EventStream, Event
except ImportError:
    EventStream = None
    Event = None

# Event Sourcing imports
try:
    from backend.app.modules.credits.integration_demo import (
        CreditSystemDemo,
        get_credit_system_demo,
    )
    EVENTSOURCING_AVAILABLE = True
except ImportError:
    logger.warning("Event Sourcing not available (integration_demo.py missing)")
    CreditSystemDemo = None
    get_credit_system_demo = None
    EVENTSOURCING_AVAILABLE = False

# Module-level EventStream (Sprint 5: EventStream Integration)
_event_stream: Optional["EventStream"] = None

# Module-level CreditSystemDemo (Event Sourcing)
_credit_system: Optional["CreditSystemDemo"] = None


def set_event_stream(stream: "EventStream") -> None:
    """Initialize EventStream for Credits module (Sprint 5)."""
    global _event_stream
    _event_stream = stream


async def initialize_event_sourcing() -> None:
    """
    Initialize Event Sourcing system.

    Called on app startup to:
    1. Initialize CreditSystemDemo
    2. Replay existing events (crash recovery)
    3. Subscribe projections to EventBus

    Note:
        - Safe to call multiple times (idempotent)
        - Gracefully handles missing Event Sourcing
    """
    global _credit_system

    if not EVENTSOURCING_AVAILABLE:
        logger.debug("Event Sourcing not available, skipping initialization")
        return

    if _credit_system is not None:
        logger.debug("Event Sourcing already initialized")
        return

    try:
        _credit_system = await get_credit_system_demo()
        logger.info("Event Sourcing initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Event Sourcing: {e}", exc_info=True)


async def get_credit_system() -> Optional["CreditSystemDemo"]:
    """
    Get CreditSystemDemo instance.

    Returns:
        CreditSystemDemo or None if not available/initialized
    """
    if not EVENTSOURCING_AVAILABLE:
        return None

    if _credit_system is None:
        await initialize_event_sourcing()

    return _credit_system


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
    config = {
        "event_sourcing_enabled": EVENTSOURCING_AVAILABLE,
    }

    if EVENTSOURCING_AVAILABLE and _credit_system is not None:
        try:
            metrics = await _credit_system.get_metrics()
            config["event_sourcing_metrics"] = metrics
        except Exception as e:
            logger.error(f"Failed to get Event Sourcing metrics: {e}")

    return CreditsInfo(
        name=MODULE_NAME,
        version=MODULE_VERSION,
        config=config,
    )


# ============================================================================
# Event Sourcing Operations
# ============================================================================


async def create_agent_with_credits(
    agent_id: str,
    skill_level: float,
    actor_id: str = "system",
) -> Dict:
    """
    Create agent and allocate initial credits (Event Sourcing).

    Args:
        agent_id: Unique agent identifier
        skill_level: Skill level (0.0 - 1.0)
        actor_id: Who created the agent

    Returns:
        Dict with agent_id, initial_credits, balance

    Raises:
        ValueError: If Event Sourcing not available
    """
    credit_system = await get_credit_system()
    if credit_system is None:
        raise ValueError("Event Sourcing not available")

    initial_credits = await credit_system.create_agent(
        agent_id=agent_id,
        skill_level=skill_level,
        actor_id=actor_id,
    )

    return {
        "agent_id": agent_id,
        "initial_credits": initial_credits,
        "balance": initial_credits,
        "skill_level": skill_level,
    }


async def consume_agent_credits(
    agent_id: str,
    amount: float,
    reason: str,
    mission_id: Optional[str] = None,
    actor_id: str = "system",
) -> Dict:
    """
    Consume credits for agent (Event Sourcing).

    Args:
        agent_id: Agent consuming credits
        amount: Credits to consume
        reason: Why credits are consumed
        mission_id: Related mission (optional)
        actor_id: Who initiated consumption

    Returns:
        Dict with agent_id, amount, balance_after

    Raises:
        ValueError: If Event Sourcing not available or insufficient credits
    """
    credit_system = await get_credit_system()
    if credit_system is None:
        raise ValueError("Event Sourcing not available")

    balance_after = await credit_system.consume_credits(
        agent_id=agent_id,
        amount=amount,
        reason=reason,
        mission_id=mission_id,
        actor_id=actor_id,
    )

    return {
        "agent_id": agent_id,
        "amount": amount,
        "balance_after": balance_after,
        "reason": reason,
        "mission_id": mission_id,
    }


async def refund_agent_credits(
    agent_id: str,
    amount: float,
    reason: str,
    mission_id: Optional[str] = None,
    actor_id: str = "system",
) -> Dict:
    """
    Refund credits to agent (Event Sourcing).

    Args:
        agent_id: Agent receiving refund
        amount: Credits to refund
        reason: Why credits are refunded
        mission_id: Related mission (optional)
        actor_id: Who initiated refund

    Returns:
        Dict with agent_id, amount, balance_after

    Raises:
        ValueError: If Event Sourcing not available
    """
    credit_system = await get_credit_system()
    if credit_system is None:
        raise ValueError("Event Sourcing not available")

    balance_after = await credit_system.refund_credits(
        agent_id=agent_id,
        amount=amount,
        reason=reason,
        mission_id=mission_id,
        actor_id=actor_id,
    )

    return {
        "agent_id": agent_id,
        "amount": amount,
        "balance_after": balance_after,
        "reason": reason,
        "mission_id": mission_id,
    }


async def get_agent_balance(agent_id: str) -> Dict:
    """
    Get current balance for agent (Event Sourcing).

    Args:
        agent_id: Agent ID

    Returns:
        Dict with agent_id, balance

    Raises:
        ValueError: If Event Sourcing not available
    """
    credit_system = await get_credit_system()
    if credit_system is None:
        raise ValueError("Event Sourcing not available")

    balance = await credit_system.get_balance(agent_id)

    return {
        "agent_id": agent_id,
        "balance": balance,
    }


async def get_all_agent_balances() -> Dict:
    """
    Get all agent balances (Event Sourcing).

    Returns:
        Dict with balances: Dict[agent_id, balance]

    Raises:
        ValueError: If Event Sourcing not available
    """
    credit_system = await get_credit_system()
    if credit_system is None:
        raise ValueError("Event Sourcing not available")

    balances = await credit_system.get_all_balances()

    return {
        "balances": balances,
        "total_agents": len(balances),
    }


async def get_agent_history(
    agent_id: str,
    limit: Optional[int] = 10,
) -> Dict:
    """
    Get transaction history for agent (Event Sourcing).

    Args:
        agent_id: Agent ID
        limit: Max number of entries (most recent first)

    Returns:
        Dict with agent_id, history (list of transactions)

    Raises:
        ValueError: If Event Sourcing not available
    """
    credit_system = await get_credit_system()
    if credit_system is None:
        raise ValueError("Event Sourcing not available")

    history = await credit_system.get_history(agent_id, limit=limit)

    # Convert LedgerEntry to dict
    history_dicts = [
        {
            "event_id": entry.event_id,
            "timestamp": entry.timestamp.isoformat(),
            "entity_id": entry.entity_id,
            "entity_type": entry.entity_type,
            "amount": entry.amount,
            "balance_after": entry.balance_after,
            "reason": entry.reason,
            "mission_id": entry.mission_id,
        }
        for entry in history
    ]

    return {
        "agent_id": agent_id,
        "history": history_dicts,
        "total_entries": len(history_dicts),
    }


async def get_event_sourcing_metrics() -> Dict:
    """
    Get Event Sourcing system metrics.

    Returns:
        Dict with journal, event_bus, replay metrics

    Raises:
        ValueError: If Event Sourcing not available
    """
    credit_system = await get_credit_system()
    if credit_system is None:
        raise ValueError("Event Sourcing not available")

    return await credit_system.get_metrics()
