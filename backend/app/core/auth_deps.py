"""
Auth Dependencies - Role and scope-based access control for BRAiN

Provides:
- get_current_principal() - Extract principal from JWT token
- require_role() - Role-based access control
- require_scope() - Scope-based access control
- Support for both Human and Agent tokens
"""

from __future__ import annotations

import logging
from typing import Optional, List, Union, Callable
from enum import Enum
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.core.jwt_middleware import (
    JWTBearer,
    TokenPayload,
    get_jwt_validator,
    optional_jwt_bearer,
)
from app.core.security import Principal as LegacyPrincipal

logger = logging.getLogger(__name__)


class PrincipalType(str, Enum):
    """Types of principals that can authenticate"""
    HUMAN = "human"
    AGENT = "agent"
    SERVICE = "service"
    ANONYMOUS = "anonymous"


class Principal:
    """
    Enhanced Principal class that wraps TokenPayload.
    
    Represents an authenticated entity (human user or agent) with
    their roles, scopes, and metadata.
    """
    
    def __init__(
        self,
        principal_id: str,
        principal_type: PrincipalType,
        email: Optional[str] = None,
        name: Optional[str] = None,
        roles: Optional[List[str]] = None,
        scopes: Optional[List[str]] = None,
        tenant_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        token_payload: Optional[TokenPayload] = None,
    ):
        self.principal_id = principal_id
        self.principal_type = principal_type
        self.email = email
        self.name = name
        self.roles = roles or []
        self.scopes = scopes or []
        self.tenant_id = tenant_id
        self.agent_id = agent_id
        self.parent_agent_id = parent_agent_id
        self.token_payload = token_payload
    
    @property
    def is_human(self) -> bool:
        """Check if principal is a human user"""
        return self.principal_type == PrincipalType.HUMAN
    
    @property
    def is_agent(self) -> bool:
        """Check if principal is an agent"""
        return self.principal_type == PrincipalType.AGENT
    
    @property
    def is_service(self) -> bool:
        """Check if principal is a service account"""
        return self.principal_type == PrincipalType.SERVICE
    
    @property
    def is_anonymous(self) -> bool:
        """Check if principal is anonymous"""
        return self.principal_type == PrincipalType.ANONYMOUS
    
    def has_role(self, role: str) -> bool:
        """Check if principal has a specific role"""
        return role in self.roles
    
    def has_any_role(self, roles: List[str]) -> bool:
        """Check if principal has any of the specified roles"""
        return any(r in self.roles for r in roles)
    
    def has_all_roles(self, roles: List[str]) -> bool:
        """Check if principal has all of the specified roles"""
        return all(r in self.roles for r in roles)
    
    def has_scope(self, scope: str) -> bool:
        """Check if principal has a specific scope"""
        return scope in self.scopes
    
    def has_any_scope(self, scopes: List[str]) -> bool:
        """Check if principal has any of the specified scopes"""
        return any(s in self.scopes for s in scopes)
    
    def has_all_scopes(self, scopes: List[str]) -> bool:
        """Check if principal has all of the specified scopes"""
        return all(s in self.scopes for s in scopes)
    
    def require_tenant(self, tenant_id: str) -> bool:
        """Check if principal belongs to a specific tenant"""
        if not self.tenant_id:
            return False
        return self.tenant_id == tenant_id
    
    def to_dict(self) -> dict:
        """Convert principal to dictionary"""
        return {
            "principal_id": self.principal_id,
            "principal_type": self.principal_type.value,
            "email": self.email,
            "name": self.name,
            "roles": self.roles,
            "scopes": self.scopes,
            "tenant_id": self.tenant_id,
            "agent_id": self.agent_id,
            "parent_agent_id": self.parent_agent_id,
        }
    
    @classmethod
    def from_token_payload(cls, payload: TokenPayload) -> "Principal":
        """Create Principal from TokenPayload"""
        principal_type = PrincipalType(payload.token_type)
        
        return cls(
            principal_id=payload.sub,
            principal_type=principal_type,
            email=payload.email,
            name=payload.name,
            roles=payload.roles,
            scopes=payload.scope,
            tenant_id=payload.tenant_id,
            agent_id=payload.agent_id,
            parent_agent_id=payload.parent_agent_id,
            token_payload=payload,
        )
    
    @classmethod
    def anonymous(cls) -> "Principal":
        """Create an anonymous principal"""
        return cls(
            principal_id="anonymous",
            principal_type=PrincipalType.ANONYMOUS,
            roles=["anonymous"],
            scopes=[],
        )


# ============================================================================
# Core Dependencies
# ============================================================================

