"""
Production-grade middleware for BRAiN Core.

Provides:
- Global exception handling
- Request ID tracking
- Security headers
- Request logging
- Prometheus metrics tracking
"""

import time
import uuid
import traceback
from datetime import datetime
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


# ============================================================================
# Global Exception Handler
# ============================================================================

class GlobalExceptionMiddleware(BaseHTTPMiddleware):
    """
    Catches all unhandled exceptions and returns structured JSON responses.

    Features:
    - Prevents raw exception exposure to clients
    - Logs full error details server-side
    - Returns user-friendly error messages
    - Includes request ID for debugging
    """

    async def dispatch(self, request: Request, call_next: Callable):
        try:
            return await call_next(request)
        except Exception as exc:
            # Get request ID (from Request ID middleware)
            request_id = getattr(request.state, "request_id", "unknown")

            # Log full error details
            logger.error(
                f"Unhandled exception in {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "client": request.client.host if request.client else "unknown",
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                    "traceback": traceback.format_exc(),
                },
            )

            # Return structured error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred. Please contact support if the issue persists.",
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )


# ============================================================================
# Request ID Tracking
# ============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Adds unique request ID to each request for tracing.

    Features:
    - Generates UUID for each request
    - Accepts X-Request-ID header from clients
    - Adds X-Request-ID to response headers
    - Stores in request.state for use in logs
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Try to get request ID from header, otherwise generate new
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in request state for access in routes
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


# ============================================================================
# Security Headers
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses.

    Headers added:
    - X-Frame-Options: Prevent clickjacking
    - X-Content-Type-Options: Prevent MIME-sniffing
    - X-XSS-Protection: XSS protection for older browsers
    - Strict-Transport-Security: Enforce HTTPS
    - Content-Security-Policy: Restrict resource loading
    - Referrer-Policy: Control referrer information
    """

    def __init__(self, app, hsts_enabled: bool = True):
        super().__init__(app)
        self.hsts_enabled = hsts_enabled

    async def dispatch(self, request: Request, call_next: Callable):
        response = await call_next(request)

        # Security headers
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (adjust as needed)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:;"
        )

        # HSTS (only in production/HTTPS)
        if self.hsts_enabled:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


# ============================================================================
# Request Logging
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs all incoming requests and their processing time.

    Features:
    - Request method, path, client IP
    - Response status code
    - Processing time
    - Request ID correlation
    """

    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()

        # Get request details
        request_id = getattr(request.state, "request_id", "unknown")
        client_ip = request.client.host if request.client else "unknown"

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Log request
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": f"{process_time:.3f}s",
                "client_ip": client_ip,
            },
        )

        # Add process time to response header (useful for debugging)
        response.headers["X-Process-Time"] = f"{process_time:.3f}"

        return response


# ============================================================================
# Rate Limiting (Simple In-Memory) - DEPRECATED
# ============================================================================

