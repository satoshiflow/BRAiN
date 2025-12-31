"""
PayCore Service Layer

Business logic for payment processing:
- Payment intent creation and management
- Refund processing with policy checks
- Webhook handling with idempotency
- Event publishing
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.redis_client import get_redis
from app.core.event_bus import EventBus
from app.core.security import Principal

from .models import PaymentIntent, Transaction, Refund
from .schemas import (
    IntentCreateRequest,
    IntentCreateResponse,
    IntentStatusResponse,
    RefundCreateRequest,
    RefundCreateResponse,
    RefundStatusResponse,
    PaymentProvider as PaymentProviderEnum,
    IntentStatus,
    RefundStatus,
    TransactionEventType,
    PayCoreInfo,
    PayCoreHealth,
)
from .providers import StripeProvider, PaymentProvider
from .exceptions import (
    IntentNotFoundException,
    RefundNotFoundException,
    RefundDeniedException,
    InvalidAmountException,
    IdempotencyException,
)


# ============================================================================
# Provider Factory
# ============================================================================

def get_payment_provider(provider: PaymentProviderEnum) -> PaymentProvider:
    """
    Factory function to get payment provider instance.

    Args:
        provider: Provider enum value

    Returns:
        PaymentProvider instance

    Raises:
        ValueError: If provider not configured or unknown
    """
    if provider == PaymentProviderEnum.STRIPE:
        config = {
            "secret_key": os.getenv("STRIPE_SECRET_KEY"),
            "webhook_secret": os.getenv("STRIPE_WEBHOOK_SECRET"),
            "success_url": os.getenv("STRIPE_SUCCESS_URL", "https://example.com/success"),
            "cancel_url": os.getenv("STRIPE_CANCEL_URL", "https://example.com/cancel"),
        }

        if not config["secret_key"]:
            raise ValueError("STRIPE_SECRET_KEY not configured in environment")

        return StripeProvider(config)

    elif provider == PaymentProviderEnum.PAYPAL:
        # TODO: Implement PayPal provider
        from .providers.paypal import PayPalProvider

        config = {
            "client_id": os.getenv("PAYPAL_CLIENT_ID"),
            "client_secret": os.getenv("PAYPAL_CLIENT_SECRET"),
            "mode": os.getenv("PAYPAL_MODE", "sandbox"),
        }
        return PayPalProvider(config)

    else:
        raise ValueError(f"Unknown provider: {provider}")


# ============================================================================
# Service Class
# ============================================================================

class PayCoreService:
    """
    PayCore service layer.

    Handles business logic for payment processing.
    """

    def __init__(self):
        self.event_bus: Optional[EventBus] = None

    async def _get_event_bus(self) -> EventBus:
        """Get or create event bus instance."""
        if not self.event_bus:
            redis = await get_redis()
            self.event_bus = EventBus(redis)
        return self.event_bus

    async def _publish_event(self, event: Dict[str, Any]) -> None:
        """Publish event to brain.events.paycore stream."""
        try:
            bus = await self._get_event_bus()
            bus.publish_domain("paycore", event)
            logger.debug(f"Published event: {event.get('event_type')}")
        except Exception as e:
            logger.error(f"Failed to publish event: {e}")

    # ========================================================================
    # Info & Health
    # ========================================================================

    async def get_info(self) -> PayCoreInfo:
        """Get module information."""
        return PayCoreInfo()

    async def get_health(self) -> PayCoreHealth:
        """Health check."""
        providers_health = {}

        # Check Stripe
        try:
            stripe_key = os.getenv("STRIPE_SECRET_KEY")
            providers_health["stripe"] = bool(stripe_key)
        except Exception:
            providers_health["stripe"] = False

        # Check PayPal
        try:
            paypal_id = os.getenv("PAYPAL_CLIENT_ID")
            providers_health["paypal"] = bool(paypal_id)
        except Exception:
            providers_health["paypal"] = False

        return PayCoreHealth(
            timestamp=datetime.now(timezone.utc),
            providers=providers_health
        )

    # ========================================================================
    # Payment Intents
    # ========================================================================

    async def create_intent(
        self,
        request: IntentCreateRequest,
        tenant_id: str,
    ) -> IntentCreateResponse:
        """
        Create payment intent.

        Args:
            request: Intent creation request
            tenant_id: Tenant ID from principal

        Returns:
            IntentCreateResponse with checkout URL

        Raises:
            InvalidAmountException: If amount <= 0
        """
        if request.amount_cents <= 0:
            raise InvalidAmountException("Amount must be greater than 0")

        logger.info(
            f"Creating intent: {request.amount_cents} {request.currency} "
            f"(provider={request.provider.value}, tenant={tenant_id})"
        )

        # Get provider
        provider = get_payment_provider(request.provider)

        # Create intent with provider
        provider_intent = await provider.create_intent(
            amount_cents=request.amount_cents,
            currency=request.currency,
            metadata=request.metadata,
        )

        # Save to database
        async with get_session() as session:
            intent = PaymentIntent(
                id=uuid4(),
                tenant_id=tenant_id,
                user_id=request.user_id,
                provider=request.provider.value,
                provider_intent_id=provider_intent.provider_intent_id,
                amount_cents=request.amount_cents,
                currency=request.currency,
                status=provider_intent.status.value,
                metadata=request.metadata,
            )
            session.add(intent)
            await session.commit()
            await session.refresh(intent)

            logger.info(f"Created intent: {intent.id}")

            # Publish event
            await self._publish_event({
                "event_type": "intent_created",
                "intent_id": str(intent.id),
                "tenant_id": tenant_id,
                "amount_cents": request.amount_cents,
                "currency": request.currency,
                "provider": request.provider.value,
                "metadata": request.metadata,
                "timestamp": datetime.now(timezone.utc).timestamp(),
            })

            return IntentCreateResponse(
                intent_id=intent.id,
                provider=request.provider,
                provider_intent_id=provider_intent.provider_intent_id,
                status=IntentStatus(intent.status),
                amount_cents=intent.amount_cents,
                currency=intent.currency,
                checkout_url=provider_intent.checkout_url,
                client_secret=provider_intent.client_secret,
                created_at=intent.created_at,
            )

    async def get_intent_status(self, intent_id: UUID) -> IntentStatusResponse:
        """
        Get payment intent status.

        Args:
            intent_id: Intent UUID

        Returns:
            IntentStatusResponse with current status

        Raises:
            IntentNotFoundException: If intent not found
        """
        async with get_session() as session:
            result = await session.execute(
                select(PaymentIntent).where(PaymentIntent.id == intent_id)
            )
            intent = result.scalar_one_or_none()

            if not intent:
                raise IntentNotFoundException(f"Intent {intent_id} not found")

            return IntentStatusResponse(
                intent_id=intent.id,
                status=IntentStatus(intent.status),
                amount_cents=intent.amount_cents,
                currency=intent.currency,
                provider=PaymentProviderEnum(intent.provider),
                provider_intent_id=intent.provider_intent_id,
                metadata=intent.metadata or {},
                created_at=intent.created_at,
                updated_at=intent.updated_at,
            )

    # ========================================================================
    # Refunds
    # ========================================================================

    async def create_refund(
        self,
        request: RefundCreateRequest,
        principal: Principal,
    ) -> RefundCreateResponse:
        """
        Create refund request.

        Args:
            request: Refund request
            principal: User principal

        Returns:
            RefundCreateResponse

        Raises:
            IntentNotFoundException: If intent not found
            InvalidAmountException: If amount invalid
            RefundDeniedException: If denied by policy
        """
        # Get intent
        async with get_session() as session:
            result = await session.execute(
                select(PaymentIntent).where(PaymentIntent.id == request.intent_id)
            )
            intent = result.scalar_one_or_none()

            if not intent:
                raise IntentNotFoundException(f"Intent {request.intent_id} not found")

            # Validate amount
            if request.amount_cents <= 0 or request.amount_cents > intent.amount_cents:
                raise InvalidAmountException(
                    f"Refund amount must be between 0 and {intent.amount_cents}"
                )

            # Check policy for high-value refunds
            threshold = int(os.getenv("PAYCORE_REFUND_SUPERVISOR_THRESHOLD", "10000"))
            if request.amount_cents > threshold:
                logger.info(
                    f"Refund exceeds threshold ({threshold}), checking policy"
                )

                try:
                    from app.modules.policy.service import get_policy_engine

                    policy_result = await get_policy_engine().evaluate({
                        "agent_id": principal.principal_id,
                        "action": "paycore.refund",
                        "resource": str(request.intent_id),
                        "params": {"amount_cents": request.amount_cents},
                    })

                    if not policy_result.allowed:
                        raise RefundDeniedException(
                            f"Refund denied by policy: {policy_result.reason}"
                        )

                except ImportError:
                    logger.warning("Policy engine not available - skipping check")

            # Create refund record
            refund = Refund(
                id=uuid4(),
                intent_id=request.intent_id,
                amount_cents=request.amount_cents,
                reason=request.reason,
                status=RefundStatus.REQUESTED.value,
                requested_by=principal.principal_id,
            )
            session.add(refund)
            await session.commit()
            await session.refresh(refund)

            logger.info(f"Created refund request: {refund.id}")

            # Process refund with provider
            try:
                provider = get_payment_provider(PaymentProviderEnum(intent.provider))
                provider_refund = await provider.create_refund(
                    provider_intent_id=intent.provider_intent_id,
                    amount_cents=request.amount_cents,
                    reason=request.reason,
                )

                # Update refund record
                refund.status = provider_refund.status.value
                refund.provider_refund_id = provider_refund.provider_refund_id
                await session.commit()
                await session.refresh(refund)

                logger.info(f"Refund processed: {refund.id} -> {refund.status}")

            except Exception as e:
                logger.error(f"Refund processing failed: {e}")
                refund.status = RefundStatus.FAILED.value
                await session.commit()
                raise

            # Publish event
            await self._publish_event({
                "event_type": "refund_requested",
                "refund_id": str(refund.id),
                "intent_id": str(intent.id),
                "amount_cents": request.amount_cents,
                "requested_by": principal.principal_id,
                "timestamp": datetime.now(timezone.utc).timestamp(),
            })

            return RefundCreateResponse(
                refund_id=refund.id,
                intent_id=refund.intent_id,
                status=RefundStatus(refund.status),
                amount_cents=refund.amount_cents,
                reason=refund.reason,
                requested_by=refund.requested_by,
                approved_by=refund.approved_by,
                created_at=refund.created_at,
            )

    async def get_refund_status(self, refund_id: UUID) -> RefundStatusResponse:
        """
        Get refund status.

        Args:
            refund_id: Refund UUID

        Returns:
            RefundStatusResponse

        Raises:
            RefundNotFoundException: If refund not found
        """
        async with get_session() as session:
            result = await session.execute(
                select(Refund).where(Refund.id == refund_id)
            )
            refund = result.scalar_one_or_none()

            if not refund:
                raise RefundNotFoundException(f"Refund {refund_id} not found")

            return RefundStatusResponse(
                refund_id=refund.id,
                intent_id=refund.intent_id,
                status=RefundStatus(refund.status),
                amount_cents=refund.amount_cents,
                reason=refund.reason,
                provider_refund_id=refund.provider_refund_id,
                requested_by=refund.requested_by,
                approved_by=refund.approved_by,
                created_at=refund.created_at,
                updated_at=refund.updated_at,
            )

    # ========================================================================
    # Webhooks
    # ========================================================================

    async def handle_webhook(
        self,
        provider: PaymentProviderEnum,
        payload: bytes,
        signature: str,
    ) -> Dict[str, Any]:
        """
        Handle provider webhook with idempotency.

        Args:
            provider: Payment provider
            payload: Raw webhook payload
            signature: Webhook signature

        Returns:
            Webhook processing result

        Raises:
            WebhookVerificationException: If signature invalid
        """
        # Get provider
        provider_instance = get_payment_provider(provider)

        # Verify webhook
        event = provider_instance.verify_webhook(payload, signature)
        normalized = provider_instance.normalize_webhook_event(event)

        event_id = normalized.get("event_id")
        event_type = normalized.get("event_type")
        provider_intent_id = normalized.get("provider_intent_id")

        logger.info(f"Webhook received: {event_type} (event_id={event_id})")

        # Check idempotency
        async with get_session() as session:
            existing = await session.execute(
                select(Transaction).where(
                    Transaction.provider_event_id == event_id
                )
            )
            if existing.scalar_one_or_none():
                logger.info(f"Event {event_id} already processed (idempotent)")
                return {
                    "success": True,
                    "event_id": event_id,
                    "event_type": event_type,
                    "processed": False,  # Already processed
                }

            # Find intent
            intent_result = await session.execute(
                select(PaymentIntent).where(
                    PaymentIntent.provider_intent_id == provider_intent_id
                )
            )
            intent = intent_result.scalar_one_or_none()

            if not intent:
                logger.warning(
                    f"Intent not found for provider_intent_id={provider_intent_id}"
                )
                # Still record transaction for audit
                intent_id = None
            else:
                intent_id = intent.id

            # Record transaction
            transaction = Transaction(
                id=uuid4(),
                intent_id=intent_id,
                event_type=self._map_event_type(event_type),
                provider_event_id=event_id,
                amount_cents=normalized.get("amount_cents", 0),
                currency=normalized.get("currency", "EUR"),
                provider_data=normalized.get("raw_data"),
            )
            session.add(transaction)

            # Update intent status if found
            if intent:
                if event_type == "payment_succeeded":
                    intent.status = IntentStatus.SUCCEEDED.value
                elif event_type in ["payment_failed", "payment_cancelled"]:
                    intent.status = IntentStatus.FAILED.value

            await session.commit()
            await session.refresh(transaction)

            logger.info(f"Transaction recorded: {transaction.id}")

            # Publish event
            await self._publish_event({
                "event_type": event_type,
                "transaction_id": str(transaction.id),
                "intent_id": str(intent_id) if intent_id else None,
                "amount_cents": transaction.amount_cents,
                "provider": provider.value,
                "timestamp": datetime.now(timezone.utc).timestamp(),
            })

            return {
                "success": True,
                "event_id": event_id,
                "event_type": event_type,
                "processed": True,
                "intent_id": str(intent_id) if intent_id else None,
                "transaction_id": str(transaction.id),
            }

    def _map_event_type(self, event_type: str) -> str:
        """Map normalized event type to TransactionEventType enum."""
        mapping = {
            "payment_succeeded": TransactionEventType.PAYMENT_SUCCEEDED.value,
            "payment_failed": TransactionEventType.PAYMENT_FAILED.value,
            "payment_cancelled": TransactionEventType.PAYMENT_CANCELLED.value,
            "refund_succeeded": TransactionEventType.REFUND_SUCCEEDED.value,
            "refund_failed": TransactionEventType.REFUND_FAILED.value,
        }
        return mapping.get(event_type, TransactionEventType.PAYMENT_SUCCEEDED.value)


# ============================================================================
# Service Singleton
# ============================================================================

_service: Optional[PayCoreService] = None


def get_paycore_service() -> PayCoreService:
    """Get or create PayCore service instance."""
    global _service
    if _service is None:
        _service = PayCoreService()
    return _service
