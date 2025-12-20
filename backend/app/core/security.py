"""
Security and authentication for BRAiN Core.

Provides:
- JWT token-based authentication
- API key authentication
- Principal (user) model with roles
- Dependency injection for protected routes
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer, APIKeyHeader
from jose import JWTError

from .jwt import verify_token

security_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class Principal:
    """
    Represents an authenticated user/principal in the system.

    Attributes:
        principal_id: Unique identifier for the principal (user ID)
        tenant_id: Optional tenant ID for multi-tenancy
        app_id: Optional application ID
        roles: List of role names assigned to the principal
    """

    def __init__(
        self,
        principal_id: str,
        tenant_id: str | None = None,
        app_id: str | None = None,
        roles: list[str] | None = None,
    ):
        self.principal_id = principal_id
        self.tenant_id = tenant_id
        self.app_id = app_id
        self.roles = roles or []

    def has_role(self, role: str) -> bool:
        """Check if principal has a specific role."""
        return role in self.roles

    def has_any_role(self, *roles: str) -> bool:
        """Check if principal has any of the specified roles."""
        return any(role in self.roles for role in roles)

    def __repr__(self) -> str:
        return f"Principal(id={self.principal_id}, roles={self.roles})"


async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> Principal:
    """
    Dependency to get the current authenticated principal from JWT token.

    Args:
        credentials: HTTP Authorization header with Bearer token

    Returns:
        Principal object with user information

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired

    Usage:
        @router.get("/protected")
        async def protected_route(
            principal: Principal = Depends(get_current_principal)
        ):
            return {"user_id": principal.principal_id}
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        # Verify and decode JWT token
        payload = verify_token(token)

        # Extract user information from token
        principal_id = payload.get("sub")
        if principal_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload: missing 'sub' claim",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Extract optional fields
        tenant_id = payload.get("tenant_id")
        app_id = payload.get("app_id")
        roles = payload.get("roles", [])

        # Verify token type (should be "access")
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type: expected 'access', got '{token_type}'",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return Principal(
            principal_id=principal_id,
            tenant_id=tenant_id,
            app_id=app_id,
            roles=roles,
        )

    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_principal_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> Principal | None:
    """
    Optional authentication - returns None if no token provided.

    Useful for endpoints that work both authenticated and anonymous.

    Returns:
        Principal object if valid token provided, None otherwise
    """
    if credentials is None:
        return None

    try:
        return await get_current_principal(credentials)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.

    Args:
        required_role: Role name that the principal must have

    Returns:
        Dependency function that checks for the role

    Usage:
        @router.post("/admin/action")
        async def admin_action(
            principal: Principal = Depends(require_role("admin"))
        ):
            return {"message": "Admin action performed"}
    """

    async def check_role(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires '{required_role}' role",
            )
        return principal

    return check_role


def require_any_role(*required_roles: str):
    """
    Dependency factory requiring at least one of the specified roles.

    Args:
        required_roles: Role names (principal must have at least one)

    Usage:
        @router.post("/moderator-action")
        async def mod_action(
            principal: Principal = Depends(require_any_role("admin", "moderator"))
        ):
            return {"message": "Moderator action performed"}
    """

    async def check_roles(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_any_role(*required_roles):
            roles_str = "', '".join(required_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions: requires one of ['{roles_str}'] roles",
            )
        return principal

    return check_roles


# ============================================================================
# API Key Authentication
# ============================================================================

async def get_principal_from_api_key(
    api_key: str | None = Depends(api_key_header),
    request: Request = None,
) -> Principal | None:
    """
    Authenticate using API key from X-API-Key header.

    Args:
        api_key: API key from header
        request: FastAPI request (for client IP)

    Returns:
        Principal object if valid API key, None otherwise
    """
    if not api_key:
        return None

    try:
        from .api_keys import get_api_key_manager

        manager = get_api_key_manager()

        # Get client IP for whitelist check
        client_ip = None
        if request:
            client_ip = request.client.host if request.client else None

        # Validate API key
        api_key_obj = await manager.validate_key(
            plaintext_key=api_key,
            client_ip=client_ip
        )

        if not api_key_obj:
            return None

        # Create principal from API key
        # API keys use their name as principal_id
        return Principal(
            principal_id=f"apikey:{api_key_obj.id}",
            tenant_id=None,
            app_id=api_key_obj.name,
            roles=["api_key"] + api_key_obj.scopes,  # Add api_key role + scopes as roles
        )

    except Exception as e:
        # Log error but don't expose details
        from loguru import logger
        logger.error(f"API key validation error: {e}")
        return None


async def get_current_principal_or_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    api_key: str | None = Depends(api_key_header),
    request: Request = None,
) -> Principal:
    """
    Dependency for authentication via JWT or API key.

    Tries JWT first (Bearer token), then API key (X-API-Key header).

    Args:
        credentials: HTTP Authorization header with Bearer token
        api_key: API key from X-API-Key header
        request: FastAPI request

    Returns:
        Principal object with user information

    Raises:
        HTTPException: 401 if neither authentication method succeeds

    Usage:
        @router.get("/protected")
        async def protected_route(
            principal: Principal = Depends(get_current_principal_or_api_key)
        ):
            return {"user_id": principal.principal_id}
    """
    # Try JWT authentication first
    if credentials:
        try:
            return await get_current_principal(credentials)
        except HTTPException:
            pass  # Fall through to API key

    # Try API key authentication
    if api_key:
        principal = await get_principal_from_api_key(api_key, request)
        if principal:
            return principal

    # Neither authentication method succeeded
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required: provide Bearer token or X-API-Key header",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_principal_or_api_key_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    api_key: str | None = Depends(api_key_header),
    request: Request = None,
) -> Principal | None:
    """
    Optional authentication via JWT or API key.

    Returns None if no authentication provided.

    Returns:
        Principal object if authenticated, None otherwise
    """
    try:
        return await get_current_principal_or_api_key(credentials, api_key, request)
    except HTTPException:
        return None


def require_scope(required_scope: str):
    """
    Dependency factory for scope-based access control (API keys).

    Args:
        required_scope: Scope that the principal must have

    Returns:
        Dependency function that checks for the scope

    Usage:
        @router.get("/missions")
        async def list_missions(
            principal: Principal = Depends(require_scope("missions:read"))
        ):
            return {"missions": [...]}
    """

    async def check_scope(
        principal: Principal = Depends(get_current_principal_or_api_key)
    ) -> Principal:
        # Check if principal has the required scope
        # Scopes are stored in roles list for API keys
        if not principal.has_role(required_scope):
            # Check for wildcard scopes
            resource = required_scope.split(":")[0]
            wildcard_scope = f"{resource}:*"

            if not principal.has_role(wildcard_scope) and not principal.has_role("*:*"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions: requires '{required_scope}' scope",
                )

        return principal

    return check_scope
