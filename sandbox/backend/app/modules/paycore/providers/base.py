"""
PayCore Base Payment Provider

Abstract interface for payment gateway adapters.
All providers must implement this interface for consistency.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..schemas import ProviderIntent, ProviderRefund


class PaymentProvider(ABC):
    """
    Abstract base class for payment providers.

    All payment gateway adapters must inherit from this class
    and implement the required methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration.

        Args:
            config: Provider-specific configuration (API keys, etc.)
        """
        self.config = config

    @abstractmethod
    async def create_intent(
        self,
        amount_cents: int,
        currency: str,
        metadata: Dict[str, Any]
    ) -> ProviderIntent:
        """
        Create a payment intent/session.

        Args:
            amount_cents: Payment amount in cents (e.g., 5000 = 50.00)
            currency: ISO currency code (e.g., "EUR", "USD")
            metadata: Custom metadata to attach to the intent

        Returns:
            ProviderIntent with provider_intent_id and checkout_url

        Raises:
            ProviderException: If provider API call fails
        """
        pass

    @abstractmethod
    async def get_intent(self, provider_intent_id: str) -> ProviderIntent:
        """
        Retrieve intent status from provider.

        Args:
            provider_intent_id: Provider-specific intent ID

        Returns:
            ProviderIntent with current status

        Raises:
            ProviderException: If provider API call fails
        """
        pass

    @abstractmethod
    async def create_refund(
        self,
        provider_intent_id: str,
        amount_cents: int,
        reason: Optional[str] = None
    ) -> ProviderRefund:
        """
        Create a refund for a payment.

        Args:
            provider_intent_id: Provider-specific intent ID
            amount_cents: Refund amount in cents
            reason: Optional reason for refund

        Returns:
            ProviderRefund with provider_refund_id and status

        Raises:
            ProviderException: If provider API call fails
        """
        pass

    @abstractmethod
    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Verify webhook signature and parse event.

        Args:
            payload: Raw webhook payload (bytes)
            signature: Webhook signature from headers

        Returns:
            Parsed event data

        Raises:
            WebhookVerificationException: If signature verification fails
        """
        pass

    @abstractmethod
    def normalize_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize provider webhook event to common format.

        Args:
            event: Raw provider event

        Returns:
            Normalized event with:
                - event_id: str
                - event_type: str (payment_succeeded, payment_failed, etc.)
                - provider_intent_id: str
                - amount_cents: int (optional, depends on event)
                - status: str (optional)

        """
        pass
