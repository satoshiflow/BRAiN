"""
Rate Limiting Configuration for BRAiN

Uses slowapi with Redis backend for distributed rate limiting.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from starlette.responses import JSONResponse


# Key function for per-user rate limiting
def get_user_identifier(request: Request) -> str:
    """
    Get user identifier for rate limiting.
    Uses principal_id from auth if available, falls back to IP address.
    """
    # Try to get authenticated user ID
    principal = getattr(request.state, "principal", None)
    if principal and hasattr(principal, "principal_id"):
        return f"user:{principal.principal_id}"
    
    # Fall back to IP address
    return f"ip:{get_remote_address(request)}"


# Key function for per-IP rate limiting (for auth endpoints)
def get_ip_identifier(request: Request) -> str:
    """Get IP address for rate limiting."""
    return get_remote_address(request)


# Create limiter instance with Redis backend (if available) or memory
# In production, configure Redis: limiter = Limiter(key_func=..., storage_uri="redis://localhost:6379")
limiter = Limiter(
    key_func=get_user_identifier,
    default_limits=["100/minute"],  # Global default: 100 req/min per user
)


# Rate limit configurations
class RateLimits:
    """Rate limit definitions for BRAiN endpoints."""
    
    # Skills: 10 executions per minute per user
    SKILLS_EXECUTE = "10/minute"
    
    # Missions: 5 instantiations per minute per user
    MISSIONS_INSTANTIATE = "5/minute"
    
    # Auth: 5 login attempts per 15 minutes per IP
    AUTH_LOGIN = "5/15minute"
    
    # Immune events: 100 per minute global
    IMMUNE_EVENTS = "100/minute"
    
    # Foundation validation: 50 per minute per user
    FOUNDATION_VALIDATE = "50/minute"


# Custom rate limit exceeded handler
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit exceeded errors.
    Returns 429 Too Many Requests with retry-after info.
    """
    retry_after = getattr(exc, "retry_after", 60)
    
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "detail": "Too many requests. Please slow down.",
            "retry_after_seconds": retry_after,
            "limit": str(exc.limit) if hasattr(exc, "limit") else "unknown",
        },
        headers={"Retry-After": str(retry_after)},
    )


def add_rate_limit_headers(response, limit: str, remaining: int, reset_time: int):
    """
    Add rate limit headers to response for client awareness.
    
    Headers:
        X-RateLimit-Limit: Maximum requests allowed
        X-RateLimit-Remaining: Requests remaining in current window
        X-RateLimit-Reset: Unix timestamp when limit resets
    """
    response.headers["X-RateLimit-Limit"] = limit
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(reset_time)
    return response