async def get_current_principal(
    token_payload: Optional[TokenPayload] = Depends(optional_jwt_bearer),
) -> Principal:
    """
    Get the current authenticated principal from JWT token.
    
    Returns anonymous principal if no valid token provided.
    Use require_auth() to enforce authentication.
    
    Usage:
        @router.get("/profile")
        async def get_profile(principal: Principal = Depends(get_current_principal)):
            if principal.is_anonymous:
                raise HTTPException(401, "Authentication required")
            return {"user": principal.principal_id}
    """
    if token_payload is None:
        return Principal.anonymous()
    
    return Principal.from_token_payload(token_payload)


async def require_auth(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """
    Require authentication - raises 401 if not authenticated.
    
    Usage:
        @router.get("/private")
        async def private_endpoint(principal: Principal = Depends(require_auth)):
            return {"message": f"Hello {principal.name}"}
    """
    if principal.is_anonymous:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


async def require_human(
    principal: Principal = Depends(require_auth),
) -> Principal:
    """
    Require human authentication (not agent tokens).
    
    Usage:
        @router.post("/admin-action")
        async def admin_action(principal: Principal = Depends(require_human)):
            # Only humans can access this
            pass
    """
    if not principal.is_human:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Human authentication required",
        )
    return principal


async def require_agent(
    principal: Principal = Depends(require_auth),
) -> Principal:
    """
    Require agent authentication (not human tokens).
    
    Usage:
        @router.post("/agent-callback")
        async def agent_callback(principal: Principal = Depends(require_agent)):
            # Only agents can access this
            pass
    """
    if not principal.is_agent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent authentication required",
        )
    return principal


# ============================================================================
# Role-Based Access Control (RBAC)
# ============================================================================

class SystemRole(str, Enum):
    """System-defined roles"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    AGENT = "agent"
    SERVICE = "service"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"  # Genesis API compatibility


def require_role(
    *roles: str,
    allow_anonymous: bool = False,
) -> Callable:
    """
    Dependency factory for requiring specific roles.
    
    Args:
        *roles: Required roles (any one of these is sufficient)
        allow_anonymous: If True, allows anonymous access
    
    Usage:
        @router.get("/admin-only")
        async def admin_only(principal: Principal = Depends(require_role("admin"))):
            pass
        
        @router.get("/manager-plus")
        async def manager_plus(principal: Principal = Depends(require_role("admin", "manager"))):
            pass
    """
    role_list = list(roles)
    
    async def check_role(
        principal: Principal = Depends(get_current_principal if allow_anonymous else require_auth),
    ) -> Principal:
        if principal.is_anonymous and not allow_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not principal.has_any_role(role_list):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: one of {', '.join(role_list)}",
            )
        
        return principal
    
    return check_role


def require_all_roles(
    *roles: str,
    allow_anonymous: bool = False,
) -> Callable:
    """
    Dependency factory for requiring ALL specified roles.
    
    Usage:
        @router.get("/super-admin")
        async def super_admin(principal: Principal = Depends(require_all_roles("admin", "superuser"))):
            pass
    """
    role_list = list(roles)
    
    async def check_roles(
        principal: Principal = Depends(get_current_principal if allow_anonymous else require_auth),
    ) -> Principal:
        if principal.is_anonymous and not allow_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not principal.has_all_roles(role_list):
            missing = [r for r in role_list if not principal.has_role(r)]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required roles: {', '.join(missing)}",
            )
        
        return principal
    
    return check_roles


# Convenience shortcuts
require_admin = require_role(SystemRole.ADMIN, SystemRole.SYSTEM_ADMIN)
require_operator = require_role(SystemRole.ADMIN, SystemRole.OPERATOR, SystemRole.SYSTEM_ADMIN)
require_viewer = require_role(SystemRole.ADMIN, SystemRole.OPERATOR, SystemRole.VIEWER, SystemRole.SYSTEM_ADMIN)


# ============================================================================
# Scope-Based Access Control
# ============================================================================

class SystemScope(str, Enum):
    """System-defined OAuth scopes"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    AGENTS_READ = "agents:read"
    AGENTS_WRITE = "agents:write"
    AGENTS_DELETE = "agents:delete"
    MISSIONS_READ = "missions:read"
    MISSIONS_WRITE = "missions:write"
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"


def require_scope(
    *scopes: str,
    allow_anonymous: bool = False,
) -> Callable:
    """
    Dependency factory for requiring specific OAuth scopes.
    
    Args:
        *scopes: Required scopes (any one of these is sufficient)
        allow_anonymous: If True, allows anonymous access
    
    Usage:
        @router.get("/resources")
        async def list_resources(principal: Principal = Depends(require_scope("read"))):
            pass
        
        @router.post("/resources")
        async def create_resource(principal: Principal = Depends(require_scope("write"))):
            pass
    """
    scope_list = list(scopes)
    
    async def check_scope(
        principal: Principal = Depends(get_current_principal if allow_anonymous else require_auth),
    ) -> Principal:
        if principal.is_anonymous and not allow_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not principal.has_any_scope(scope_list):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient scope. Required: one of {', '.join(scope_list)}",
            )
        
        return principal
    
    return check_scope


