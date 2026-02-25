"""
PayCore API Router

FastAPI endpoints for payment processing.
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from loguru import logger

from app.core.auth_deps import require_auth, get_current_principal, Principal

from .service import get_paycore_service, PayCoreService
from .schemas import (
    PayCoreInfo,
    PayCoreHealth,
    IntentCreateRequest,
    IntentCreateResponse,
    IntentStatusResponse,
    RefundCreateRequest,
    RefundCreateResponse,
    RefundStatusResponse,
    PaymentProvider,
)
from .exceptions import (
    IntentNotFoundException,
    RefundNotFoundException,
    RefundDeniedException,
    InvalidAmountException,
    WebhookVerificationException,
    PayCoreException,
)


router = APIRouter(
    prefix="/api/paycore",
    tags=["paycore"],
    dependencies=[Depends(require_auth)]
)


# ============================================================================
# Info & Health
# ============================================================================

@router.get("/info", response_model=PayCoreInfo)
async def get_info() -> PayCoreInfo:
    """
    Get PayCore module information.

    Returns module version, features, and supported providers.
    """
    service = get_paycore_service()
    return await service.get_info()


@router.get("/health", response_model=PayCoreHealth)
async def get_health() -> PayCoreHealth:
    """
    Health check endpoint.

    Returns system status and provider availability.
    """
    service = get_paycore_service()
    return await service.get_health()


# ============================================================================
# Payment Intents
# ============================================================================

@router.post("/intents", response_model=IntentCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_intent(
    request: IntentCreateRequest,
    principal: Principal = Depends(get_current_principal),
    service: PayCoreService = Depends(get_paycore_service),
) -> IntentCreateResponse:
    """
    Create payment intent/checkout session.

    Creates a payment intent with the specified provider (Stripe, PayPal, etc.)
    and returns a checkout URL for the user to complete payment.

    Args:
        request: Intent creation request with amount, currency, provider, metadata

    Returns:
        IntentCreateResponse with checkout_url and intent_id

    Raises:
        HTTPException 400: Invalid amount
        HTTPException 500: Provider error

    Example:
        ```json
        POST /api/paycore/intents
        {
          "amount_cents": 5000,
          "currency": "EUR",
          "provider": "stripe",
          "user_id": "user_123",
          "metadata": {
            "course_id": "course_abc",
            "product_type": "course_purchase"
          }
        }
        ```
    """
    try:
        tenant_id = principal.tenant_id or "default"
        return await service.create_intent(request, tenant_id)

    except InvalidAmountException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"Intent creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Intent creation failed: {str(e)}"
        )


@router.get("/intents/{intent_id}", response_model=IntentStatusResponse)
async def get_intent(
    intent_id: UUID,
    service: PayCoreService = Depends(get_paycore_service),
) -> IntentStatusResponse:
    """
    Get payment intent status.

    Args:
        intent_id: Payment intent UUID

    Returns:
        IntentStatusResponse with current status

    Raises:
        HTTPException 404: Intent not found
    """
    try:
        return await service.get_intent_status(intent_id)

    except IntentNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error(f"Get intent failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get intent failed: {str(e)}"
        )


@router.get("/intents/{intent_id}/status", response_model=Dict[str, Any])
async def get_intent_simple_status(
    intent_id: UUID,
    service: PayCoreService = Depends(get_paycore_service),
) -> Dict[str, Any]:
    """
    Simple status check (lightweight endpoint).

    Returns just status and basic info, useful for polling.

    Args:
        intent_id: Payment intent UUID

    Returns:
        Simple status dict

    Example Response:
        ```json
        {
          "intent_id": "uuid",
          "status": "succeeded",
          "amount_cents": 5000
        }
        ```
    """
    try:
        intent = await service.get_intent_status(intent_id)
        return {
            "intent_id": str(intent.intent_id),
            "status": intent.status.value,
            "amount_cents": intent.amount_cents,
        }

    except IntentNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# Refunds
# ============================================================================

@router.post("/refunds", response_model=RefundCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_refund(
    request: RefundCreateRequest,
    principal: Principal = Depends(get_current_principal),
    service: PayCoreService = Depends(get_paycore_service),
) -> RefundCreateResponse:
    """
    Request payment refund.

    Creates a refund request. High-value refunds (>threshold) are checked
    against Policy Engine for approval.

    Args:
        request: Refund request with intent_id, amount, reason

    Returns:
        RefundCreateResponse

    Raises:
        HTTPException 403: Refund denied by policy
        HTTPException 404: Intent not found
        HTTPException 400: Invalid amount

    Example:
        ```json
        POST /api/paycore/refunds
        {
          "intent_id": "uuid",
          "amount_cents": 5000,
          "reason": "Customer requested refund"
        }
        ```
    """
    try:
        return await service.create_refund(request, principal)

    except RefundDeniedException as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    except IntentNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except InvalidAmountException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"Refund creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refund creation failed: {str(e)}"
        )


@router.get("/refunds/{refund_id}", response_model=RefundStatusResponse)
async def get_refund(
    refund_id: UUID,
    service: PayCoreService = Depends(get_paycore_service),
) -> RefundStatusResponse:
    """
    Get refund status.

    Args:
        refund_id: Refund UUID

    Returns:
        RefundStatusResponse

    Raises:
        HTTPException 404: Refund not found
    """
    try:
        return await service.get_refund_status(refund_id)

    except RefundNotFoundException as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    except Exception as e:
        logger.error(f"Get refund failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Get refund failed: {str(e)}"
        )


# ============================================================================
# Webhooks
# ============================================================================

@router.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    service: PayCoreService = Depends(get_paycore_service),
) -> Dict[str, Any]:
    """
    Stripe webhook handler.

    Receives and processes Stripe webhook events with signature verification.
    Implements idempotency - duplicate events are ignored.

    Args:
        request: FastAPI request (for body)
        stripe_signature: Stripe-Signature header

    Returns:
        Webhook processing result

    Raises:
        HTTPException 400: Invalid signature or payload
    """
    try:
        payload = await request.body()

        if not stripe_signature:
            raise WebhookVerificationException("Missing stripe-signature header")

        result = await service.handle_webhook(
            provider=PaymentProvider.STRIPE,
            payload=payload,
            signature=stripe_signature,
        )

        return result

    except WebhookVerificationException as e:
        logger.error(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    except Exception as e:
        logger.error(f"Webhook handling failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook handling failed: {str(e)}"
        )


@router.post("/webhooks/paypal", status_code=status.HTTP_200_OK)
async def paypal_webhook(
    request: Request,
    service: PayCoreService = Depends(get_paycore_service),
) -> Dict[str, Any]:
    """
    PayPal webhook handler (STUB).

    TODO: Implement PayPal webhook handling with signature verification.

    Args:
        request: FastAPI request

    Returns:
        Webhook processing result
    """
    logger.warning("PayPal webhook handler is a stub - not yet implemented")

    return {
        "success": True,
        "event_id": "STUB",
        "event_type": "paypal.webhook",
        "processed": False,
        "message": "PayPal webhook handler not yet implemented",
    }
