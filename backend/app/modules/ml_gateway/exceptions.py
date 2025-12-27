"""
ML Gateway Module - Custom Exceptions

Exception hierarchy for ML-related errors.
"""

from typing import Optional


class MLGatewayException(Exception):
    """Base exception for ML Gateway errors"""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class MLServiceUnavailableError(MLGatewayException):
    """ML service is unavailable or unreachable"""

    pass


class MLTimeoutError(MLGatewayException):
    """ML service request timed out"""

    pass


class MLInvalidResponseError(MLGatewayException):
    """ML service returned invalid or malformed response"""

    pass


class MLModelVersionMismatchError(MLGatewayException):
    """ML model version doesn't match expected version"""

    pass


class MLInferenceError(MLGatewayException):
    """Error during ML model inference"""

    pass


class MLConfigurationError(MLGatewayException):
    """ML Gateway configuration error"""

    pass
