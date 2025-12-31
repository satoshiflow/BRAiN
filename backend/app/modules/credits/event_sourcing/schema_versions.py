"""
Event Schema Version Registry - Track Schema Evolution.

Manages event schema versions and upcasting transformations:
- Version registry for all event types
- Upcaster functions for transforming old schemas to new
- Automatic schema evolution during replay
- Backward compatibility support

Design Principles:
- Events are immutable (never modify old events)
- Upcasters are pure functions (deterministic transformations)
- Always upcast to latest schema during replay
- Schema versions are per-event-type (different types evolve independently)

Example Evolution:
    Version 1 (original):
        {
            "entity_id": "agent_123",
            "amount": 100.0,
            "reason": "Initial allocation"
        }

    Version 2 (added metadata):
        {
            "entity_id": "agent_123",
            "amount": 100.0,
            "reason": "Initial allocation",
            "metadata": {
                "source": "system",
                "timestamp": "2025-12-30T15:30:00Z"
            }
        }

    Upcaster v1→v2:
        def upcast_credit_allocated_v1_to_v2(payload):
            return {
                **payload,
                "metadata": {
                    "source": "system",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }

Usage:
    # Get current schema version for event type
    current_version = SCHEMA_REGISTRY.get_latest_version("credit.allocated")

    # Upcast event to latest schema
    upcasted_payload = upcast_event(event)

    # Register new schema version
    SCHEMA_REGISTRY.register_version(
        event_type="credit.allocated",
        version=3,
        upcaster=upcast_v2_to_v3
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from backend.app.modules.credits.event_sourcing.events import EventType

# Type alias for upcaster functions
Upcaster = Callable[[Dict[str, Any]], Dict[str, Any]]


class SchemaVersion:
    """
    Schema version metadata.

    Tracks version number, upcaster function, and migration notes.
    """

    def __init__(
        self,
        event_type: str,
        version: int,
        upcaster: Optional[Upcaster] = None,
        description: str = "",
    ):
        """
        Initialize schema version.

        Args:
            event_type: Event type this version applies to
            version: Schema version number
            upcaster: Function to upcast from previous version (None for v1)
            description: Human-readable description of changes
        """
        self.event_type = event_type
        self.version = version
        self.upcaster = upcaster
        self.description = description

    def __repr__(self) -> str:
        return (
            f"SchemaVersion("
            f"event_type={self.event_type}, "
            f"version={self.version}, "
            f"has_upcaster={self.upcaster is not None})"
        )


class SchemaRegistry:
    """
    Registry of all event schema versions.

    Features:
    - Track latest version per event type
    - Store upcaster functions for each version
    - Query schema evolution history
    - Validate schema versions
    """

    def __init__(self):
        """Initialize empty schema registry."""
        # Format: {event_type: {version: SchemaVersion}}
        self._schemas: Dict[str, Dict[int, SchemaVersion]] = {}

    def register_version(
        self,
        event_type: str,
        version: int,
        upcaster: Optional[Upcaster] = None,
        description: str = "",
    ):
        """
        Register a new schema version.

        Args:
            event_type: Event type (e.g., "credit.allocated")
            version: Schema version number
            upcaster: Function to upcast from previous version
            description: Description of changes in this version

        Raises:
            ValueError: If version already registered or skips versions
        """
        if event_type not in self._schemas:
            self._schemas[event_type] = {}

        if version in self._schemas[event_type]:
            raise ValueError(
                f"Schema version {version} already registered for {event_type}"
            )

        # Validate sequential versioning
        existing_versions = sorted(self._schemas[event_type].keys())
        if existing_versions and version != max(existing_versions) + 1:
            raise ValueError(
                f"Schema versions must be sequential. "
                f"Expected version {max(existing_versions) + 1}, got {version}"
            )

        # Version 1 should not have an upcaster
        if version == 1 and upcaster is not None:
            raise ValueError("Schema version 1 should not have an upcaster")

        # Versions > 1 should have an upcaster
        if version > 1 and upcaster is None:
            raise ValueError(f"Schema version {version} must have an upcaster")

        schema_version = SchemaVersion(
            event_type=event_type,
            version=version,
            upcaster=upcaster,
            description=description,
        )

        self._schemas[event_type][version] = schema_version

    def get_latest_version(self, event_type: str) -> int:
        """
        Get latest schema version for event type.

        Args:
            event_type: Event type (e.g., "credit.allocated")

        Returns:
            Latest version number (1 if not registered)
        """
        if event_type not in self._schemas or not self._schemas[event_type]:
            return 1  # Default to version 1

        return max(self._schemas[event_type].keys())

    def get_schema(self, event_type: str, version: int) -> Optional[SchemaVersion]:
        """
        Get schema version metadata.

        Args:
            event_type: Event type
            version: Schema version number

        Returns:
            SchemaVersion if found, None otherwise
        """
        return self._schemas.get(event_type, {}).get(version)

    def get_upcaster(self, event_type: str, from_version: int) -> Optional[Upcaster]:
        """
        Get upcaster function for transforming from one version to next.

        Args:
            event_type: Event type
            from_version: Source version to upcast from

        Returns:
            Upcaster function if exists, None otherwise
        """
        to_version = from_version + 1
        schema = self.get_schema(event_type, to_version)
        return schema.upcaster if schema else None

    def get_evolution_path(self, event_type: str, from_version: int) -> list[int]:
        """
        Get version evolution path from old version to latest.

        Args:
            event_type: Event type
            from_version: Starting version

        Returns:
            List of versions to upcast through (e.g., [2, 3, 4])
        """
        latest_version = self.get_latest_version(event_type)

        if from_version >= latest_version:
            return []  # Already at latest

        return list(range(from_version + 1, latest_version + 1))

    def get_all_event_types(self) -> list[str]:
        """Get all registered event types."""
        return list(self._schemas.keys())

    def get_version_history(self, event_type: str) -> list[SchemaVersion]:
        """
        Get all schema versions for event type.

        Args:
            event_type: Event type

        Returns:
            List of SchemaVersion objects, sorted by version
        """
        if event_type not in self._schemas:
            return []

        versions = self._schemas[event_type]
        return [versions[v] for v in sorted(versions.keys())]


# === Global Schema Registry ===

SCHEMA_REGISTRY = SchemaRegistry()


# === Example Upcasters ===
# These are examples showing how to write upcasters for future schema changes.
# Uncomment and modify when you need to evolve event schemas.


def upcast_credit_allocated_v1_to_v2(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example upcaster: Add metadata field to credit.allocated events.

    This is a TEMPLATE - not currently active.
    Uncomment and register when you need to add metadata to events.

    Changes in v2:
    - Added "metadata" field with source and timestamp
    - Preserves all v1 fields
    """
    return {
        **payload,
        "metadata": {
            "source": "system",
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def upcast_credit_consumed_v1_to_v2(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Example upcaster: Add cost_breakdown field to credit.consumed events.

    This is a TEMPLATE - not currently active.

    Changes in v2:
    - Added "cost_breakdown" field for detailed cost tracking
    - Preserves all v1 fields
    """
    return {
        **payload,
        "cost_breakdown": {
            "base_cost": payload["amount"],
            "multiplier": 1.0,
            "total": payload["amount"],
        },
    }


# === Register Current Schema Versions ===

def initialize_schema_registry():
    """
    Initialize schema registry with current event schemas.

    This should be called once at application startup.
    All events are currently at version 1 (no upcasters registered).

    To evolve a schema:
    1. Write an upcaster function (see examples above)
    2. Register new version with SCHEMA_REGISTRY.register_version()
    3. Update event creation helpers to use new schema
    4. Run migration script to upcast existing events
    """
    # Register version 1 for all event types (no upcasters)
    for event_type in EventType:
        SCHEMA_REGISTRY.register_version(
            event_type=event_type.value,
            version=1,
            upcaster=None,
            description="Initial schema version",
        )

    # Example: Registering version 2 (commented out - template for future use)
    # SCHEMA_REGISTRY.register_version(
    #     event_type=EventType.CREDIT_ALLOCATED.value,
    #     version=2,
    #     upcaster=upcast_credit_allocated_v1_to_v2,
    #     description="Added metadata field for enhanced tracking"
    # )


# === Helper Functions ===


def get_current_schema_version(event_type: str) -> int:
    """
    Get current schema version for event type.

    Args:
        event_type: Event type (e.g., "credit.allocated")

    Returns:
        Current version number
    """
    return SCHEMA_REGISTRY.get_latest_version(event_type)


def is_schema_current(event_type: str, version: int) -> bool:
    """
    Check if event schema is current (latest version).

    Args:
        event_type: Event type
        version: Schema version to check

    Returns:
        True if version is latest, False otherwise
    """
    latest_version = SCHEMA_REGISTRY.get_latest_version(event_type)
    return version >= latest_version


# Initialize registry on module import
initialize_schema_registry()
