"""
Production-grade middleware for BRAiN Core.

Provides:
- Global exception handling
- Request ID tracking
- Security headers
- Request logging
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
# Rate Limiting (Simple In-Memory)
# ============================================================================

from collections import defaultdict
from datetime import datetime, timedelta


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple in-memory rate limiting.

    WARNING: This is for basic protection only!
    For production, use Redis-based rate limiting (slowapi).

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
