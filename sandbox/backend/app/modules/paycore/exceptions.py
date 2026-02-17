"""
PayCore Custom Exceptions

Domain-specific exceptions for payment processing errors.
"""


class PayCoreException(Exception):
    """Base exception for PayCore module"""
    pass


class IntentNotFoundException(PayCoreException):
    """Payment intent not found"""
    pass


class RefundNotFoundException(PayCoreException):
    """Refund not found"""
    pass


class RefundDeniedException(PayCoreException):
    """Refund denied by policy"""
    pass


class InvalidAmountException(PayCoreException):
    """Invalid payment/refund amount"""
    pass


class ProviderException(PayCoreException):
    """Generic provider error"""
    pass


class StripeProviderException(ProviderException):
    """Stripe-specific error"""
    pass


class PayPalProviderException(ProviderException):
    """PayPal-specific error"""
    pass


class WebhookVerificationException(PayCoreException):
    """Webhook signature verification failed"""
    pass


class IdempotencyException(PayCoreException):
    """Duplicate event detected (already processed)"""
    pass
