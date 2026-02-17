"""Base notification channel interface."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from loguru import logger


class BaseNotificationChannel(ABC):
    """Abstract base class for notification channels."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize notification channel.

        Args:
            config: Channel-specific configuration
        """
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

    @abstractmethod
    async def send(
        self, recipient: str, subject: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send notification through this channel.

        Args:
            recipient: Recipient identifier (email, webhook URL, etc.)
            subject: Notification subject/title
            message: Notification message body
            metadata: Additional metadata

        Returns:
            True if sent successfully, False otherwise
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate channel configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        pass

    async def send_with_retry(
        self,
        recipient: str,
        subject: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> bool:
        """Send notification with retry logic.

        Args:
            recipient: Recipient identifier
            subject: Notification subject
            message: Notification message
            metadata: Additional metadata
            max_retries: Maximum number of retry attempts

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.enabled:
            logger.warning(f"{self.__class__.__name__} is disabled")
            return False

        if not self.validate_config():
            logger.error(f"{self.__class__.__name__} configuration is invalid")
            return False

        for attempt in range(max_retries):
            try:
                success = await self.send(recipient, subject, message, metadata)
                if success:
                    logger.info(
                        f"{self.__class__.__name__} sent notification to {recipient}"
                    )
                    return True
                else:
                    logger.warning(
                        f"{self.__class__.__name__} failed to send (attempt {attempt + 1}/{max_retries})"
                    )
            except Exception as e:
                logger.error(
                    f"{self.__class__.__name__} error on attempt {attempt + 1}/{max_retries}: {e}"
                )

            # Don't retry on last attempt
            if attempt < max_retries - 1:
                # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(2**attempt)

        logger.error(
            f"{self.__class__.__name__} failed to send after {max_retries} attempts"
        )
        return False


import asyncio  # Import at end to avoid circular dependency
