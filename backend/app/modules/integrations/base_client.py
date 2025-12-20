"""
Base API client for external integrations.

Provides a foundation for all external API integrations with:
- Automatic retry with exponential backoff
- Circuit breaker pattern for resilience
- Rate limiting with token bucket algorithm
- Multiple authentication types
- Request/response logging
- Comprehensive error handling
- Connection pooling
- Metrics collection

All integrations (Odoo, Bitcoin/Lightning, GitHub, etc.) should inherit
from BaseAPIClient.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union
from contextlib import asynccontextmanager
from loguru import logger
import httpx

from .schemas import (
    APIClientConfig,
    APIRequest,
    APIResponse,
    ClientMetrics,
)
from .auth import AuthenticationManager
from .rate_limit import RateLimiter
from .circuit_breaker import CircuitBreaker
from .retry import RetryHandler
from .exceptions import (
    IntegrationError,
    APIError,
    TimeoutError as IntegrationTimeoutError,
    CircuitBreakerOpenError,
    RateLimitExceededError,
)


class BaseAPIClient(ABC):
    """
    Abstract base class for all external API integrations.

    Subclasses must implement:
    - _build_base_url(): Return the base URL for the API
    - Optionally override _prepare_request() for custom request preparation
    - Optionally override _handle_response() for custom response handling

    Example:
        class OdooClient(BaseAPIClient):
            async def _build_base_url(self) -> str:
                return "https://odoo.example.com/api"

            async def get_customers(self, limit: int = 100):
                return await self.get("/customers", params={"limit": limit})
    """

    def __init__(self, config: APIClientConfig) -> None:
        """
        Initialize API client.

        Args:
            config: Client configuration
        """
        self.config = config
        self.metrics = ClientMetrics()

        # Initialize components
        self.auth_manager: Optional[AuthenticationManager] = None
        if config.auth:
            self.auth_manager = AuthenticationManager(config.auth)

        self.rate_limiter: Optional[RateLimiter] = None
        if config.rate_limit:
            self.rate_limiter = RateLimiter(config.rate_limit)

        self.circuit_breaker: Optional[CircuitBreaker] = None
        if config.circuit_breaker:
            self.circuit_breaker = CircuitBreaker(
                config.circuit_breaker,
                name=config.name,
            )

        self.retry_handler: Optional[RetryHandler] = None
        if config.retry:
            self.retry_handler = RetryHandler(config.retry)

        # HTTP client (created on first use)
        self._http_client: Optional[httpx.AsyncClient] = None

        logger.info(
            "API Client '{name}' initialized: base_url={url}",
            name=config.name,
            url=config.base_url,
        )

    @abstractmethod
    async def _build_base_url(self) -> str:
        """
        Build the base URL for this API.

        This allows subclasses to dynamically construct URLs
        (e.g., from config, environment, etc.)

        Returns:
            Base URL string
        """
        pass

    def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client with connection pooling.

        Returns:
            HTTP client instance
        """
        if self._http_client is None:
            # Create client with connection pooling
            limits = httpx.Limits(
                max_connections=self.config.max_connections,
                max_keepalive_connections=self.config.max_keepalive_connections,
            )

            timeout = httpx.Timeout(
                connect=self.config.connect_timeout,
                read=self.config.timeout,
                write=self.config.timeout,
                pool=self.config.timeout,
            )

            self._http_client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                follow_redirects=True,
            )

            logger.debug(
                "HTTP client created for '{name}': "
                "max_connections={max}, timeout={timeout}s",
                name=self.config.name,
                max=self.config.max_connections,
                timeout=self.config.timeout,
            )

        return self._http_client

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.debug("HTTP client closed for '{name}'", name=self.config.name)

    @asynccontextmanager
    async def session(self):
        """
        Context manager for client session.

        Usage:
            async with client.session():
                await client.get("/endpoint")
        """
        try:
            yield self
        finally:
            await self.close()

    async def _prepare_request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
    ) -> tuple[str, Dict[str, str], Dict[str, Any], Optional[Any], Optional[Any]]:
        """
        Prepare request with authentication and default headers.

        Args:
            method: HTTP method
            path: Request path (relative to base URL)
            headers: Additional headers
            params: Query parameters
            json: JSON body
            data: Form data

        Returns:
            Tuple of (url, headers, params, json, data)
        """
        # Build URL
        base_url = await self._build_base_url()
        if not base_url:
            base_url = self.config.base_url

        # Normalize path
        if not path.startswith("/"):
            path = f"/{path}"

        url = f"{base_url.rstrip('/')}{path}"

        # Merge headers
        request_headers = dict(self.config.default_headers)
        if headers:
            request_headers.update(headers)

        # Initialize params
        request_params = params or {}

        # Apply authentication
        if self.auth_manager:
            request_headers, request_params = await self.auth_manager.apply_auth(
                request_headers,
                request_params,
            )

        return url, request_headers, request_params, json, data

    async def _handle_response(
        self,
        response: httpx.Response,
        start_time: float,
    ) -> APIResponse:
        """
        Handle and parse response.

        Args:
            response: HTTP response
            start_time: Request start time (monotonic)

        Returns:
            Parsed API response

        Raises:
            APIError: If response indicates an error
        """
        elapsed_ms = (time.monotonic() - start_time) * 1000

        # Extract response body
        body = None
        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                body = response.json()
            else:
                body = response.text
        except Exception:
            body = response.content

        # Create response object
        api_response = APIResponse(
            status_code=response.status_code,
            headers=dict(response.headers),
            body=body,
            elapsed_ms=elapsed_ms,
        )

        # Update rate limiter from headers
        if self.rate_limiter:
            self.rate_limiter.update_from_headers(dict(response.headers))

        # Log response
        if self.config.log_responses:
            log_body = body if self.config.log_response_body else "[hidden]"
            logger.debug(
                "{name} {method} {url} → {status} ({elapsed:.0f}ms)",
                name=self.config.name,
                method=response.request.method,
                url=str(response.request.url),
                status=response.status_code,
                elapsed=elapsed_ms,
            )

        # Check for errors
        if not api_response.is_success:
            error_message = f"API error: {response.status_code}"

            # Try to extract error message from body
            if isinstance(body, dict):
                error_message = body.get("error", body.get("message", error_message))
            elif isinstance(body, str):
                error_message = body[:200]  # Truncate long error messages

            raise APIError(
                error_message,
                status_code=response.status_code,
                response_body=str(body),
            )

        return api_response

    async def _make_request(
        self,
        method: str,
        path: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
    ) -> APIResponse:
        """
        Make HTTP request with all protections (rate limit, circuit breaker, retry).

        Args:
            method: HTTP method
            path: Request path
            headers: Additional headers
            params: Query parameters
            json: JSON body
            data: Form data

        Returns:
            API response

        Raises:
            Various exceptions (RateLimitExceededError, CircuitBreakerOpenError, etc.)
        """
        # Prepare request
        url, req_headers, req_params, req_json, req_data = await self._prepare_request(
            method, path,
            headers=headers,
            params=params,
            json=json,
            data=data,
        )

        # Log request
        if self.config.log_requests:
            logger.debug(
                "{name} {method} {url}",
                name=self.config.name,
                method=method,
                url=url,
            )

        # Rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire()

        # Define actual request function
        async def make_http_request() -> APIResponse:
            start_time = time.monotonic()

            try:
                client = self._get_http_client()

                response = await client.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    params=req_params,
                    json=req_json,
                    data=req_data,
                )

                return await self._handle_response(response, start_time)

            except httpx.TimeoutException as exc:
                raise IntegrationTimeoutError(
                    f"Request timed out after {self.config.timeout}s",
                    timeout=self.config.timeout,
                ) from exc

            except httpx.HTTPError as exc:
                raise IntegrationError(
                    f"HTTP error: {exc}",
                    cause=exc,
                ) from exc

        # Circuit breaker
        if self.circuit_breaker:
            # Wrap in circuit breaker
            async def cb_wrapped() -> APIResponse:
                return await self.circuit_breaker.call(make_http_request)

            request_func = cb_wrapped
        else:
            request_func = make_http_request

        # Retry logic
        start_time = time.monotonic()
        retries = 0

        try:
            if self.retry_handler:
                response = await self.retry_handler.call(request_func)
            else:
                response = await request_func()

            # Record success metrics
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self.metrics.record_request(
                success=True,
                response_time_ms=elapsed_ms,
                retries=retries,
            )

            return response

        except RateLimitExceededError:
            # Record rate limit hit
            self.metrics.rate_limit_hits += 1
            raise

        except CircuitBreakerOpenError:
            # Record circuit breaker open
            self.metrics.circuit_breaker_opens += 1
            raise

        except Exception:
            # Record failure
            elapsed_ms = (time.monotonic() - start_time) * 1000
            self.metrics.record_request(
                success=False,
                response_time_ms=elapsed_ms,
                retries=retries,
            )
            raise

    # ========================================================================
    # Public HTTP methods
    # ========================================================================

    async def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Make GET request.

        Args:
            path: Request path
            params: Query parameters
            headers: Additional headers

        Returns:
            API response
        """
        return await self._make_request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Make POST request.

        Args:
            path: Request path
            json: JSON body
            data: Form data
            params: Query parameters
            headers: Additional headers

        Returns:
            API response
        """
        return await self._make_request(
            "POST", path,
            json=json,
            data=data,
            params=params,
            headers=headers,
        )

    async def put(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Make PUT request.

        Args:
            path: Request path
            json: JSON body
            data: Form data
            params: Query parameters
            headers: Additional headers

        Returns:
            API response
        """
        return await self._make_request(
            "PUT", path,
            json=json,
            data=data,
            params=params,
            headers=headers,
        )

    async def patch(
        self,
        path: str,
        *,
        json: Optional[Any] = None,
        data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Make PATCH request.

        Args:
            path: Request path
            json: JSON body
            data: Form data
            params: Query parameters
            headers: Additional headers

        Returns:
            API response
        """
        return await self._make_request(
            "PATCH", path,
            json=json,
            data=data,
            params=params,
            headers=headers,
        )

    async def delete(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> APIResponse:
        """
        Make DELETE request.

        Args:
            path: Request path
            params: Query parameters
            headers: Additional headers

        Returns:
            API response
        """
        return await self._make_request("DELETE", path, params=params, headers=headers)

    # ========================================================================
    # Utility methods
    # ========================================================================

    def get_metrics(self) -> ClientMetrics:
        """Get client metrics."""
        return self.metrics

    def reset_metrics(self) -> None:
        """Reset metrics to initial state."""
        self.metrics.reset()
        logger.debug("Metrics reset for '{name}'", name=self.config.name)

    async def health_check(self) -> bool:
        """
        Perform health check.

        Subclasses can override to implement custom health checks.
        Default implementation just checks if circuit breaker is not open.

        Returns:
            True if healthy, False otherwise
        """
        if self.circuit_breaker and self.circuit_breaker.is_open:
            logger.warning(
                "Health check failed for '{name}': circuit breaker is open",
                name=self.config.name,
            )
            return False

        return True

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"name={self.config.name} "
            f"base_url={self.config.base_url}>"
        )