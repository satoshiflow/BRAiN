"""
Authentication API Routes

FastAPI endpoints for authentication and user management.
"""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.security import create_access_token, SECRET_KEY, ALGORITHM
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest, LoginResponse, RegisterRequest, UserResponse,
    FirstTimeSetupRequest, InvitationCreate, InvitationResponse
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])

# Export both routers
__all__ = ["router", "admin_router", "get_current_user_db", "require_role_db", "require_any_role_db"]

# Security scheme for JWT
device_security = HTTPBearer(auto_error=False)


# ============================================================================
# DB-Based Authentication Dependencies
# ============================================================================

async def get_current_user_db(
    credentials: HTTPAuthorizationCredentials = Depends(device_security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token using database"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    
    # Get user from database
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


def require_role_db(required_role: UserRole):
    """Dependency factory for requiring specific role (DB-based)"""
    async def check_role(user: User = Depends(get_current_user_db)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required",
            )
        return user
    return check_role


def require_any_role_db(required_roles: List[UserRole]):
    """Dependency factory for requiring any of the specified roles (DB-based)"""
    async def check_roles(user: User = Depends(get_current_user_db)) -> User:
        if user.role not in required_roles:
            roles_str = ", ".join([r.value for r in required_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these roles required: {roles_str}",
            )
        return user
    return check_roles


@router.get("/first-time-setup")
async def check_first_time_setup(db: AsyncSession = Depends(get_db)):
    """Check if first-time setup is needed (no admin exists)"""
    is_first_time = await AuthService.check_first_time_setup(db)
    return {"needs_setup": is_first_time}


@router.post("/first-time-setup", response_model=LoginResponse)
async def first_time_setup(
    data: FirstTimeSetupRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create first admin user (only works if no admin exists)"""
    try:
        user = await AuthService.create_first_admin(db, data)

        # Generate JWT token
        token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "scope": ["read", "write", "admin"]
            }
        )

        return LoginResponse(
            access_token=token,
            user=UserResponse.from_orm(user)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""
    user = await AuthService.authenticate_user(
        db, credentials.email, credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # Generate JWT token
    scopes = ["read"]
    if user.role == UserRole.ADMIN:
        scopes = ["read", "write", "admin"]
    elif user.role == UserRole.OPERATOR:
        scopes = ["read", "write"]

    token = create_access_token(
        data={
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "scope": scopes
        }
    )

    return LoginResponse(
        access_token=token,
        user=UserResponse.from_orm(user)
    )


@router.post("/register", response_model=LoginResponse)
async def register(
    data: RegisterRequest,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Register new user with invitation token"""
    try:
        user = await AuthService.register_with_invitation(db, token, data)

        # Generate JWT token
        scopes = ["read"]
        if user.role == UserRole.ADMIN:
            scopes = ["read", "write", "admin"]
        elif user.role == UserRole.OPERATOR:
            scopes = ["read", "write"]

        token = create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value,
                "scope": scopes
            }
        )

        return LoginResponse(
            access_token=token,
            user=UserResponse.from_orm(user)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/invitations", response_model=InvitationResponse)
async def create_invitation(
    data: InvitationCreate,
    current_user: User = Depends(require_role_db(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Create invitation for new user (admin only)"""
    try:
        invitation = await AuthService.create_invitation(
            db, current_user.id, data
        )

        # Build invitation URL
        base_url = "https://control-deck.falklabs.de"  # TODO: From config
        invitation_url = f"{base_url}/auth/register?token={invitation.token}"

        return InvitationResponse(
            id=invitation.id,
            email=invitation.email,
            role=invitation.role,
            token=invitation.token,
            expires_at=invitation.expires_at,
            invitation_url=invitation_url
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_user_db),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user"""
    return UserResponse.from_orm(current_user)


@router.get("/validate-invitation")
async def validate_invitation(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Validate invitation token (public endpoint for registration page)"""
    from app.models.user import Invitation
    from datetime import datetime
    
    result = await db.execute(
        select(Invitation).where(
            Invitation.token == token,
            Invitation.used_at == None,
            Invitation.expires_at > datetime.utcnow()
        )
    )
    invitation = result.scalar_one_or_none()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired invitation token"
        )
    
    return {
        "valid": True,
        "email": invitation.email,
        "role": invitation.role.value,
        "expires_at": invitation.expires_at.isoformat()
    }


# ============================================================================
# Admin Endpoints
# ============================================================================

@admin_router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: User = Depends(require_role_db(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """List all users (admin only)"""
    result = await db.execute(
        select(User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return [UserResponse.from_orm(user) for user in users]


@admin_router.get("/invitations", response_model=List[InvitationResponse])
async def list_invitations(
    current_user: User = Depends(require_role_db(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
    pending_only: bool = Query(True, description="Only show pending invitations")
):
    """List all invitations (admin only)"""
    from app.models.user import Invitation
    from datetime import datetime
    
    query = select(Invitation)
    
    if pending_only:
        query = query.where(
            Invitation.used_at == None,
            Invitation.expires_at > datetime.utcnow()
        )
    
    result = await db.execute(query)
    invitations = result.scalars().all()
    
    # Build invitation URLs
    base_url = "https://control-deck.falklabs.de"
    responses = []
    for inv in invitations:
        responses.append(InvitationResponse(
            id=inv.id,
            email=inv.email,
            role=inv.role,
            token=inv.token,
            expires_at=inv.expires_at,
            invitation_url=f"{base_url}/auth/register?token={inv.token}"
        ))
    
    return responses


@admin_router.post("/users/{user_id}/deactivate", response_model=UserResponse)
async def deactivate_user(
    user_id: UUID,
    current_user: User = Depends(require_role_db(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate/reactivate a user (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deactivating yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Toggle active status
    user.is_active = not user.is_active
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.from_orm(user)


@admin_router.put("/users/{user_id}/role", response_model=UserResponse)
async def change_user_role(
    user_id: UUID,
    new_role: UserRole,
    current_user: User = Depends(require_role_db(UserRole.ADMIN)),
    db: AsyncSession = Depends(get_db)
):
    """Change user role (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent removing your own admin rights
    if user.id == current_user.id and new_role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin rights"
        )
    
    user.role = new_role
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.from_orm(user)
