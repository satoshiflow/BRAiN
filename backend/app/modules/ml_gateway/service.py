"""
ML Gateway Service

Core service for ML-powered risk scoring with fail-closed architecture.
Implements optional provider pattern - BRAiN remains fully functional without ML.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from loguru import logger

from .exceptions import (
    MLInferenceError,
    MLServiceUnavailableError,
    MLTimeoutError,
)
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


class MLGatewayService:
    """
    ML Gateway Service - Optional Provider Pattern

    Provides ML-powered risk scoring as an advisory input to governance.
    Implements fail-closed architecture: if ML unavailable, uses conservative fallback.

    Design Principles:
    1. Determinism First: ML scores are INPUTS, not DECISIONS
    2. Fail-Closed: Service unavailability doesn't compromise safety
    3. Auditability: All ML outputs are logged and versioned
    4. Optional: BRAiN core functions without ML
    """

    def __init__(self, config: Optional[MLProviderConfig] = None):
        """
        Initialize ML Gateway service

        Args:
            config: ML provider configuration (uses defaults if None)
        """
        self.config = config or MLProviderConfig()
        self._start_time = time.time()

        # Metrics
        self._total_requests = 0
        self._successful_requests = 0
        self._failed_requests = 0
        self._fallback_requests = 0
        self._total_inference_time_ms = 0.0

        # Risk scoring sidecar (will be injected)
        self._risk_scorer: Optional[Any] = None

        logger.info(
            f"ML Gateway initialized (enabled={self.config.enabled}, "
            f"timeout={self.config.timeout_ms}ms, "
            f"model_version={self.config.model_version})"
        )

    def set_risk_scorer(self, scorer: Any) -> None:
        """
        Inject risk scoring sidecar

        Args:
            scorer: Risk scoring service instance
        """
        self._risk_scorer = scorer
        logger.info(f"Risk scorer injected: {type(scorer).__name__}")

    async def get_risk_score(
        self, request: RiskScoreRequest
    ) -> RiskScoreResponse:
        """
        Get ML risk score with automatic fallback

        Implements fail-closed pattern:
        1. Try ML service (with timeout)
        2. If unavailable/timeout/error → use conservative fallback
        3. Log all outcomes for audit trail

        Args:
            request: Risk scoring request

        Returns:
            RiskScoreResponse with score or fallback
        """
        self._total_requests += 1
        start_time = time.time()

        # Check if ML is enabled
        if not self.config.enabled:
            logger.debug("ML Gateway disabled, using fallback score")
            self._fallback_requests += 1
            return self._get_fallback_score(reason="ml_disabled")

        # Check if risk scorer is available
        if self._risk_scorer is None:
            logger.warning("No risk scorer configured, using fallback")
            self._fallback_requests += 1
            return self._get_fallback_score(reason="no_scorer_configured")

        try:
            # Attempt ML inference with timeout
            timeout_seconds = self.config.timeout_ms / 1000.0
            response = await asyncio.wait_for(
                self._compute_risk_score(request),
                timeout=timeout_seconds,
            )

            # Validate response
            if not self._is_valid_response(response):
                logger.error("Invalid ML response, using fallback")
                self._failed_requests += 1
                return self._get_fallback_score(reason="invalid_response")

            # Success
            inference_time_ms = (time.time() - start_time) * 1000
            self._successful_requests += 1
            self._total_inference_time_ms += inference_time_ms

            logger.debug(
                f"ML risk score computed: {response.risk_score:.3f} "
                f"(confidence={response.confidence:.3f}, "
                f"time={inference_time_ms:.1f}ms)"
            )

            return response

        except asyncio.TimeoutError:
            logger.warning(
                f"ML request timed out after {self.config.timeout_ms}ms, "
                "using fallback"
            )
            self._failed_requests += 1
            self._fallback_requests += 1
            return self._get_fallback_score(reason="timeout")

        except MLServiceUnavailableError as e:
            logger.warning(f"ML service unavailable: {e.message}, using fallback")
            self._failed_requests += 1
            self._fallback_requests += 1
            return self._get_fallback_score(reason="service_unavailable")

        except Exception as e:
            logger.error(f"ML inference error: {e}, using fallback")
            self._failed_requests += 1
            self._fallback_requests += 1
            return self._get_fallback_score(reason=f"error: {type(e).__name__}")

    async def _compute_risk_score(
        self, request: RiskScoreRequest
    ) -> RiskScoreResponse:
        """
        Compute risk score using ML sidecar

        Args:
            request: Risk scoring request

        Returns:
            RiskScoreResponse from ML model

        Raises:
            MLServiceUnavailableError: If service is down
            MLInferenceError: If inference fails
        """
        if self._risk_scorer is None:
            raise MLServiceUnavailableError("Risk scorer not configured")

        start_time = time.time()

        try:
            # Delegate to risk scoring sidecar
            result = await self._risk_scorer.score(request)
            inference_time_ms = (time.time() - start_time) * 1000

            # Build response
            return RiskScoreResponse(
                risk_score=result.get("risk_score", 0.5),
                confidence=result.get("confidence", 0.0),
                top_factors=[
                    RiskFactor(
                        factor=f["factor"],
                        weight=f["weight"],
                        description=f.get("description", ""),
                    )
                    for f in result.get("top_factors", [])
                ],
                model_version=self.config.model_version,
                inference_time_ms=inference_time_ms,
                is_fallback=False,
            )

        except Exception as e:
            raise MLInferenceError(f"Inference failed: {e}")

    def _get_fallback_score(self, reason: str = "unknown") -> RiskScoreResponse:
        """
        Generate conservative fallback risk score

        Used when ML service is unavailable. Returns mid-range risk score
        with zero confidence to signal uncertainty.

        Args:
            reason: Reason for fallback (for logging)

        Returns:
            Conservative fallback RiskScoreResponse
        """
        return RiskScoreResponse(
            risk_score=self.config.fallback_risk_score,
            confidence=0.0,  # Zero confidence signals "unknown"
            top_factors=[
                RiskFactor(
                    factor="ml_unavailable",
                    weight=1.0,
                    description=f"ML service unavailable: {reason}",
                )
            ],
            model_version=self.config.model_version,
            inference_time_ms=0.0,
            is_fallback=True,
        )

    def _is_valid_response(self, response: RiskScoreResponse) -> bool:
        """
        Validate ML response

        Args:
            response: ML response to validate

        Returns:
            True if response is valid
        """
        try:
            # Check score range
            if not 0.0 <= response.risk_score <= 1.0:
                logger.error(f"Invalid risk_score: {response.risk_score}")
                return False

            # Check confidence range
            if not 0.0 <= response.confidence <= 1.0:
                logger.error(f"Invalid confidence: {response.confidence}")
                return False

            # Check model version matches
            if response.model_version != self.config.model_version:
                logger.warning(
                    f"Model version mismatch: expected {self.config.model_version}, "
                    f"got {response.model_version}"
                )
                # Don't reject, just warn
                # return False

            return True

        except Exception as e:
            logger.error(f"Response validation error: {e}")
            return False

    async def enrich_context(
        self, context: Dict[str, Any], request_info: Optional[Dict[str, Any]] = None
    ) -> MLEnrichedContext:
        """
        Enrich context with ML risk scores for policy evaluation

        Args:
            context: Original context data
            request_info: Optional request metadata (mission_id, agent_id, action)

        Returns:
            MLEnrichedContext with risk scores
        """
        request_info = request_info or {}
        request = RiskScoreRequest(
            context=context,
            mission_id=request_info.get("mission_id"),
            agent_id=request_info.get("agent_id"),
            action=request_info.get("action"),
        )

        score_response = await self.get_risk_score(request)

        return MLEnrichedContext(
            original_context=context,
            ml_risk_score=score_response.risk_score,
            ml_confidence=score_response.confidence,
            ml_model_version=score_response.model_version,
            ml_top_factors=score_response.top_factors,
            ml_is_fallback=score_response.is_fallback,
            ml_inference_time_ms=score_response.inference_time_ms,
            ml_timestamp=score_response.timestamp,
        )

    def get_health(self) -> MLGatewayHealth:
        """
        Get health status of ML Gateway

        Returns:
            MLGatewayHealth with metrics
        """
        uptime = time.time() - self._start_time
        avg_inference_time = (
            self._total_inference_time_ms / self._successful_requests
            if self._successful_requests > 0
            else 0.0
        )

        # Determine status
        if not self.config.enabled:
            status = MLProviderStatus.DISABLED
        elif self._risk_scorer is None:
            status = MLProviderStatus.UNAVAILABLE
        elif self._successful_requests == 0 and self._total_requests > 0:
            status = MLProviderStatus.UNAVAILABLE
        elif self._fallback_requests > self._successful_requests:
            status = MLProviderStatus.DEGRADED
        else:
            status = MLProviderStatus.AVAILABLE

        return MLGatewayHealth(
            status=status,
            provider_available=self._risk_scorer is not None,
            model_version=self.config.model_version,
            uptime_seconds=uptime,
            total_requests=self._total_requests,
            successful_requests=self._successful_requests,
            failed_requests=self._failed_requests,
            fallback_requests=self._fallback_requests,
            avg_inference_time_ms=avg_inference_time,
        )

    def get_info(self) -> MLGatewayInfo:
        """
        Get ML Gateway system information

        Returns:
            MLGatewayInfo
        """
        return MLGatewayInfo(
            enabled=self.config.enabled,
            config=self.config,
        )


# ============================================================================
# Singleton Instance
# ============================================================================

_ml_gateway_service: Optional[MLGatewayService] = None


def get_ml_gateway_service() -> MLGatewayService:
    """
    Get or create ML Gateway service singleton

    Returns:
        MLGatewayService instance
    """
    global _ml_gateway_service
    if _ml_gateway_service is None:
        _ml_gateway_service = MLGatewayService()
    return _ml_gateway_service
