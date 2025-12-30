"""
Authentication API Endpoints

Provides JWT-based authentication with login, token management, and user info.
"""

from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.core.security import (
    User,
    Token,
    Principal,
    UserRole,
    authenticate_user,
    create_access_token,
    get_current_principal,
    get_current_active_principal,
    require_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    USERS_DB,
    get_password_hash,
)


router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ============================================================================
# Request/Response Models
# ============================================================================

class LoginRequest(BaseModel):
    """Login request with username and password"""
    username: str
    password: str


class UserInfo(BaseModel):
    """Current user information"""
    username: str
    email: str | None
    full_name: str | None
    roles: List[str]
    is_admin: bool


class CreateUserRequest(BaseModel):
    """Request to create a new user"""
    username: str
    password: str
    email: str | None = None
    full_name: str | None = None
    roles: List[str] = []


class UpdateUserRequest(BaseModel):
    """Request to update user"""
    email: str | None = None
    full_name: str | None = None
    roles: List[str] | None = None
    disabled: bool | None = None


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authenticate user and return JWT access token.

    Default users:
    - username: admin, password: password (roles: admin, operator, viewer)
    - username: operator, password: password (roles: operator, viewer)
    - username: viewer, password: password (roles: viewer)
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "email": user.email,
            "roles": user.roles,
        },
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
    )


@router.post("/login/json", response_model=Token)
async def login_json(request: LoginRequest):
    """
    Authenticate user with JSON request body.

    Alternative to OAuth2 password flow for frontend applications.
    """
    user = authenticate_user(request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "email": user.email,
            "roles": user.roles,
        },
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
    principal: Principal = Depends(get_current_active_principal),
):
    """
    Get current authenticated user information.

    Requires valid JWT token.
    """
    from app.core.security import get_user

    user = get_user(principal.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserInfo(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        roles=user.roles,
        is_admin=principal.is_admin(),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    principal: Principal = Depends(get_current_active_principal),
):
    """
    Refresh JWT access token.

    Returns a new token with extended expiration.
    """
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": principal.username,
            "email": principal.email,
            "roles": principal.roles,
        },
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ============================================================================
# User Management Endpoints (Admin Only)
# ============================================================================

@router.get("/users", response_model=List[User])
async def list_users(
    _principal: Principal = Depends(require_admin),
):
    """
    List all users (admin only).

    Returns user information without passwords.
    """
    users = []
    for user in USERS_DB.values():
        users.append(User(
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            roles=user.roles,
        ))
    return users


@router.post("/users", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    _principal: Principal = Depends(require_admin),
):
    """
    Create a new user (admin only).

    Password is hashed before storage.
    """
    from app.core.security import UserInDB

    if request.username in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    new_user = UserInDB(
        username=request.username,
        email=request.email,
        full_name=request.full_name,
        disabled=False,
        roles=request.roles,
        hashed_password=get_password_hash(request.password),
    )

    USERS_DB[request.username] = new_user

    return User(
        username=new_user.username,
        email=new_user.email,
        full_name=new_user.full_name,
        disabled=new_user.disabled,
        roles=new_user.roles,
    )


@router.get("/users/{username}", response_model=User)
async def get_user_by_username(
    username: str,
    _principal: Principal = Depends(require_admin),
):
    """
    Get user by username (admin only).
    """
    from app.core.security import get_user

    user = get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )

    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        roles=user.roles,
    )


@router.put("/users/{username}", response_model=User)
async def update_user(
    username: str,
    request: UpdateUserRequest,
    _principal: Principal = Depends(require_admin),
):
    """
    Update user information (admin only).

    Password cannot be updated through this endpoint.
    """
    if username not in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )

    user = USERS_DB[username]

    # Update fields
    if request.email is not None:
        user.email = request.email
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.roles is not None:
        user.roles = request.roles
    if request.disabled is not None:
        user.disabled = request.disabled

    return User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        disabled=user.disabled,
        roles=user.roles,
    )


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    username: str,
    principal: Principal = Depends(require_admin),
):
    """
    Delete user (admin only).

    Cannot delete yourself or the last admin user.
    """
    if username not in USERS_DB:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )

    # Prevent self-deletion
    if username == principal.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    # Prevent deleting last admin
    user = USERS_DB[username]
    if "admin" in user.roles:
        admin_count = sum(1 for u in USERS_DB.values() if "admin" in u.roles)
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin user",
            )

    del USERS_DB[username]


# ============================================================================
# Role Information Endpoints
# ============================================================================

@router.get("/roles")
async def list_roles():
    """
    List available user roles.

    Returns role definitions and permissions.
    """
    return {
        "roles": [
            {
                "name": "admin",
                "display_name": "Administrator",
                "description": "Full system access including user management",
                "permissions": ["all"],
            },
            {
                "name": "operator",
                "display_name": "Operator",
                "description": "Can perform operations and deployments",
                "permissions": ["read", "write", "execute", "deploy"],
            },
            {
                "name": "viewer",
                "display_name": "Viewer",
                "description": "Read-only access to system",
                "permissions": ["read"],
            },
            {
                "name": "guest",
                "display_name": "Guest",
                "description": "Limited access (anonymous users)",
                "permissions": ["read_public"],
            },
        ]
    }
