"""
WebGenesis Module - Health Check Service (Sprint II)

Health monitoring for deployed sites.

Features:
- HTTP health check validation
- Configurable timeout and retries
- Linear backoff between retries
- Success on HTTP 2xx/3xx status codes

Configuration (ENV):
- BRAIN_WEBGENESIS_HEALTH_TIMEOUT: Request timeout in seconds (default: 60)
- BRAIN_WEBGENESIS_HEALTH_RETRIES: Number of retries (default: 3)
- BRAIN_WEBGENESIS_HEALTH_BACKOFF: Backoff between retries in seconds (default: 5)
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import httpx
from loguru import logger

from .schemas import HealthStatus


# ============================================================================
# Configuration
# ============================================================================

HEALTH_TIMEOUT = int(os.getenv("BRAIN_WEBGENESIS_HEALTH_TIMEOUT", "60"))
HEALTH_RETRIES = int(os.getenv("BRAIN_WEBGENESIS_HEALTH_RETRIES", "3"))
HEALTH_BACKOFF = int(os.getenv("BRAIN_WEBGENESIS_HEALTH_BACKOFF", "5"))


# ============================================================================
# Health Check Service
# ============================================================================


class HealthCheckService:
    """
    Health check service for WebGenesis sites (Sprint II).

    Features:
    - HTTP GET requests to deployment URL
    - Configurable timeout and retries
    - Linear backoff between retries
    - Success on 2xx/3xx status codes
    """

    def __init__(
        self,
        timeout: int = HEALTH_TIMEOUT,
        retries: int = HEALTH_RETRIES,
        backoff: int = HEALTH_BACKOFF,
    ):
        """
        Initialize health check service.

        Args:
            timeout: Request timeout in seconds
            retries: Number of retry attempts
            backoff: Backoff between retries in seconds (linear)
        """
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        logger.info(
            f"HealthCheckService initialized "
            f"(timeout={timeout}s, retries={retries}, backoff={backoff}s)"
        )

    async def check_site_health(
        self,
        url: str,
        path: str = "/",
    ) -> tuple[bool, HealthStatus, Optional[str]]:
        """
        Check site health via HTTP GET request.

        Makes GET request to {url}{path} and checks response.
        Retries on failure with linear backoff.

        Args:
            url: Base URL (e.g., "http://localhost:8080")
            path: Health check path (default: "/")

        Returns:
            Tuple of (success: bool, status: HealthStatus, error_message: Optional[str])

        Example:
            success, status, error = await service.check_site_health(
                "http://localhost:8080", "/"
            )
        """
        full_url = f"{url.rstrip('/')}{path}"

        logger.info(
            f"Health check started: {full_url} "
            f"(timeout={self.timeout}s, retries={self.retries})"
        )

        # Try up to retries + 1 times (initial attempt + retries)
        for attempt in range(self.retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(full_url, follow_redirects=True)

                    # Success on 2xx or 3xx status codes
                    if 200 <= response.status_code < 400:
                        logger.info(
                            f"Health check PASSED: {full_url} "
                            f"(status={response.status_code}, attempt={attempt + 1})"
                        )
                        return True, HealthStatus.HEALTHY, None

                    else:
                        error_msg = (
                            f"HTTP {response.status_code}: {response.reason_phrase}"
                        )
                        logger.warning(
                            f"Health check FAILED: {full_url} - {error_msg} "
                            f"(attempt={attempt + 1}/{self.retries + 1})"
                        )

                        # Last attempt?
                        if attempt >= self.retries:
                            return False, HealthStatus.UNHEALTHY, error_msg

            except httpx.TimeoutException as e:
                error_msg = f"Request timeout after {self.timeout}s"
                logger.warning(
                    f"Health check TIMEOUT: {full_url} - {error_msg} "
                    f"(attempt={attempt + 1}/{self.retries + 1})"
                )

                # Last attempt?
                if attempt >= self.retries:
                    return False, HealthStatus.UNHEALTHY, error_msg

            except httpx.ConnectError as e:
                error_msg = f"Connection failed: {str(e)}"
                logger.warning(
                    f"Health check CONNECTION ERROR: {full_url} - {error_msg} "
                    f"(attempt={attempt + 1}/{self.retries + 1})"
                )

                # Last attempt?
                if attempt >= self.retries:
                    return False, HealthStatus.UNHEALTHY, error_msg

            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                logger.error(
                    f"Health check ERROR: {full_url} - {error_msg} "
                    f"(attempt={attempt + 1}/{self.retries + 1})"
                )

                # Last attempt?
                if attempt >= self.retries:
                    return False, HealthStatus.UNKNOWN, error_msg

            # Backoff before retry (except on last attempt)
            if attempt < self.retries:
                logger.debug(f"Health check retry backoff: {self.backoff}s")
                await asyncio.sleep(self.backoff)

        # Should not reach here
        return False, HealthStatus.UNKNOWN, "Max retries exceeded"

    async def check_site_health_simple(self, url: str) -> bool:
        """
        Simplified health check (returns only success/failure).

        Args:
            url: Full URL to check

        Returns:
            True if healthy, False otherwise
        """
        success, status, error = await self.check_site_health(url)
        return success


# ============================================================================
# Singleton
# ============================================================================

_health_service: Optional[HealthCheckService] = None


def get_health_service() -> HealthCheckService:
    """Get singleton HealthCheckService instance."""
    global _health_service
    if _health_service is None:
        _health_service = HealthCheckService()
    return _health_service
