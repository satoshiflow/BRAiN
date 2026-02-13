"""
AXE Event Telemetry Module

Privacy-aware event collection and analytics for AXE widget.
"""
from .schemas import (
    AxeEventType,
    AnonymizationLevel,
    AxeEventCreate,
    AxeEventBatchCreate,
    AxeEventResponse,
    AxeEventStats,
    AxeEventQuery,
    PrivacySettings,
    AnonymizationResult,
)

__all__ = [
    "AxeEventType",
    "AnonymizationLevel",
    "AxeEventCreate",
    "AxeEventBatchCreate",
    "AxeEventResponse",
    "AxeEventStats",
    "AxeEventQuery",
    "PrivacySettings",
    "AnonymizationResult",
]
