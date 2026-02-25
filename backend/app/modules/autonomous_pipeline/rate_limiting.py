"""
Rate Limiting Configuration for Autonomous Pipeline

Provides rate limiting for workspace pipeline execution.
Uses slowapi for per-endpoint rate limiting.
"""

from typing import Callable
from slowapi import Limiter
from slowapi.util import get_remote_address

# Create a separate limiter instance for workspace pipeline execution
# This allows for specific rate limits independent of the global limiter
workspace_limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
)

# Rate limit decorators for common operations
# Pipeline execution: 10 requests per minute per IP
PIPELINE_EXECUTE_LIMIT = "10/minute"

# Workspace CRUD: 100 requests per minute per IP
WORKSPACE_CRUD_LIMIT = "100/minute"

# Project CRUD: 100 requests per minute per IP
PROJECT_CRUD_LIMIT = "100/minute"