def require_all_scopes(
    *scopes: str,
    allow_anonymous: bool = False,
) -> Callable:
    """
    Dependency factory for requiring ALL specified scopes.
    
    Usage:
        @router.post("/critical-operation")
        async def critical_op(principal: Principal = Depends(require_all_scopes("write", "admin"))):
            pass
    """
    scope_list = list(scopes)
    
    async def check_scopes(
        principal: Principal = Depends(get_current_principal if allow_anonymous else require_auth),
    ) -> Principal:
        if principal.is_anonymous and not allow_anonymous:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not principal.has_all_scopes(scope_list):
            missing = [s for s in scope_list if not principal.has_scope(s)]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing)}",
            )
        
        return principal
    
    return check_scopes


# ============================================================================
# Combined RBAC + Scope Dependencies
# ============================================================================

def require_role_and_scope(
    roles: List[str],
    scopes: List[str],
    require_all_roles: bool = False,
    require_all_scopes: bool = False,
) -> Callable:
    """
    Dependency factory for requiring both roles AND scopes.
    
    Usage:
        @router.post("/admin-write")
        async def admin_write(
            principal: Principal = Depends(require_role_and_scope(
                roles=["admin"],
                scopes=["write", "admin"],
                require_all_scopes=True,
            ))
        ):
            pass
    """
    async def check_both(principal: Principal = Depends(require_auth)) -> Principal:
        # Check roles
        if require_all_roles:
            if not principal.has_all_roles(roles):
                missing = [r for r in roles if not principal.has_role(r)]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required roles: {', '.join(missing)}",
                )
        else:
            if not principal.has_any_role(roles):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required role: one of {', '.join(roles)}",
                )
        
        # Check scopes
        if require_all_scopes:
            if not principal.has_all_scopes(scopes):
                missing = [s for s in scopes if not principal.has_scope(s)]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scopes: {', '.join(missing)}",
                )
        else:
            if not principal.has_any_scope(scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Required scope: one of {', '.join(scopes)}",
                )
        
        return principal
    
    return check_both


# ============================================================================
# Tenant Isolation
# ============================================================================

def require_tenant_access(
    tenant_id_param: str = "tenant_id",
    from_path: bool = True,
    from_query: bool = False,
) -> Callable:
    """
    Dependency factory for tenant isolation.
    
    Ensures the authenticated principal can only access resources
    belonging to their tenant.
    
    Usage:
        @router.get("/tenants/{tenant_id}/resources")
        async def list_tenant_resources(
            principal: Principal = Depends(require_tenant_access()),
        ):
            pass
    """
    async def check_tenant(
        request: Request,
        principal: Principal = Depends(require_auth),
    ) -> Principal:
        # Get tenant_id from path or query
        tenant_id = None
        if from_path:
            tenant_id = request.path_params.get(tenant_id_param)
        if not tenant_id and from_query:
            tenant_id = request.query_params.get(tenant_id_param)
        
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant ID parameter '{tenant_id_param}' not found",
            )
        
        # Admin can access any tenant
        if principal.has_role(SystemRole.ADMIN):
            return principal
        
        # Check tenant match
        if principal.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this tenant",
            )
        
        return principal
    
    return check_tenant


# ============================================================================
# Agent Context
# ============================================================================

async def get_agent_context(
    principal: Principal = Depends(require_agent),
) -> dict:
    """
    Get agent context from an authenticated agent principal.
    
    Returns context about the agent including parent relationships.
    """
    return {
        "agent_id": principal.agent_id,
        "parent_agent_id": principal.parent_agent_id,
        "principal_id": principal.principal_id,
        "tenant_id": principal.tenant_id,
        "scopes": principal.scopes,
        "roles": principal.roles,
    }


# ============================================================================
# Legacy Compatibility
# ============================================================================

async def get_current_principal_legacy(
    principal: Principal = Depends(get_current_principal),
) -> LegacyPrincipal:
    """
    Convert new Principal to legacy Principal for backward compatibility.
    
    Usage in legacy code:
        from app.core.auth_deps import get_current_principal_legacy
        
        @router.get("/legacy")
        async def legacy_endpoint(
            principal: LegacyPrincipal = Depends(get_current_principal_legacy)
        ):
            pass
    """
    return LegacyPrincipal(
        principal_id=principal.principal_id,
        username=principal.name or principal.principal_id,
        email=principal.email,
        roles=principal.roles,
        tenant_id=principal.tenant_id,
    )
