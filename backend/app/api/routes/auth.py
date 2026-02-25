"""
Authentication API Routes

FastAPI endpoints for authentication and user management.
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt

from app.core.database import get_db
from app.core.security import create_access_token, SECRET_KEY, ALGORITHM
from app.core.config import get_settings
from app.core.token_keys import get_token_key_manager
from app.models.user import User, UserRole
from app.models.token import RefreshToken, ServiceAccount, AgentCredential
from app.services.auth_service import AuthService
from app.schemas.auth import (
    LoginRequest, LoginResponse, RegisterRequest, UserResponse,
    FirstTimeSetupRequest, InvitationCreate, InvitationResponse,
    TokenPair, RefreshRequest, LogoutRequest, ServiceTokenRequest,
    ServiceTokenResponse, AgentTokenRequest, AgentTokenResponse,
    JWKSResponse, DeviceInfo
)
import logging

logger = logging.getLogger(__name__)

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
        if user.role != required_role.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role.value}' required",
            )
        return user
    return check_role


def require_any_role_db(required_roles: List[UserRole]):
    """Dependency factory for requiring any of the specified roles (DB-based)"""
    async def check_roles(user: User = Depends(get_current_user_db)) -> User:
        allowed_roles = [r.value for r in required_roles]
        if user.role not in allowed_roles:
            roles_str = ", ".join(allowed_roles)
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


@router.post("/first-time-setup", response_model=TokenPair)
async def first_time_setup(
    data: FirstTimeSetupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Create first admin user (only works if no admin exists).
    
    Returns a token pair (access_token + refresh_token) using RS256.
    
    HTTP Codes:
        200: Success, admin created and token pair returned
        400: Admin already exists
    """
    try:
        user = await AuthService.create_first_admin(db, data)

        # Create device info
        device_info = DeviceInfo(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            device_fingerprint=request.headers.get("x-device-fingerprint")
        )

        # Create token pair
        token_pair, refresh_record = await AuthService.create_token_pair(
            user=user,
            scopes=["read", "write", "admin"],
            device_info=device_info
        )

        # Save refresh token
        await AuthService.save_refresh_token(db, refresh_record)

        return token_pair
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenPair)
async def login(
    credentials: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns a token pair (access_token + refresh_token) using RS256.
    The refresh token is stored as a SHA256 hash in the database.
    
    HTTP Codes:
        200: Success, token pair returned
        401: Invalid credentials
        403: User account is disabled
    """
    user = await AuthService.authenticate_user(
        db, credentials.email, credentials.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Determine scopes based on user role
    scopes = ["read"]
    if user.role == UserRole.ADMIN.value:
        scopes = ["read", "write", "admin"]
    elif user.role == UserRole.OPERATOR.value:
        scopes = ["read", "write"]

    # Extract device info from request
    device_info = DeviceInfo(
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        device_fingerprint=request.headers.get("x-device-fingerprint")
    )

    # Create token pair (returns both the response object and the DB record)
    token_pair, refresh_record = await AuthService.create_token_pair(
        user=user,
        scopes=scopes,
        device_info=device_info
    )

    # Save refresh token to database
    await AuthService.save_refresh_token(db, refresh_record)

    return token_pair


@router.post("/register", response_model=TokenPair)
async def register(
    data: RegisterRequest,
    invitation_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Register new user with invitation token.
    
    Returns a token pair (access_token + refresh_token) using RS256.
    
    HTTP Codes:
        200: Success, user created and token pair returned
        400: Invalid invitation or validation error
    """
    try:
        user = await AuthService.register_with_invitation(db, invitation_token, data)

        # Determine scopes
        scopes = ["read"]
        if user.role == UserRole.ADMIN.value:
            scopes = ["read", "write", "admin"]
        elif user.role == UserRole.OPERATOR.value:
            scopes = ["read", "write"]

        # Create device info
        device_info = DeviceInfo(
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            device_fingerprint=request.headers.get("x-device-fingerprint")
        )

        # Create token pair
        token_pair, refresh_record = await AuthService.create_token_pair(
            user=user,
            scopes=scopes,
            device_info=device_info
        )

        # Save refresh token
        await AuthService.save_refresh_token(db, refresh_record)

        return token_pair
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


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
# Token Management Endpoints
# ============================================================================

@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh an access token using a refresh token.
    
    Implements token rotation - the old refresh token is invalidated
    and a new token pair is returned.
    
    HTTP Codes:
        200: Success, new token pair returned
        401: Invalid or expired refresh token
        403: User account is disabled
    """
    try:
        new_pair = await AuthService.refresh_access_token(data.refresh_token, db)
        return new_pair
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: LogoutRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Logout by revoking the refresh token.
    
    The access token remains valid until expiry (short-lived),
    but the refresh token is immediately invalidated.
    
    HTTP Codes:
        204: Successfully logged out
        400: Invalid token format
    """
    token_hash = AuthService._hash_token(data.refresh_token)
    revoked = await AuthService.revoke_token(token_hash, "User logout", db)
    
    if not revoked:
        # Token not found - still return 204 as the end state is the same
        logger = logging.getLogger(__name__)
        logger.info("Logout attempted with unknown token")
    
    return None


@router.post("/service-token", response_model=ServiceTokenResponse)
async def service_token(
    data: ServiceTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtain an access token for a service account (Client Credentials Grant).
    
    This endpoint is designed for non-human entities like CI/CD pipelines,
    monitoring systems, and external integrations.
    
    HTTP Codes:
        200: Success, token returned
        401: Invalid client credentials
        403: Service account is disabled or expired
        400: Invalid scope requested
    """
    try:
        # Parse scope string into list
        scopes = []
        if data.scope:
            scopes = [s.strip() for s in data.scope.split() if s.strip()]

        result = await AuthService.create_service_token(
            client_id=data.client_id,
            client_secret=data.client_secret,
            scopes=scopes,
            db=db
        )

        return ServiceTokenResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            scope=result["scope"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/agent-token", response_model=AgentTokenResponse)
async def agent_token(
    data: AgentTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Obtain an access token for an AI agent.
    
    This endpoint authenticates agents using their agent credentials
    and supports capability-based access control with delegation chains.
    
    HTTP Codes:
        200: Success, token returned
        401: Invalid agent credentials
        403: Agent is disabled or expired
        400: Invalid scope or parent mismatch
    """
    try:
        # Parse scope string into list
        scopes = []
        if data.scope:
            scopes = [s.strip() for s in data.scope.split() if s.strip()]

        result = await AuthService.create_agent_token(
            agent_id=data.agent_id,
            parent_agent_id=data.parent_agent_id,
            scopes=scopes,
            db=db
        )

        return AgentTokenResponse(
            access_token=result["access_token"],
            token_type=result["token_type"],
            expires_in=result["expires_in"],
            scope=result["scope"],
            agent_id=result["agent_id"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )


# ============================================================================
# JWKS Endpoint (Well-Known)
# ============================================================================

from fastapi.responses import JSONResponse

@router.get("/.well-known/jwks.json", response_model=JWKSResponse)
async def jwks_endpoint():
    """
    JSON Web Key Set (JWKS) endpoint for token verification.
    
    This endpoint provides the public key(s) that can be used to
    verify JWT access tokens signed by this authorization server.
    
    HTTP Codes:
        200: Returns JWKS containing public key
        503: Key management not initialized
    """
    try:
        key_manager = get_token_key_manager()
        jwks_data = key_manager.get_jwks()
        return JWKSResponse(**jwks_data)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token key management not initialized"
        )


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
    if user.id == current_user.id and new_role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin rights"
        )
    
    user.role = new_role.value
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.from_orm(user)
