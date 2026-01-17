"""
Security Module - JWT Authentication and RBAC

Provides JWT token generation/validation and role-based access control.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, List
from enum import Enum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel


# ============================================================================
# Configuration
# ============================================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "brain-dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "30"))

security_scheme = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================================
# Models
# ============================================================================

class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"
    GUEST = "guest"


class Principal:
    """Principal represents an authenticated user with roles and permissions"""

    def __init__(
        self,
        principal_id: str,
        username: str | None = None,
        email: str | None = None,
        roles: list[str] | None = None,
        tenant_id: str | None = None,
        app_id: str | None = None,
    ):
        self.principal_id = principal_id
        self.username = username or principal_id
        self.email = email
        self.roles = roles or []
        self.tenant_id = tenant_id
        self.app_id = app_id

    def has_role(self, role: str | UserRole) -> bool:
        """Check if principal has a specific role"""
        role_str = role.value if isinstance(role, UserRole) else role
        return role_str in self.roles

    def has_any_role(self, roles: List[str | UserRole]) -> bool:
        """Check if principal has any of the specified roles"""
        return any(self.has_role(role) for role in roles)

    def is_admin(self) -> bool:
        """Check if principal is an admin"""
        return self.has_role(UserRole.ADMIN)


class User(BaseModel):
    """User model for authentication"""
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: bool = False
    roles: List[str] = []


class UserInDB(User):
    """User model with hashed password"""
    hashed_password: str


class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """JWT token payload data"""
    username: str
    email: Optional[str] = None
    roles: List[str] = []


# ============================================================================
# In-Memory User Storage (Replace with Database in Production)
# ============================================================================

# Load passwords from environment variables (Security Fix - Task 2.1)
ADMIN_PASSWORD = os.getenv("BRAIN_ADMIN_PASSWORD", "password")  # Default for dev only
OPERATOR_PASSWORD = os.getenv("BRAIN_OPERATOR_PASSWORD", "password")  # Default for dev only
VIEWER_PASSWORD = os.getenv("BRAIN_VIEWER_PASSWORD", "password")  # Default for dev only

# Production Security Check: Fail fast if default passwords are used in production
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if ENVIRONMENT == "production":
    if ADMIN_PASSWORD == "password":
        raise RuntimeError(
            "FATAL SECURITY ERROR: BRAIN_ADMIN_PASSWORD must be set in production! "
            "Default password is not allowed. Set BRAIN_ADMIN_PASSWORD in .env file."
        )
    if OPERATOR_PASSWORD == "password":
        raise RuntimeError(
            "FATAL SECURITY ERROR: BRAIN_OPERATOR_PASSWORD must be set in production! "
            "Default password is not allowed. Set BRAIN_OPERATOR_PASSWORD in .env file."
        )

# User database with environment-based passwords
USERS_DB: Dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        email="admin@brain.local",
        full_name="Administrator",
        disabled=False,
        roles=["admin", "operator", "viewer"],
        hashed_password=pwd_context.hash(ADMIN_PASSWORD),
    ),
    "operator": UserInDB(
        username="operator",
        email="operator@brain.local",
        full_name="Operator User",
        disabled=False,
        roles=["operator", "viewer"],
        hashed_password=pwd_context.hash(OPERATOR_PASSWORD),
    ),
    "viewer": UserInDB(
        username="viewer",
        email="viewer@brain.local",
        full_name="Viewer User",
        disabled=False,
        roles=["viewer"],
        hashed_password=pwd_context.hash(VIEWER_PASSWORD),
    ),
}


# ============================================================================
# Password Hashing
# ============================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storage"""
    return pwd_context.hash(password)


# ============================================================================
# User Operations
# ============================================================================

def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database"""
    return USERS_DB.get(username)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate user with username and password"""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# ============================================================================
# JWT Token Operations
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None

        return TokenData(
            username=username,
            email=payload.get("email"),
            roles=payload.get("roles", []),
        )
    except JWTError:
        return None


# ============================================================================
# Authentication Dependencies
# ============================================================================

async def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> Principal:
    """
    Get current authenticated principal from JWT token.

    For development: allows anonymous access if no credentials provided.
    For production: should require authentication.
    """
    # Allow anonymous access in development
    if credentials is None:
        return Principal(
            principal_id="anonymous",
            username="anonymous",
            roles=["guest"],
        )

    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode and validate token
    token_data = decode_access_token(token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = get_user(token_data.username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return Principal(
        principal_id=user.username,
        username=user.username,
        email=user.email,
        roles=user.roles,
    )


async def get_current_active_principal(
    principal: Principal = Depends(get_current_principal),
) -> Principal:
    """Get current active principal (non-anonymous)"""
    if principal.principal_id == "anonymous":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


# ============================================================================
# RBAC Dependencies
# ============================================================================

def require_role(required_role: UserRole | str):
    """
    Dependency factory for requiring specific role.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role(UserRole.ADMIN))])
    """
    async def check_role(principal: Principal = Depends(get_current_active_principal)):
        if not principal.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return principal
    return check_role


def require_any_role(required_roles: List[UserRole | str]):
    """
    Dependency factory for requiring any of the specified roles.

    Usage:
        @router.get("/protected", dependencies=[Depends(require_any_role([UserRole.ADMIN, UserRole.OPERATOR]))])
    """
    async def check_roles(principal: Principal = Depends(get_current_active_principal)):
        if not principal.has_any_role(required_roles):
            roles_str = ", ".join([str(r) for r in required_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {roles_str}",
            )
        return principal
    return check_roles


# ============================================================================
# Admin-Only Dependency
# ============================================================================

async def require_admin(
    principal: Principal = Depends(get_current_active_principal),
) -> Principal:
    """Require admin role"""
    if not principal.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return principal
