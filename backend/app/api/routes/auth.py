"""
Authentication API Routes

FastAPI endpoints for authentication and user management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, require_role
from app.models.user import UserRole
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest, LoginResponse, RegisterRequest, UserResponse,
    FirstTimeSetupRequest, InvitationCreate, InvitationResponse
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


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
    current_user: User = Depends(require_role("admin")),
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
    current_user: User = Depends(require_role("viewer")),
    db: AsyncSession = Depends(get_db)
):
    """Get current authenticated user"""
    return UserResponse.from_orm(current_user)