from collections import defaultdict
from datetime import datetime, timedelta


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting.

    ⚠️ DEPRECATED: Use RedisRateLimitMiddleware for production!

    WARNING: This is for basic protection only!
    Not suitable for production (not distributed, memory-bound).

    Limits:
    - 100 requests per minute per IP
    - Returns 429 Too Many Requests when exceeded
    """

    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)  # {ip: [timestamps]}

    async def dispatch(self, request: Request, call_next: Callable):
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Clean old timestamps
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.requests[client_ip] = [
            ts for ts in self.requests[client_ip] if ts > cutoff
        ]

        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.max_requests} requests per {self.window_seconds}s",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Add current request timestamp
        self.requests[client_ip].append(now)

        return await call_next(request)


# ============================================================================
# Rate Limiting (Redis-based - Production)
# ============================================================================

class RedisRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-grade distributed rate limiting using Redis.

    Features:
    - Distributed across multiple backend instances
    - Per-IP and per-user rate limiting
    - Multiple rate limit tiers (global, authenticated, premium)
    - Sliding window log algorithm (accurate counting)
    - Automatic Redis failover (fail-open)
    - Prometheus metrics integration

    Configuration:
    - Global (unauthenticated): 100 req/min
    - Authenticated users: 500 req/min
    - Premium/admin users: 5000 req/min

    Exemptions:
    - /health/* endpoints (health checks should not be rate limited)
    - /metrics endpoint (Prometheus scraping)
    """

    def __init__(self, app):
        super().__init__(app)
        # Rate limiter will be initialized in middleware
        # (to avoid circular imports with redis_client)
        self.rate_limiter = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazy initialization of rate limiter."""
        if not self._initialized:
            from app.core.redis_client import get_redis
            from app.core.rate_limiter import RateLimiter

            redis = await get_redis()
            self.rate_limiter = RateLimiter(redis)
            self._initialized = True

    def _should_skip_rate_limit(self, path: str) -> bool:
        """Check if path should be exempted from rate limiting."""
        exempt_paths = [
            "/health/",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

        for exempt_path in exempt_paths:
            if path.startswith(exempt_path):
                return True

        return False

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting for exempt paths
        if self._should_skip_rate_limit(request.url.path):
            return await call_next(request)

        # Ensure rate limiter is initialized
        await self._ensure_initialized()

        if not self.rate_limiter:
            # Failover: If rate limiter failed to initialize, allow request
            logger.warning("Rate limiter not initialized, allowing request")
            return await call_next(request)

        # Import utilities
        from app.core.rate_limiter import (
            get_client_identifier,
            get_rate_limit_tier,
            RateLimitTier,
        )

        try:
            # Get client identifier (user ID, API key, or IP)
            client_id = get_client_identifier(request)

            # Get rate limit tier
            tier_name = get_rate_limit_tier(request)
            tier_config = RateLimitTier.get_limit(tier_name)

            # Check rate limit
            allowed, retry_after = await self.rate_limiter.is_allowed(
                key=client_id,
                max_requests=tier_config["max_requests"],
                window_seconds=tier_config["window_seconds"],
            )

            if not allowed:
                # Track rate limit hit in metrics
                from app.core.metrics import MetricsCollector
                MetricsCollector.track_rate_limit_hit(client_id, tier_name)

                # Return 429 Too Many Requests
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Too many requests. Limit: {tier_config['max_requests']} requests per {tier_config['window_seconds']}s",
                        "tier": tier_name,
                        "retry_after": retry_after,
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(tier_config["max_requests"]),
                        "X-RateLimit-Window": str(tier_config["window_seconds"]),
                    },
                )

            # Request allowed - add rate limit headers
            response = await call_next(request)

            # Get current usage
            usage = await self.rate_limiter.get_usage(
                client_id, tier_config["window_seconds"]
            )

            # Add informational headers
            response.headers["X-RateLimit-Limit"] = str(tier_config["max_requests"])
            response.headers["X-RateLimit-Remaining"] = str(
                max(0, tier_config["max_requests"] - usage["count"])
            )
            response.headers["X-RateLimit-Window"] = str(tier_config["window_seconds"])

            return response

        except Exception as e:
            # Failover: If rate limiting fails, allow request (fail-open)
            logger.error(f"Rate limit middleware error: {e}", exc_info=True)
            return await call_next(request)


# ============================================================================
# Prometheus Metrics Middleware
# ============================================================================

class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Collects Prometheus metrics for HTTP requests.

    Metrics collected:
    - Request count (method, endpoint, status)
    - Request duration (method, endpoint)
    - Requests in progress (method, endpoint)
    - Request/response size (optional)

    Features:
    - Automatic endpoint normalization (path parameters)
    - Excludes /metrics endpoint (avoids self-tracking)
    - Low overhead
    """

    def __init__(self, app):
        super().__init__(app)
        # Import here to avoid circular imports
        from app.core.metrics import (
            http_requests_in_progress,
            MetricsCollector
        )
        self.in_progress = http_requests_in_progress
        self.metrics = MetricsCollector

    def _normalize_endpoint(self, path: str) -> str:
        """
        Normalize endpoint path for metrics.

        Replaces path parameters with placeholders to avoid
        high cardinality in metrics.

        Example:
            /api/users/123 -> /api/users/{id}
            /api/missions/abc-def -> /api/missions/{id}
        """
        # Simple normalization: replace UUIDs and numeric IDs
        import re

        # Replace UUIDs (8-4-4-4-12 format)
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{id}',
            path,
            flags=re.IGNORECASE
        )

        # Replace numeric IDs (e.g., /users/123 -> /users/{id})
        path = re.sub(r'/\d+', '/{id}', path)

        # Replace alphanumeric IDs (e.g., /users/abc123 -> /users/{id})
        # Be conservative: only if it looks like an ID (>6 chars, alphanumeric)
        path = re.sub(r'/[a-zA-Z0-9_-]{8,}', '/{id}', path)

        return path

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip metrics endpoint to avoid self-tracking
        if request.url.path == "/metrics":
            return await call_next(request)

        # Normalize endpoint for metrics
        endpoint = self._normalize_endpoint(request.url.path)
        method = request.method

        # Track requests in progress
        self.in_progress.labels(method=method, endpoint=endpoint).inc()

        # Track request size (optional)
        request_size = None
        if hasattr(request, 'headers') and 'content-length' in request.headers:
            try:
                request_size = int(request.headers['content-length'])
            except (ValueError, KeyError):
                pass

        # Start timer
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Track response size
            response_size = None
            if hasattr(response, 'headers') and 'content-length' in response.headers:
                try:
                    response_size = int(response.headers['content-length'])
                except (ValueError, KeyError):
                    pass

            # Record metrics
            self.metrics.track_http_request(
                method=method,
                endpoint=endpoint,
                status=response.status_code,
                duration=duration,
                request_size=request_size,
                response_size=response_size
            )

            return response

        except Exception as exc:
            # Track error
            duration = time.time() - start_time
            self.metrics.track_http_request(
                method=method,
                endpoint=endpoint,
                status=500,
                duration=duration,
                request_size=request_size
            )
            raise

        finally:
            # Decrement in-progress counter
            self.in_progress.labels(method=method, endpoint=endpoint).dec()


# ============================================================================
# Utility Functions
# ============================================================================

def get_request_id(request: Request) -> str:
    """
    Get the request ID from the request state.

    Usage:
        from app.core.middleware import get_request_id

        @router.get("/")
        async def handler(request: Request):
            request_id = get_request_id(request)
            logger.info(f"Processing {request_id}")
    """
    return getattr(request.state, "request_id", "unknown")
