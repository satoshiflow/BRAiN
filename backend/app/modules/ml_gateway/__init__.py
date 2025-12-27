"""
ML Gateway Module

Machine Learning integration for governance augmentation.
Provides risk scoring and context enrichment as advisory inputs to deterministic governance.
"""

from .router import router
from .schemas import (
    MLEnrichedContext,
    MLGatewayHealth,
    MLGatewayInfo,
    MLProviderConfig,
    MLProviderStatus,
    RiskFactor,
    RiskScoreRequest,
    RiskScoreResponse,
)
from .service import MLGatewayService, get_ml_gateway_service

__all__ = [
    # Router
    "router",
    # Service
    "MLGatewayService",
    "get_ml_gateway_service",
    # Schemas
    "MLProviderConfig",
    "MLProviderStatus",
    "RiskScoreRequest",
    "RiskScoreResponse",
    "RiskFactor",
    "MLEnrichedContext",
    "MLGatewayHealth",
    "MLGatewayInfo",
]
