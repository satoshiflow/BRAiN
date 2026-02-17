"""
PayPal Payment Provider (STUB)

Placeholder implementation for PayPal integration.
TODO: Implement with PayPal REST API SDK.
"""

from typing import Dict, Any, Optional
from loguru import logger

from .base import PaymentProvider
from ..schemas import ProviderIntent, ProviderRefund, IntentStatus, RefundStatus
from ..exceptions import PayPalProviderException


class PayPalProvider(PaymentProvider):
    """
    PayPal payment provider stub.

    TODO: Implement with PayPal REST API:
    - https://developer.paypal.com/docs/api/orders/v2/
    - pip install paypalrestsdk or use requests directly
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PayPal provider.

        Args:
            config: Must contain:
                - client_id: PayPal client ID
                - client_secret: PayPal client secret
                - mode: 'sandbox' or 'live'
        """
        super().__init__(config)
        logger.warning("PayPalProvider is a stub - not yet implemented")

        self.client_id = config.get("client_id")
        self.client_secret = config.get("client_secret")
        self.mode = config.get("mode", "sandbox")

    async def create_intent(
        self,
        amount_cents: int,
        currency: str,
        metadata: Dict[str, Any]
    ) -> ProviderIntent:
        """
        TODO: Create PayPal Order.

        Reference:
        https://developer.paypal.com/docs/api/orders/v2/#orders_create
        """
        logger.warning("PayPal create_intent not implemented - returning stub")

        return ProviderIntent(
            provider_intent_id=f"PAYPAL_STUB_{amount_cents}",
            status=IntentStatus.CREATED,
            amount_cents=amount_cents,
            currency=currency,
            checkout_url="https://www.sandbox.paypal.com/checkoutnow?token=STUB",
            raw_data={"stub": True},
        )

    async def get_intent(self, provider_intent_id: str) -> ProviderIntent:
        """
        TODO: Retrieve PayPal Order status.

        Reference:
        https://developer.paypal.com/docs/api/orders/v2/#orders_get
        """
        logger.warning("PayPal get_intent not implemented - returning stub")

        return ProviderIntent(
            provider_intent_id=provider_intent_id,
            status=IntentStatus.PENDING,
            amount_cents=0,
            currency="EUR",
            raw_data={"stub": True},
        )

    async def create_refund(
        self,
        provider_intent_id: str,
        amount_cents: int,
        reason: Optional[str] = None
    ) -> ProviderRefund:
        """
        TODO: Create PayPal Refund.

        Reference:
        https://developer.paypal.com/docs/api/payments/v2/#captures_refund
        """
        logger.warning("PayPal create_refund not implemented - returning stub")

        return ProviderRefund(
            provider_refund_id=f"REFUND_STUB_{amount_cents}",
            status=RefundStatus.PROCESSING,
            amount_cents=amount_cents,
            raw_data={"stub": True},
        )

    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        TODO: Verify PayPal webhook signature.

        Reference:
        https://developer.paypal.com/docs/api/webhooks/v1/#verify-webhook-signature
        """
        logger.warning("PayPal verify_webhook not implemented - returning stub")
        import json
        return json.loads(payload)

    def normalize_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        TODO: Normalize PayPal webhook event.

        PayPal event types:
        - CHECKOUT.ORDER.APPROVED
        - PAYMENT.CAPTURE.COMPLETED
        - PAYMENT.CAPTURE.REFUNDED
        """
        logger.warning("PayPal normalize_webhook_event not implemented")

        return {
            "event_id": event.get("id", "STUB"),
            "event_type": "payment_succeeded",
            "provider_intent_id": "STUB",
            "raw_data": event,
        }
