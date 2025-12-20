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
from typing import Callable, Optional, Dict

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
# Security Headers (Enhanced)
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Enhanced security headers middleware with comprehensive protection.

    Headers added:
    - X-Frame-Options: Prevent clickjacking (DENY)
    - X-Content-Type-Options: Prevent MIME-sniffing (nosniff)
    - X-XSS-Protection: XSS protection for legacy browsers (deprecated but included)
    - X-Download-Options: Prevent file download in browser context (IE)
    - X-Permitted-Cross-Domain-Policies: Restrict cross-domain access (Adobe)
    - Strict-Transport-Security: Enforce HTTPS (HSTS)
    - Content-Security-Policy: Comprehensive CSP with nonce support
    - Referrer-Policy: Control referrer information leakage
    - Permissions-Policy: Control browser features
    - Cross-Origin-Opener-Policy: Prevent cross-origin attacks
    - Cross-Origin-Resource-Policy: Restrict resource sharing
    - Cross-Origin-Embedder-Policy: Enable SharedArrayBuffer

    Features:
    - Configurable CSP directives
    - CSP nonce generation for inline scripts/styles
    - Report-only mode for testing
    - Environment-aware configuration
    - HSTS preload support
    - Comprehensive feature policy
    """

    def __init__(
        self,
        app,
        hsts_enabled: bool = True,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
        csp_report_only: bool = False,
        csp_report_uri: Optional[str] = None,
        custom_csp: Optional[Dict[str, str]] = None
    ):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI app instance
            hsts_enabled: Enable HSTS header (default: True)
            hsts_max_age: HSTS max age in seconds (default: 1 year)
            hsts_include_subdomains: Include subdomains in HSTS (default: True)
            hsts_preload: Enable HSTS preload (default: True)
            csp_report_only: Use CSP report-only mode (default: False)
            csp_report_uri: CSP violation report URI (default: None)
            custom_csp: Custom CSP directives override (default: None)
        """
        super().__init__(app)
        self.hsts_enabled = hsts_enabled
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.csp_report_only = csp_report_only
        self.csp_report_uri = csp_report_uri
        self.custom_csp = custom_csp or {}

    def _generate_csp_nonce(self) -> str:
        """Generate cryptographically secure nonce for CSP."""
        import secrets
        return secrets.token_urlsafe(16)

    def _build_csp(self, nonce: Optional[str] = None) -> str:
        """
        Build Content Security Policy header.

        Args:
            nonce: Optional nonce for inline scripts/styles

        Returns:
            CSP header string
        """
        # Default CSP directives (strict)
        csp_directives = {
            # Default source: self only
            "default-src": "'self'",

            # Scripts: self + nonce (no unsafe-inline, no unsafe-eval in production)
            "script-src": f"'self' 'nonce-{nonce}'" if nonce else "'self'",

            # Styles: self + nonce
            "style-src": f"'self' 'nonce-{nonce}'" if nonce else "'self' 'unsafe-inline'",

            # Images: self + data URLs + HTTPS
            "img-src": "'self' data: https:",

            # Fonts: self + data URLs
            "font-src": "'self' data:",

            # AJAX/WebSocket: self + WebSocket protocols
            "connect-src": "'self' ws: wss:",

            # Media: self only
            "media-src": "'self'",

            # Objects: none (disable Flash, etc.)
            "object-src": "'none'",

            # Base URI: self only (prevents base tag injection)
            "base-uri": "'self'",

            # Form actions: self only
            "form-action": "'self'",

            # Frame ancestors: none (prevent clickjacking)
            "frame-ancestors": "'none'",

            # Upgrade insecure requests (HTTP -> HTTPS)
            "upgrade-insecure-requests": "",

            # Block mixed content
            "block-all-mixed-content": "",
        }

        # Apply custom CSP overrides
        csp_directives.update(self.custom_csp)

        # Add report URI if configured
        if self.csp_report_uri:
            csp_directives["report-uri"] = self.csp_report_uri

        # Build CSP string
        csp_parts = []
        for directive, value in csp_directives.items():
            if value:
                csp_parts.append(f"{directive} {value}")
            else:
                csp_parts.append(directive)

        return "; ".join(csp_parts)

    async def dispatch(self, request: Request, call_next: Callable):
        # Generate CSP nonce
        csp_nonce = self._generate_csp_nonce()

        # Store nonce in request state (for use in templates)
        request.state.csp_nonce = csp_nonce

        # Process request
        response = await call_next(request)

        # ====================================================================
        # Core Security Headers
        # ====================================================================

        # X-Frame-Options: Prevent clickjacking
        # DENY = cannot be embedded in any frame
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options: Prevent MIME-sniffing
        # nosniff = browsers must respect Content-Type header
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection: Legacy XSS protection (deprecated but harmless)
        # 1; mode=block = enable XSS filter, block page if attack detected
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # X-Download-Options: Prevent file download in browser (IE only)
        # noopen = don't auto-open downloads
        response.headers["X-Download-Options"] = "noopen"

        # X-Permitted-Cross-Domain-Policies: Restrict cross-domain access
        # none = no cross-domain policy files allowed (Flash, PDF, etc.)
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # ====================================================================
        # Content Security Policy
        # ====================================================================

        csp = self._build_csp(nonce=csp_nonce)

        if self.csp_report_only:
            # Report-only mode (for testing)
            response.headers["Content-Security-Policy-Report-Only"] = csp
        else:
            # Enforcement mode (production)
            response.headers["Content-Security-Policy"] = csp

        # ====================================================================
        # HSTS (HTTP Strict Transport Security)
        # ====================================================================

        if self.hsts_enabled:
            hsts_value = f"max-age={self.hsts_max_age}"

            if self.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"

            if self.hsts_preload:
                hsts_value += "; preload"

            response.headers["Strict-Transport-Security"] = hsts_value

        # ====================================================================
        # Referrer Policy
        # ====================================================================

        # strict-origin-when-cross-origin:
        # - Same origin: send full URL
        # - Cross origin HTTPS: send origin only
        # - HTTPS -> HTTP: send nothing
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # ====================================================================
        # Permissions Policy (Feature Policy)
        # ====================================================================

        # Restrict powerful browser features
        permissions_policy = [
            "accelerometer=()",        # Disable accelerometer
            "camera=()",               # Disable camera
            "geolocation=()",          # Disable geolocation
            "gyroscope=()",            # Disable gyroscope
            "magnetometer=()",         # Disable magnetometer
            "microphone=()",           # Disable microphone
            "payment=()",              # Disable payment API
            "usb=()",                  # Disable USB API
            "interest-cohort=()",      # Disable FLoC tracking
        ]
        response.headers["Permissions-Policy"] = ", ".join(permissions_policy)

        # ====================================================================
        # Cross-Origin Policies
        # ====================================================================

        # Cross-Origin-Opener-Policy: Isolate browsing context
        # same-origin = only same-origin documents can reference this window
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Cross-Origin-Resource-Policy: Restrict resource sharing
        # same-origin = only same-origin can load this resource
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Cross-Origin-Embedder-Policy: Enable SharedArrayBuffer
        # require-corp = require CORP header for cross-origin resources
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

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
# Audit Logging Middleware
# ============================================================================

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Automatic audit logging for all API requests.

    Features:
    - Logs all API requests (method, endpoint, user, status, duration)
    - Extracts user ID from JWT token or API key
    - Records client IP address
    - Stores in Redis with 90-day retention
    - Non-blocking (async logging)
    - Automatic failure handling (fail-open)

    Excludes:
    - Health check endpoints (/health/*)
    - Metrics endpoint (/metrics)
    - Static assets
    - WebSocket connections (logged separately)
    """

    def __init__(self, app):
        super().__init__(app)
        self.audit_logger = None
        self._initialized = False

    async def _ensure_initialized(self):
        """Lazy initialization of audit logger."""
        if not self._initialized:
            from app.core.audit import get_audit_logger
            self.audit_logger = get_audit_logger()
            self._initialized = True

    def _should_skip_audit(self, path: str) -> bool:
        """Check if path should be exempted from audit logging."""
        exempt_paths = [
            "/health/",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static/",
            "/favicon.ico",
        ]

        for exempt_path in exempt_paths:
            if path.startswith(exempt_path):
                return True

        return False

    def _extract_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request (JWT token or API key)."""
        try:
            # Check for principal in request state (set by auth middleware)
            if hasattr(request.state, "principal"):
                principal = request.state.principal
                return principal.principal_id

            # Try to extract from JWT token
            from fastapi.security import HTTPAuthorizationCredentials
            from jose import jwt
            import os

            # Check Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                try:
                    # Decode without verification (we just need the user ID)
                    payload = jwt.decode(
                        token,
                        os.getenv("JWT_SECRET_KEY", ""),
                        algorithms=["HS256"],
                        options={"verify_signature": False}  # Just for logging
                    )
                    return payload.get("sub")
                except Exception:
                    pass

            # Check API key header
            api_key_header = request.headers.get("X-API-Key")
            if api_key_header:
                # We don't validate here, just note that an API key was used
                return f"apikey:{api_key_header[:8]}..."

            return None

        except Exception as e:
            logger.debug(f"Failed to extract user ID from request: {e}")
            return None

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip audit logging for exempt paths
        if self._should_skip_audit(request.url.path):
            return await call_next(request)

        # Ensure audit logger is initialized
        await self._ensure_initialized()

        if not self.audit_logger:
            # Failover: If audit logger failed to initialize, continue without logging
            logger.warning("Audit logger not initialized, skipping audit log")
            return await call_next(request)

        # Extract request details
        method = request.method
        endpoint = request.url.path
        client_ip = request.client.host if request.client else None
        user_id = self._extract_user_id(request)

        # Start timer
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log API request (fire and forget)
            try:
                await self.audit_logger.log_api_request(
                    method=method,
                    endpoint=endpoint,
                    user_id=user_id,
                    ip_address=client_ip,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    error=None
                )
            except Exception as e:
                # Don't let audit logging failures affect the request
                logger.error(f"Failed to log audit entry: {e}")

            return response

        except Exception as exc:
            # Log failed request
            duration_ms = (time.time() - start_time) * 1000

            try:
                await self.audit_logger.log_api_request(
                    method=method,
                    endpoint=endpoint,
                    user_id=user_id,
                    ip_address=client_ip,
                    status_code=500,
                    duration_ms=duration_ms,
                    error=str(exc)
                )
            except Exception as e:
                logger.error(f"Failed to log audit entry for error: {e}")

            # Re-raise the original exception
            raise


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
