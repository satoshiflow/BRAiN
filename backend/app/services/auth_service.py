"""
Authentication Service

Business logic for authentication, user management, and invitations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import secrets

from app.models.user import User, Invitation, UserRole
from app.schemas.auth import (
    LoginRequest, RegisterRequest, FirstTimeSetupRequest,
    InvitationCreate
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Authentication and user management service"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    async def check_first_time_setup(db: AsyncSession) -> bool:
        """Check if any admin user exists"""
        result = await db.execute(
            select(User).where(User.role == UserRole.ADMIN.value, User.is_active.is_(True))
        )
        admin = result.scalar_one_or_none()
        return admin is None  # True if no admin exists

    @staticmethod
    async def create_first_admin(
        db: AsyncSession,
        data: FirstTimeSetupRequest
    ) -> User:
        """Create the first admin user (only if no admin exists)"""
        is_first_time = await AuthService.check_first_time_setup(db)
        if not is_first_time:
            raise ValueError("Admin user already exists")

        user = User(
            email=data.email,
            username=data.username,
            password_hash=AuthService.hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,  # First admin is auto-verified
        )

        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """Authenticate user with email and password"""
        result = await db.execute(
            select(User).where(User.email == email, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not AuthService.verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.utcnow()
        await db.commit()

        return user

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        admin_id: UUID,
        data: InvitationCreate
    ) -> Invitation:
        """Create invitation for new user (admin only)"""
        # Check if user already exists
        result = await db.execute(
            select(User).where(User.email == data.email)
        )
        existing_user = result.scalar_one_or_none()
        if existing_user:
            raise ValueError("User with this email already exists")

        # Generate unique token
        token = secrets.token_urlsafe(32)

        invitation = Invitation(
            email=data.email,
            role=data.role,
            token=token,
            created_by=admin_id,
            expires_at=datetime.utcnow() + timedelta(days=7),  # 7 days validity
        )

        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        return invitation

    @staticmethod
    async def register_with_invitation(
        db: AsyncSession,
        token: str,
        data: RegisterRequest
    ) -> User:
        """Register new user with invitation token"""
        # Find valid invitation
        result = await db.execute(
            select(Invitation).where(
                Invitation.token == token,
                Invitation.used_at == None,
                Invitation.expires_at > datetime.utcnow()
            )
        )
        invitation = result.scalar_one_or_none()

        if not invitation:
            raise ValueError("Invalid or expired invitation token")

        # Verify email matches
        if invitation.email != data.email:
            raise ValueError("Email does not match invitation")

        # Create user
        user = User(
            email=data.email,
            username=data.username,
            password_hash=AuthService.hash_password(data.password),
            full_name=data.full_name,
            role=invitation.role,  # Role from invitation
            is_active=True,
            is_verified=True,  # Invited users are verified
            created_by=invitation.created_by,
        )

        db.add(user)

        # Mark invitation as used
        invitation.used_at = datetime.utcnow()

        await db.commit()
        await db.refresh(user)
        return user
