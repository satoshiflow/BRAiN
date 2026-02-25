"""
Authentication Schemas

Pydantic models for authentication and user management.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


# ============================================================================
# Login
# ============================================================================

class LoginRequest(BaseModel):
    """Login request payload"""
    email: EmailStr
    password: str = Field(..., min_length=8)


class LoginResponse(BaseModel):
    """Login response"""
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


# ============================================================================
# Registration
# ============================================================================

class RegisterRequest(BaseModel):
    """Registration request payload"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.replace('_', '').replace('-', '').isalnum(), 'Username must be alphanumeric'
        return v


# ============================================================================
# First-Time Admin Setup
# ============================================================================

class FirstTimeSetupRequest(BaseModel):
    """First-time admin setup request"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


# ============================================================================
# Invitation
# ============================================================================

class InvitationCreate(BaseModel):
    """Create invitation request"""
    email: EmailStr
    role: UserRole = UserRole.OPERATOR


class InvitationResponse(BaseModel):
    """Invitation response"""
    id: UUID
    email: str
    role: UserRole
    token: str
    expires_at: datetime
    invitation_url: str


# ============================================================================
# Token Pair & Refresh
# ============================================================================

class TokenPair(BaseModel):
    """Access token and refresh token pair"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token expiration in seconds


class RefreshRequest(BaseModel):
    """Token refresh request"""
    refresh_token: str


class LogoutRequest(BaseModel):
    """Logout request"""
    refresh_token: str


class TokenIntrospectionResponse(BaseModel):
    """Token introspection response (RFC 7662)"""
    active: bool
    sub: Optional[str] = None
    scope: Optional[str] = None
    client_id: Optional[str] = None
    token_type: Optional[str] = None
    exp: Optional[int] = None
    iat: Optional[int] = None
    nbf: Optional[int] = None
    aud: Optional[str] = None
    iss: Optional[str] = None
    jti: Optional[str] = None


# ============================================================================
# Service Account Token
# ============================================================================

class ServiceTokenRequest(BaseModel):
    """Service token request (Client Credentials Grant)"""
    client_id: str
    client_secret: str
    scope: Optional[str] = None  # Space-separated scopes


class ServiceTokenResponse(BaseModel):
    """Service token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: Optional[str] = None


# ============================================================================
# Agent Token
# ============================================================================

class AgentTokenRequest(BaseModel):
    """Agent token request"""
    agent_id: str
    parent_agent_id: Optional[str] = None
    scope: Optional[str] = None  # Space-separated scopes
    capabilities: Optional[List[str]] = None


class AgentTokenResponse(BaseModel):
    """Agent token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    scope: str
    agent_id: str


# ============================================================================
# JWKS
# ============================================================================

class JWK(BaseModel):
    """JSON Web Key"""
    kty: str
    kid: str
    use: str
    alg: str
    n: str  # RSA modulus (base64url-encoded)
    e: str  # RSA exponent (base64url-encoded)


class JWKSResponse(BaseModel):
    """JSON Web Key Set response"""
    keys: List[JWK]


# ============================================================================
# Device Info
# ============================================================================

class DeviceInfo(BaseModel):
    """Device information for token binding"""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_fingerprint: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================================
# User Response
# ============================================================================

class UserResponse(BaseModel):
    """User data response"""
    id: UUID
    email: str
    username: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        from_attributes = True
