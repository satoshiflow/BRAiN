"""
Foundation Module - Core abstractions for BRAiN agents

This module provides:
- Ethics enforcement (validate actions against ethical rules)
- Safety checks (prevent dangerous operations)
- Behavior tree execution (for robotics/RYR integration)
- Foundation layer for all agent operations

Version: 0.1.0
"""

from .schemas import (
    FoundationConfig,
    FoundationStatus,
    BehaviorTreeNode,
    ActionValidationRequest,
    ActionValidationResponse,
)
from .service import FoundationService, get_foundation_service
from .router import router

__all__ = [
    # Schemas
    "FoundationConfig",
    "FoundationStatus",
    "BehaviorTreeNode",
    "ActionValidationRequest",
    "ActionValidationResponse",
    # Service
    "FoundationService",
    "get_foundation_service",
    # Router
    "router",
]

__version__ = "0.1.0"
