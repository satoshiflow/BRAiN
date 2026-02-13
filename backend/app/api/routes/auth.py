"""
Auth Router - Test endpoints for JWT authentication

Provides:
- /api/auth/me - Get current principal info
- /api/auth/test/protected - Test protected endpoint
- /api/auth/test/role/{role} - Test role-based access
- /api/auth/test/scope/{scope} - Test scope-based access
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth_deps import (
    Principal,
    get_current_principal,
    require_auth,
    require_role,
    require_scope,
    require_admin,
    require_human,
    require_agent,
    SystemRole,
    SystemScope,
)
from app.core.jwt_middleware import JWTBearer, TokenPayload

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================================================
# Response Models
# ============================================================================

class PrincipalInfo(BaseModel):
    """Principal information response"""
    principal_id: str
    principal_type: str
    email: Optional[str]
    name: Optional[str]
    roles: list[str]
    scopes: list[str]
    tenant_id: Optional[str]
    agent_id: Optional[str]
    parent_agent_id: Optional[str]
    is_authenticated: bool
    is_human: bool
    is_agent: bool
    is_anonymous: bool


class TokenValidationResponse(BaseModel):
    """Token validation test response"""
    valid: bool
    message: str
    principal: Optional[PrincipalInfo] = None
    error: Optional[str] = None


class AccessTestResponse(BaseModel):
    """Access test response"""
    success: bool
    message: str
    principal_id: str
    required_check: str
    your_roles: list[str]
    your_scopes: list[str]


# ============================================================================
# Auth Info Endpoints
# ============================================================================

@router.get("/me", response_model=PrincipalInfo)
async def get_me(
    principal: Principal = Depends(get_current_principal),
) -> PrincipalInfo:
    """
    Get current authenticated principal information.
    
    Returns information about the currently authenticated user or agent.
    Works with both valid tokens and anonymous requests.
    """
    return PrincipalInfo(
        principal_id=principal.principal_id,
        principal_type=principal.principal_type.value,
        email=principal.email,
        name=principal.name,
        roles=principal.roles,
        scopes=principal.scopes,
        tenant_id=principal.tenant_id,
        agent_id=principal.agent_id,
        parent_agent_id=principal.parent_agent_id,
        is_authenticated=not principal.is_anonymous,
        is_human=principal.is_human,
        is_agent=principal.is_agent,
        is_anonymous=principal.is_anonymous,
    )


@router.get("/me/protected", response_model=PrincipalInfo)
async def get_me_protected(
    principal: Principal = Depends(require_auth),
) -> PrincipalInfo:
    """
    Get current principal info (authentication required).
    
    Same as /me but requires valid authentication.
    """
    return PrincipalInfo(
        principal_id=principal.principal_id,
        principal_type=principal.principal_type.value,
        email=principal.email,
        name=principal.name,
        roles=principal.roles,
        scopes=principal.scopes,
        tenant_id=principal.tenant_id,
        agent_id=principal.agent_id,
        parent_agent_id=principal.parent_agent_id,
        is_authenticated=True,
        is_human=principal.is_human,
        is_agent=principal.is_agent,
        is_anonymous=False,
    )


# ============================================================================
# Token Validation Test
# ============================================================================

@router.post("/test/validate", response_model=TokenValidationResponse)
async def test_token_validation(
    token_payload: Optional[TokenPayload] = Depends(JWTBearer(auto_error=False)),
) -> TokenValidationResponse:
    """
    Test token validation without requiring authentication.
    
    Returns whether the provided token is valid and its claims.
    """
    if token_payload is None:
        return TokenValidationResponse(
            valid=False,
            message="No valid token provided",
            error="Missing or invalid Authorization header",
        )
    
    return TokenValidationResponse(
        valid=True,
        message="Token is valid",
        principal=PrincipalInfo(
            principal_id=token_payload.sub,
            principal_type=token_payload.token_type,
            email=token_payload.email,
            name=token_payload.name,
            roles=token_payload.roles,
            scopes=token_payload.scope,
            tenant_id=token_payload.tenant_id,
            agent_id=token_payload.agent_id,
            parent_agent_id=token_payload.parent_agent_id,
            is_authenticated=True,
            is_human=token_payload.token_type == "human",
            is_agent=token_payload.token_type == "agent",
            is_anonymous=False,
        ),
    )


# ============================================================================
# Role-Based Access Tests
# ============================================================================

@router.get("/test/role/admin", response_model=AccessTestResponse)
async def test_admin_access(
    principal: Principal = Depends(require_admin),
) -> AccessTestResponse:
    """
    Test admin role access.
    
    Requires 'admin' or 'SYSTEM_ADMIN' role.
    """
    return AccessTestResponse(
        success=True,
        message="You have admin access!",
        principal_id=principal.principal_id,
        required_check="admin role",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


@router.get("/test/role/operator", response_model=AccessTestResponse)
async def test_operator_access(
    principal: Principal = Depends(require_role("admin", "operator", "SYSTEM_ADMIN")),
) -> AccessTestResponse:
    """
    Test operator role access.
    
    Requires 'admin', 'operator', or 'SYSTEM_ADMIN' role.
    """
    return AccessTestResponse(
        success=True,
        message="You have operator access!",
        principal_id=principal.principal_id,
        required_check="operator role",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


@router.get("/test/role/viewer", response_model=AccessTestResponse)
async def test_viewer_access(
    principal: Principal = Depends(require_role("admin", "operator", "viewer", "SYSTEM_ADMIN")),
) -> AccessTestResponse:
    """
    Test viewer role access.
    
    Requires 'admin', 'operator', 'viewer', or 'SYSTEM_ADMIN' role.
    """
    return AccessTestResponse(
        success=True,
        message="You have viewer access!",
        principal_id=principal.principal_id,
        required_check="viewer role",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


@router.get("/test/role/custom/{role}", response_model=AccessTestResponse)
async def test_custom_role(
    role: str,
    principal: Principal = Depends(require_auth),
) -> AccessTestResponse:
    """
    Test specific role access.
    
    Provide a role name to check if you have it.
    """
    if principal.has_role(role):
        return AccessTestResponse(
            success=True,
            message=f"You have the '{role}' role!",
            principal_id=principal.principal_id,
            required_check=f"{role} role",
            your_roles=principal.roles,
            your_scopes=principal.scopes,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have the '{role}' role. Your roles: {principal.roles}",
        )


# ============================================================================
# Scope-Based Access Tests
# ============================================================================

@router.get("/test/scope/read", response_model=AccessTestResponse)
async def test_read_scope(
    principal: Principal = Depends(require_scope(SystemScope.READ)),
) -> AccessTestResponse:
    """
    Test read scope access.
    
    Requires 'read' scope.
    """
    return AccessTestResponse(
        success=True,
        message="You have read access!",
        principal_id=principal.principal_id,
        required_check="read scope",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


@router.get("/test/scope/write", response_model=AccessTestResponse)
async def test_write_scope(
    principal: Principal = Depends(require_scope(SystemScope.WRITE)),
) -> AccessTestResponse:
    """
    Test write scope access.
    
    Requires 'write' scope.
    """
    return AccessTestResponse(
        success=True,
        message="You have write access!",
        principal_id=principal.principal_id,
        required_check="write scope",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


@router.get("/test/scope/admin", response_model=AccessTestResponse)
async def test_admin_scope(
    principal: Principal = Depends(require_scope(SystemScope.ADMIN)),
) -> AccessTestResponse:
    """
    Test admin scope access.
    
    Requires 'admin' scope.
    """
    return AccessTestResponse(
        success=True,
        message="You have admin scope access!",
        principal_id=principal.principal_id,
        required_check="admin scope",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


@router.get("/test/scope/custom/{scope}", response_model=AccessTestResponse)
async def test_custom_scope(
    scope: str,
    principal: Principal = Depends(require_auth),
) -> AccessTestResponse:
    """
    Test specific scope access.
    
    Provide a scope name to check if you have it.
    """
    if principal.has_scope(scope):
        return AccessTestResponse(
            success=True,
            message=f"You have the '{scope}' scope!",
            principal_id=principal.principal_id,
            required_check=f"{scope} scope",
            your_roles=principal.roles,
            your_scopes=principal.scopes,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You don't have the '{scope}' scope. Your scopes: {principal.scopes}",
        )


# ============================================================================
# Principal Type Tests
# ============================================================================

@router.get("/test/type/human", response_model=AccessTestResponse)
async def test_human_access(
    principal: Principal = Depends(require_human),
) -> AccessTestResponse:
    """
    Test human-only access.
    
    Only human users can access this endpoint.
    """
    return AccessTestResponse(
        success=True,
        message="You are a human user!",
        principal_id=principal.principal_id,
        required_check="human principal type",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


@router.get("/test/type/agent", response_model=AccessTestResponse)
async def test_agent_access(
    principal: Principal = Depends(require_agent),
) -> AccessTestResponse:
    """
    Test agent-only access.
    
    Only agents can access this endpoint.
    """
    return AccessTestResponse(
        success=True,
        message="You are an agent!",
        principal_id=principal.principal_id,
        required_check="agent principal type",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


# ============================================================================
# Combined Tests
# ============================================================================

@router.post("/test/combined", response_model=AccessTestResponse)
async def test_combined_access(
    principal: Principal = Depends(require_auth),
) -> AccessTestResponse:
    """
    Test combined role and scope checks programmatically.
    
    This endpoint accepts any authenticated user and returns
    information about their access levels.
    """
    checks = []
    
    if principal.has_role("admin"):
        checks.append("admin role")
    if principal.has_scope("write"):
        checks.append("write scope")
    if principal.has_scope("admin"):
        checks.append("admin scope")
    if principal.is_human:
        checks.append("human type")
    if principal.is_agent:
        checks.append("agent type")
    
    return AccessTestResponse(
        success=True,
        message=f"Passed checks: {', '.join(checks) if checks else 'none specific'}",
        principal_id=principal.principal_id,
        required_check="authenticated",
        your_roles=principal.roles,
        your_scopes=principal.scopes,
    )


# ============================================================================
# Public Test Endpoints (No auth required)
# ============================================================================

@router.get("/test/public")
async def test_public_access() -> dict:
    """
    Public test endpoint - no authentication required.
    
    Useful for testing connectivity without a token.
    """
    return {
        "message": "This is a public endpoint",
        "auth_required": False,
        "hint": "Try /api/auth/me with a Bearer token",
    }


@router.get("/health")
async def auth_health_check() -> dict:
    """
    Auth module health check.
    
    Returns basic status of the auth system.
    """
    return {
        "status": "ok",
        "module": "auth",
        "features": [
            "jwt_validation",
            "role_based_access",
            "scope_based_access",
            "human_agent_tokens",
        ],
    }
