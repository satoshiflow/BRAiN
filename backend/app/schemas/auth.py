"""
Authentication Schemas

Pydantic models for authentication and user management.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from datetime import datetime
from typing import Optional
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
