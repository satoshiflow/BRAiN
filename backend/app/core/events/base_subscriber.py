"""
Base Event Subscriber

Abstract base class for all event subscribers in the BRAiN system.
Provides lifecycle management and error handling patterns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from loguru import logger


class EventSubscriber(ABC):
    """
    Abstract base class for event subscribers.

    Subclasses must implement:
    - event_types: List of event types to subscribe to
    - handle(): Event processing logic
    """

    @property
    @abstractmethod
    def subscriber_name(self) -> str:
        """Unique subscriber identifier"""
        pass

    @property
    @abstractmethod
    def event_types(self) -> List[str]:
        """Event types this subscriber handles"""
        pass

    @abstractmethod
    async def handle(self, event: Dict[str, Any]) -> None:
        """
        Handle event.

        Args:
            event: Event payload (includes event_type, trace_id, etc.)

        Raises:
            ValueError: For permanent errors (malformed data, validation)
            Exception: For transient errors (DB connection, timeout)
        """
        pass

    async def on_error(self, event: Dict[str, Any], error: Exception) -> bool:
        """
        Error handler hook.

        Args:
            event: Event that caused error
            error: Exception raised

        Returns:
            bool: True if error is transient (retry), False if permanent (skip)
        """
        # Default: classify errors
        if isinstance(error, (ValueError, KeyError, TypeError)):
            # Permanent: validation/data errors
            logger.error(
                f"[{self.subscriber_name}] Permanent error: {error}",
                event_type=event.get("event_type"),
                trace_id=event.get("trace_id"),
            )
            return False  # Don't retry
        else:
            # Transient: network, DB, timeout
            logger.warning(
                f"[{self.subscriber_name}] Transient error: {error}",
                event_type=event.get("event_type"),
                trace_id=event.get("trace_id"),
            )
            return True  # Retry

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} subscriber={self.subscriber_name} events={self.event_types}>"
