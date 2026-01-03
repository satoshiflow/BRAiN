"""
Authentication and Authorization for Genesis API

This module provides security controls for the Genesis Agent API including:
- Role-based access control (SYSTEM_ADMIN required)
- JWT token validation
- Request authentication

Author: Genesis Agent System
Version: 2.0.0
Created: 2026-01-02
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)

# Security scheme for JWT bearer tokens
security = HTTPBearer()


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when user lacks required permissions."""
    pass


async def verify_jwt_token(token: str) -> dict:
    """
    Verify JWT token and extract payload.

    Args:
        token: JWT token string

    Returns:
        dict: Token payload with user info

    Raises:
        AuthenticationError: If token is invalid

    Note:
        Phase 1: Stub implementation that accepts any token.
        Production should integrate with actual JWT validation.

    Example:
        >>> payload = await verify_jwt_token("eyJ...")
        >>> user_id = payload.get("sub")
    """
    # TODO: Implement real JWT validation
    # For Phase 1, we'll accept tokens and extract minimal info

    # Stub: Accept any token and return admin user
    # In production, use python-jose or similar to validate JWT
    try:
        # Placeholder: In real implementation, decode and validate JWT
        # import jwt
        # payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])

        # Phase 1: Return stub payload
        payload = {
            "sub": "admin_user",
            "role": "SYSTEM_ADMIN",
            "email": "admin@brain.falklabs.de"
        }
        return payload

    except Exception as e:
        logger.error(f"JWT validation failed: {e}")
        raise AuthenticationError("Invalid or expired token")


async def require_auth(
    role: str = "SYSTEM_ADMIN",
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Require authentication with specific role.

    This is the main dependency for protecting Genesis API endpoints.
    It verifies the JWT token and checks if the user has the required role.

    Args:
        role: Required role (default: SYSTEM_ADMIN)
        credentials: JWT token from Authorization header

    Returns:
        str: User ID

    Raises:
        HTTPException: 401 if auth fails, 403 if insufficient permissions

    Example:
        >>> @router.post("/create")
        >>> async def create_agent(user_id: str = Depends(require_auth)):
        ...     # Only SYSTEM_ADMIN can access
        ...     pass
    """
    token = credentials.credentials

    # Verify token
    try:
        payload = await verify_jwt_token(token)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user info
    user_id = payload.get("sub")
    user_role = payload.get("role")

    if not user_id or not user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check role
    if user_role != role:
        logger.warning(
            f"User {user_id} attempted Genesis access "
            f"(role={user_role}, required={role})"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required role: {role}"
        )

    logger.info(f"Authenticated user: {user_id} (role={user_role})")
    return user_id


async def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[str]:
    """
    Optional authentication (for public endpoints).

    Args:
        credentials: Optional JWT token

    Returns:
        Optional[str]: User ID if authenticated, None otherwise

    Example:
        >>> @router.get("/info")
        >>> async def get_info(user_id: Optional[str] = Depends(optional_auth)):
        ...     # Public endpoint with optional auth
        ...     pass
    """
    if not credentials:
        return None

    token = credentials.credentials

    try:
        payload = await verify_jwt_token(token)
        user_id = payload.get("sub")
        return user_id
    except AuthenticationError:
        # Invalid token but endpoint allows anonymous access
        return None


# ============================================================================
# Role Definitions
# ============================================================================

class Role:
    """
    Role definitions for BRAiN system.

    SYSTEM_ADMIN: Full system access, can create agents
    AGENT_MANAGER: Can manage existing agents
    VIEWER: Read-only access
    """
    SYSTEM_ADMIN = "SYSTEM_ADMIN"
    AGENT_MANAGER = "AGENT_MANAGER"
    VIEWER = "VIEWER"


def require_admin() -> str:
    """
    Convenience dependency for SYSTEM_ADMIN role.

    Returns:
        Dependency that requires SYSTEM_ADMIN role

    Example:
        >>> @router.post("/create")
        >>> async def create_agent(user_id: str = Depends(require_admin())):
        ...     pass
    """
    return Depends(lambda creds=Depends(security): require_auth(Role.SYSTEM_ADMIN, creds))
