"""Immune System Module - BRAiN defense and self-protection.

Implements:
- Event tracking and health monitoring
- Automatic self-protection responses
- Credit withdrawal integration (Myzel-Hybrid-Charta)
- Circuit breaker pattern for cascading failures
- Resource management (garbage collection, backpressure)
"""

from .core.service import ImmuneService
from .schemas import (
    ImmuneEvent,
    ImmuneHealthSummary,
    ImmuneSeverity,
    ImmuneType,
)

__all__ = [
    "ImmuneService",
    "ImmuneEvent",
    "ImmuneHealthSummary",
    "ImmuneSeverity",
    "ImmuneType",
]
