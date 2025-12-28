"""
Course Payment Event Handlers

Business logic for processing payment events.
Handles course access granting, revocation, and auditing.
"""

from __future__ import annotations

from typing import Dict, Any
from loguru import logger

from app.modules.course_factory.monetization_service import get_monetization_service


async def handle_payment_succeeded(event: Dict[str, Any]) -> None:
    """
    Handle successful payment event.

    Grants course access by creating enrollment.

    Args:
        event: Payment succeeded event

    Expected event structure:
        {
            "event_type": "paycore.payment_succeeded",
            "trace_id": "evt_...",
            "tenant_id": "tenant_123",
            "intent_id": "intent_xyz",
            "tx_id": "tx_abc",
            "user_id": "user_456",
            "metadata": {
                "course_id": "course_789",
                "language": "de"
            }
        }

    Raises:
        ValueError: If required fields missing
        Exception: On service errors (transient)
    """
    # Extract required fields
    tenant_id = event.get("tenant_id")
    user_id = event.get("user_id")
    metadata = event.get("metadata", {})
    course_id = metadata.get("course_id")
    language = metadata.get("language", "de")

    # Validate
    if not all([tenant_id, user_id, course_id]):
        raise ValueError(
            f"Missing required fields: tenant_id={tenant_id}, user_id={user_id}, course_id={course_id}"
        )

    # Create pseudonymous actor_id (tenant-scoped)
    actor_id = f"{tenant_id}:{user_id}"

    logger.info(
        f"[CoursePayment] Granting course access",
        tenant_id=tenant_id,
        course_id=course_id,
        actor_id=actor_id,
        trace_id=event.get("trace_id"),
    )

    try:
        # Grant access via enrollment service
        service = get_monetization_service()
        enrollment = await service.enroll_course(
            course_id=course_id,
            language=language,
            actor_id=actor_id,
        )

        logger.info(
            f"[CoursePayment] Course access granted successfully",
            enrollment_id=enrollment.enrollment_id,
            course_id=course_id,
            tenant_id=tenant_id,
            trace_id=event.get("trace_id"),
        )

    except Exception as e:
        logger.error(
            f"[CoursePayment] Failed to grant course access: {e}",
            tenant_id=tenant_id,
            course_id=course_id,
            trace_id=event.get("trace_id"),
        )
        raise  # Re-raise for retry logic


async def handle_payment_failed(event: Dict[str, Any]) -> None:
    """
    Handle failed payment event.

    Logs failure for auditing (no access granted).

    Args:
        event: Payment failed event
    """
    tenant_id = event.get("tenant_id")
    user_id = event.get("user_id")
    metadata = event.get("metadata", {})
    course_id = metadata.get("course_id")

    logger.warning(
        f"[CoursePayment] Payment failed (no access granted)",
        tenant_id=tenant_id,
        user_id=user_id,
        course_id=course_id,
        trace_id=event.get("trace_id"),
    )

    # Future: Could trigger notification or retry logic


async def handle_refund_succeeded(event: Dict[str, Any]) -> None:
    """
    Handle successful refund event.

    Marks enrollment as refunded (optionally revokes access).

    Args:
        event: Refund succeeded event

    Expected event structure:
        {
            "event_type": "paycore.refund_succeeded",
            "trace_id": "evt_...",
            "tenant_id": "tenant_123",
            "intent_id": "intent_xyz",  # Original payment intent
            "refund_id": "ref_abc",
            "user_id": "user_456",
            "metadata": {
                "course_id": "course_789",
                "enrollment_id": "enr_..."  # If available
            }
        }

    Raises:
        ValueError: If required fields missing
    """
    tenant_id = event.get("tenant_id")
    user_id = event.get("user_id")
    metadata = event.get("metadata", {})
    course_id = metadata.get("course_id")
    enrollment_id = metadata.get("enrollment_id")

    if not all([tenant_id, user_id, course_id]):
        raise ValueError(
            f"Missing required fields: tenant_id={tenant_id}, user_id={user_id}, course_id={course_id}"
        )

    logger.warning(
        f"[CoursePayment] Refund processed",
        tenant_id=tenant_id,
        course_id=course_id,
        enrollment_id=enrollment_id,
        trace_id=event.get("trace_id"),
    )

    # TODO: Implement enrollment revocation logic
    # Options:
    # 1. Soft delete: Mark enrollment.status = "refunded"
    # 2. Hard delete: Remove enrollment record
    # 3. Access control: Add to blocklist, keep enrollment for history
    #
    # For MVP: Just log the refund (no revocation)
    # Future: Add enrollment status field and update it

    logger.info(
        f"[CoursePayment] Refund logged (access revocation not implemented)",
        course_id=course_id,
        tenant_id=tenant_id,
    )
