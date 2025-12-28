"""
Course Factory Events Layer

Handles payment events from PayCore and other external systems.
"""

from .subscribers import CoursePaymentSubscriber
from .handlers import (
    handle_payment_succeeded,
    handle_payment_failed,
    handle_refund_succeeded,
)

__all__ = [
    "CoursePaymentSubscriber",
    "handle_payment_succeeded",
    "handle_payment_failed",
    "handle_refund_succeeded",
]
