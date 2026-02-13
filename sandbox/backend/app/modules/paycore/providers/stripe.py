"""
Stripe Payment Provider

Production-ready Stripe integration with:
- Checkout Sessions for hosted flows
- Payment Intents for custom flows
- Webhook signature verification
- Refund support
"""

from typing import Dict, Any, Optional
from loguru import logger

try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    logger.warning("stripe-python not installed. Install with: pip install stripe")

from .base import PaymentProvider
from ..schemas import ProviderIntent, ProviderRefund, IntentStatus, RefundStatus
from ..exceptions import StripeProviderException, WebhookVerificationException


class StripeProvider(PaymentProvider):
    """
    Stripe payment provider implementation.

    Uses Stripe Checkout Sessions for hosted checkout flow.
    Supports webhook signature verification for security.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Stripe provider.

        Args:
            config: Must contain:
                - secret_key: Stripe secret key (sk_test_... or sk_live_...)
                - webhook_secret: Webhook signing secret (whsec_...)
                - success_url: URL to redirect after successful payment (optional)
                - cancel_url: URL to redirect after cancelled payment (optional)
        """
        super().__init__(config)

        if not STRIPE_AVAILABLE:
            raise StripeProviderException(
                "stripe-python not installed. Install with: pip install stripe"
            )

        # Set Stripe API key
        stripe.api_key = config.get("secret_key")
        if not stripe.api_key:
            raise StripeProviderException("Stripe secret_key not configured")

        self.webhook_secret = config.get("webhook_secret")
        if not self.webhook_secret:
            logger.warning("Stripe webhook_secret not configured - webhook verification disabled")

        self.success_url = config.get("success_url", "https://example.com/success")
        self.cancel_url = config.get("cancel_url", "https://example.com/cancel")

    async def create_intent(
        self,
        amount_cents: int,
        currency: str,
        metadata: Dict[str, Any]
    ) -> ProviderIntent:
        """
        Create Stripe Checkout Session.

        Uses hosted checkout flow for simplicity and PCI compliance.

        Args:
            amount_cents: Amount in cents
            currency: ISO currency code (lowercase for Stripe)
            metadata: Custom metadata

        Returns:
            ProviderIntent with checkout URL
        """
        try:
            # Create Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        "price_data": {
                            "currency": currency.lower(),
                            "product_data": {
                                "name": metadata.get("product_name", "BRAiN Course"),
                                "description": metadata.get("description", ""),
                            },
                            "unit_amount": amount_cents,
                        },
                        "quantity": 1,
                    }
                ],
                mode="payment",
                success_url=self.success_url,
                cancel_url=self.cancel_url,
                metadata=metadata,
            )

            logger.info(f"Created Stripe Checkout Session: {session.id}")

            return ProviderIntent(
                provider_intent_id=session.id,
                status=IntentStatus.CREATED,
                amount_cents=amount_cents,
                currency=currency,
                checkout_url=session.url,
                client_secret=None,  # Not needed for Checkout Sessions
                raw_data={"session": session.to_dict()},
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {e}")
            raise StripeProviderException(f"Stripe API error: {str(e)}")

    async def get_intent(self, provider_intent_id: str) -> ProviderIntent:
        """
        Retrieve Stripe Checkout Session status.

        Args:
            provider_intent_id: Stripe session ID (cs_...)

        Returns:
            ProviderIntent with current status
        """
        try:
            session = stripe.checkout.Session.retrieve(provider_intent_id)

            # Map Stripe payment_status to IntentStatus
            status_mapping = {
                "paid": IntentStatus.SUCCEEDED,
                "unpaid": IntentStatus.PENDING,
                "no_payment_required": IntentStatus.SUCCEEDED,
            }
            status = status_mapping.get(session.payment_status, IntentStatus.PENDING)

            return ProviderIntent(
                provider_intent_id=session.id,
                status=status,
                amount_cents=session.amount_total or 0,
                currency=(session.currency or "eur").upper(),
                checkout_url=session.url,
                raw_data={"session": session.to_dict()},
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe API error: {e}")
            raise StripeProviderException(f"Stripe API error: {str(e)}")

    async def create_refund(
        self,
        provider_intent_id: str,
        amount_cents: int,
        reason: Optional[str] = None
    ) -> ProviderRefund:
        """
        Create Stripe refund.

        Args:
            provider_intent_id: Stripe session ID
            amount_cents: Refund amount in cents
            reason: Optional refund reason

        Returns:
            ProviderRefund with refund ID
        """
        try:
            # First, get the PaymentIntent from the Checkout Session
            session = stripe.checkout.Session.retrieve(provider_intent_id)
            payment_intent_id = session.payment_intent

            if not payment_intent_id:
                raise StripeProviderException(
                    f"No PaymentIntent found for session {provider_intent_id}"
                )

            # Create refund
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount_cents,
                reason=reason or "requested_by_customer",
            )

            logger.info(f"Created Stripe Refund: {refund.id}")

            # Map Stripe refund status
            status_mapping = {
                "pending": RefundStatus.PROCESSING,
                "succeeded": RefundStatus.SUCCEEDED,
                "failed": RefundStatus.FAILED,
                "canceled": RefundStatus.FAILED,
            }
            status = status_mapping.get(refund.status, RefundStatus.PROCESSING)

            return ProviderRefund(
                provider_refund_id=refund.id,
                status=status,
                amount_cents=refund.amount,
                raw_data={"refund": refund.to_dict()},
            )

        except stripe.error.StripeError as e:
            logger.error(f"Stripe refund error: {e}")
            raise StripeProviderException(f"Stripe refund error: {str(e)}")

    def verify_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Verify Stripe webhook signature.

        Args:
            payload: Raw webhook payload (bytes)
            signature: Stripe-Signature header value

        Returns:
            Parsed event dict

        Raises:
            WebhookVerificationException: If signature invalid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured - skipping verification")
            import json
            return json.loads(payload)

        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            logger.info(f"Verified Stripe webhook: {event['type']}")
            return event

        except ValueError as e:
            raise WebhookVerificationException(f"Invalid payload: {e}")
        except stripe.error.SignatureVerificationError as e:
            raise WebhookVerificationException(f"Invalid signature: {e}")

    def normalize_webhook_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Stripe webhook event to common format.

        Stripe events we care about:
        - checkout.session.completed (payment succeeded)
        - checkout.session.expired (payment failed/cancelled)
        - charge.refunded (refund succeeded)

        Args:
            event: Raw Stripe event

        Returns:
            Normalized event dict
        """
        event_type = event.get("type", "")
        event_id = event.get("id", "")
        data = event.get("data", {}).get("object", {})

        # Map Stripe event types to our event types
        if event_type == "checkout.session.completed":
            return {
                "event_id": event_id,
                "event_type": "payment_succeeded",
                "provider_intent_id": data.get("id"),
                "amount_cents": data.get("amount_total"),
                "currency": (data.get("currency") or "eur").upper(),
                "status": "succeeded",
                "raw_data": event,
            }

        elif event_type == "checkout.session.expired":
            return {
                "event_id": event_id,
                "event_type": "payment_failed",
                "provider_intent_id": data.get("id"),
                "status": "failed",
                "raw_data": event,
            }

        elif event_type == "charge.refunded":
            return {
                "event_id": event_id,
                "event_type": "refund_succeeded",
                "provider_intent_id": data.get("payment_intent"),
                "amount_cents": data.get("amount_refunded"),
                "status": "refunded",
                "raw_data": event,
            }

        else:
            # Unknown event type - return as-is for logging
            return {
                "event_id": event_id,
                "event_type": event_type,
                "raw_data": event,
            }
