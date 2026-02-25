"""
PayCore API Router

FastAPI endpoints for payment processing.
"""

from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status, Request, Header
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
# Authorization Helpers
# ============================================================================


async def verify_intent_ownership(principal: Principal, intent_id: UUID, service: PayCoreService) -> bool:
    """
    Verify principal can access this intent.

    For payment operations, ownership is based on tenant_id.
    """
    try:
        intent = await service.get_intent_status(intent_id)
        # Allow access if tenant matches
        return principal.tenant_id == intent.tenant_id or principal.tenant_id == "default"
    except IntentNotFoundException:
        return False


async def verify_refund_ownership(principal: Principal, refund_id: UUID, service: PayCoreService) -> bool:
    """
    Verify principal can access this refund.
    """
    try:
        refund = await service.get_refund_status(refund_id)
        # Get intent to check tenant
        intent = await service.get_intent_status(refund.intent_id)
        return principal.tenant_id == intent.tenant_id or principal.tenant_id == "default"
    except (IntentNotFoundException, RefundNotFoundException):
        return False


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
        logger.info(f"Invalid amount in intent creation: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid amount")

    except Exception as e:
        logger.error(f"Intent creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Intent creation failed"
        )


@router.get("/intents/{intent_id}", response_model=IntentStatusResponse)
async def get_intent(
    intent_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: PayCoreService = Depends(get_paycore_service),
) -> IntentStatusResponse:
    """
    Get payment intent status.

    Args:
        intent_id: Payment intent UUID
        principal: Current user principal

    Returns:
        IntentStatusResponse with current status

    Raises:
        HTTPException 403: Not authorized to access this intent
        HTTPException 404: Intent not found
    """
    try:
        # Verify ownership before returning intent details
        if not await verify_intent_ownership(principal, intent_id, service):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this intent")

        return await service.get_intent_status(intent_id)

    except IntentNotFoundException as e:
        logger.debug(f"Intent {intent_id} not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Get intent failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/intents/{intent_id}/status", response_model=Dict[str, Any])
async def get_intent_simple_status(
    intent_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: PayCoreService = Depends(get_paycore_service),
) -> Dict[str, Any]:
    """
    Simple status check (lightweight endpoint).

    Returns just status and basic info, useful for polling.

    Args:
        intent_id: Payment intent UUID
        principal: Current user principal

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
        # Verify ownership before returning intent details
        if not await verify_intent_ownership(principal, intent_id, service):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this intent")

        intent = await service.get_intent_status(intent_id)
        return {
            "intent_id": str(intent.intent_id),
            "status": intent.status.value,
            "amount_cents": intent.amount_cents,
        }

    except IntentNotFoundException as e:
        logger.debug(f"Intent {intent_id} not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intent not found")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Get intent status failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


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
        logger.warning(f"Refund denied by policy: {e}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Refund request denied")

    except IntentNotFoundException as e:
        logger.debug(f"Intent not found for refund: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment intent not found")

    except InvalidAmountException as e:
        logger.info(f"Invalid refund amount: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid refund amount")

    except Exception as e:
        logger.error(f"Refund creation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Refund creation failed"
        )


@router.get("/refunds/{refund_id}", response_model=RefundStatusResponse)
async def get_refund(
    refund_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: PayCoreService = Depends(get_paycore_service),
) -> RefundStatusResponse:
    """
    Get refund status.

    Args:
        refund_id: Refund UUID
        principal: Current user principal

    Returns:
        RefundStatusResponse

    Raises:
        HTTPException 403: Not authorized to access this refund
        HTTPException 404: Refund not found
    """
    try:
        # Verify ownership before returning refund details
        if not await verify_refund_ownership(principal, refund_id, service):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this refund")

        return await service.get_refund_status(refund_id)

    except RefundNotFoundException as e:
        logger.debug(f"Refund {refund_id} not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"Get refund failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
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
        logger.warning(f"Webhook verification failed: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook verification failed")

    except Exception as e:
        logger.error(f"Webhook handling failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
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
