"""
Event Upcaster - Transform Old Event Schemas to Latest Version.

Automatically upcasts events during replay to ensure compatibility:
- Detects old schema versions
- Applies sequential upcasters to reach latest version
- Maintains event immutability (creates new events, doesn't modify old)
- Integrates with replay engine for transparent operation

Design:
- Pure functions (deterministic transformations)
- Sequential upcasting (v1 → v2 → v3, not v1 → v3 directly)
- Error resilience (logs failures, continues replay)
- Backward compatibility (v1 events work forever)

Integration with Replay Engine:
    # Before applying event to projection
    event = await upcast_event_if_needed(event)
    await projection.handle_event(event)

Performance:
- Only upcasts when needed (checks schema_version first)
- Caches upcasters in memory
- O(1) lookup for latest version
- Minimal overhead for current-version events

Examples:
    # Upcast single event
    event_v1 = EventEnvelope(schema_version=1, ...)
    event_v3 = await upcast_event_if_needed(event_v1)  # Applies v1→v2→v3

    # Check if upcast needed
    needs_upcast = is_upcast_needed(event)

    # Get evolution path
    path = get_evolution_path("credit.allocated", from_version=1)
    # Returns: [2, 3] (need to upcast through v2 then v3)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from loguru import logger

from app.modules.credits.event_sourcing.events import EventEnvelope
from app.modules.credits.event_sourcing.schema_versions import SCHEMA_REGISTRY


class UpcastError(Exception):
    """Raised when event upcasting fails."""

    pass


async def upcast_event_if_needed(event: EventEnvelope) -> EventEnvelope:
    """
    Upcast event to latest schema version if needed.

    This is the main entry point for automatic schema evolution.
    Called during replay before applying event to projections.

    Args:
        event: Event envelope to upcast

    Returns:
        Upcasted event (or original if already current)

    Raises:
        UpcastError: If upcasting fails (critical - stops replay)

    Examples:
        >>> event_v1 = EventEnvelope(schema_version=1, event_type="credit.allocated", ...)
        >>> event_v3 = await upcast_event_if_needed(event_v1)
        >>> assert event_v3.schema_version == 3
    """
    event_type = event.event_type.value
    current_version = event.schema_version
    latest_version = SCHEMA_REGISTRY.get_latest_version(event_type)

    # Already at latest version - no upcast needed
    if current_version >= latest_version:
        return event

    logger.debug(
        f"Upcasting event {event.event_id} "
        f"from v{current_version} to v{latest_version}",
        event_type=event_type,
    )

    try:
        # Get evolution path (e.g., [2, 3, 4])
        evolution_path = SCHEMA_REGISTRY.get_evolution_path(event_type, current_version)

        # Apply sequential upcasters
        upcasted_payload = event.payload
        for target_version in evolution_path:
            upcaster = SCHEMA_REGISTRY.get_upcaster(event_type, target_version - 1)

            if upcaster is None:
                raise UpcastError(
                    f"Missing upcaster for {event_type} "
                    f"v{target_version - 1} → v{target_version}"
                )

            # Apply upcaster
            logger.debug(
                f"Applying upcaster v{target_version - 1} → v{target_version}",
                event_type=event_type,
                event_id=event.event_id,
            )
            upcasted_payload = upcaster(upcasted_payload)

        # Create new event with upcasted payload and latest version
        upcasted_event = event.model_copy(
            update={
                "payload": upcasted_payload,
                "schema_version": latest_version,
            }
        )

        logger.info(
            f"Upcasted event {event.event_id} "
            f"from v{current_version} to v{latest_version}",
            event_type=event_type,
        )

        return upcasted_event

    except Exception as e:
        error_msg = (
            f"Failed to upcast event {event.event_id} "
            f"from v{current_version} to v{latest_version}: {e}"
        )
        logger.error(error_msg, event_type=event_type, exc_info=True)
        raise UpcastError(error_msg) from e


def is_upcast_needed(event: EventEnvelope) -> bool:
    """
    Check if event needs upcasting.

    Args:
        event: Event envelope to check

    Returns:
        True if event schema is outdated, False if current
    """
    event_type = event.event_type.value
    current_version = event.schema_version
    latest_version = SCHEMA_REGISTRY.get_latest_version(event_type)

    return current_version < latest_version


def get_evolution_path(event_type: str, from_version: int) -> list[int]:
    """
    Get version evolution path for event type.

    Args:
        event_type: Event type (e.g., "credit.allocated")
        from_version: Starting version

    Returns:
        List of versions to upcast through (e.g., [2, 3, 4])

    Examples:
        >>> get_evolution_path("credit.allocated", from_version=1)
        [2, 3, 4]  # If latest is v4
    """
    return SCHEMA_REGISTRY.get_evolution_path(event_type, from_version)


async def upcast_event_batch(events: list[EventEnvelope]) -> list[EventEnvelope]:
    """
    Upcast a batch of events.

    Args:
        events: List of events to upcast

    Returns:
        List of upcasted events (in same order)

    Raises:
        UpcastError: If any event fails to upcast
    """
    upcasted_events = []

    for event in events:
        upcasted_event = await upcast_event_if_needed(event)
        upcasted_events.append(upcasted_event)

    return upcasted_events


def get_upcast_statistics(events: list[EventEnvelope]) -> Dict[str, Any]:
    """
    Get statistics about events that need upcasting.

    Args:
        events: List of events to analyze

    Returns:
        Dict with statistics:
        - total_events: Total number of events
        - needs_upcast: Number of events needing upcast
        - by_event_type: Breakdown by event type
        - by_version: Breakdown by schema version

    Examples:
        >>> stats = get_upcast_statistics(all_events)
        >>> print(f"{stats['needs_upcast']} / {stats['total_events']} need upcast")
    """
    total_events = len(events)
    needs_upcast_count = 0
    by_event_type: Dict[str, int] = {}
    by_version: Dict[int, int] = {}

    for event in events:
        if is_upcast_needed(event):
            needs_upcast_count += 1

            # Count by event type
            event_type = event.event_type.value
            by_event_type[event_type] = by_event_type.get(event_type, 0) + 1

            # Count by version
            version = event.schema_version
            by_version[version] = by_version.get(version, 0) + 1

    return {
        "total_events": total_events,
        "needs_upcast": needs_upcast_count,
        "upcast_percentage": (
            (needs_upcast_count / total_events * 100) if total_events > 0 else 0
        ),
        "by_event_type": by_event_type,
        "by_version": by_version,
    }


async def validate_upcaster(
    event_type: str,
    from_version: int,
    sample_payload: Dict[str, Any],
) -> bool:
    """
    Validate an upcaster function.

    Tests that upcaster:
    - Doesn't raise exceptions
    - Returns a dict
    - Preserves required fields

    Args:
        event_type: Event type
        from_version: Source version
        sample_payload: Sample v{from_version} payload to test

    Returns:
        True if upcaster is valid, False otherwise

    Examples:
        >>> sample = {"entity_id": "agent_123", "amount": 100.0}
        >>> is_valid = await validate_upcaster("credit.allocated", 1, sample)
    """
    try:
        upcaster = SCHEMA_REGISTRY.get_upcaster(event_type, from_version)

        if upcaster is None:
            logger.warning(
                f"No upcaster found for {event_type} v{from_version} → v{from_version + 1}"
            )
            return False

        # Apply upcaster
        result = upcaster(sample_payload)

        # Validate result
        if not isinstance(result, dict):
            logger.error(
                f"Upcaster returned non-dict: {type(result)}",
                event_type=event_type,
                from_version=from_version,
            )
            return False

        # Check that original fields are preserved
        for key in sample_payload:
            if key not in result:
                logger.error(
                    f"Upcaster lost required field: {key}",
                    event_type=event_type,
                    from_version=from_version,
                )
                return False

        logger.info(
            f"Upcaster validation passed",
            event_type=event_type,
            from_version=from_version,
            to_version=from_version + 1,
        )
        return True

    except Exception as e:
        logger.error(
            f"Upcaster validation failed: {e}",
            event_type=event_type,
            from_version=from_version,
            exc_info=True,
        )
        return False


# === Integration Example ===

"""
To integrate with replay engine, modify replay.py:

# Before:
await self.projection_manager.balance.handle_event(event)

# After:
from app.modules.credits.event_sourcing.event_upcaster import upcast_event_if_needed

upcasted_event = await upcast_event_if_needed(event)
await self.projection_manager.balance.handle_event(upcasted_event)

This ensures all events are automatically upcasted to latest schema before
being applied to projections.
"""
