"""
Authentication Service

Business logic for authentication, user management, and invitations.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID, uuid4
import secrets
import hashlib
import logging

from jose import jwt
from jose.exceptions import JWTError

from app.models.user import User, Invitation, UserRole
from app.models.token import RefreshToken, ServiceAccount, AgentCredential, TokenStatus, ServiceAccountStatus, AgentCredentialStatus
from app.schemas.auth import (
    LoginRequest, RegisterRequest, FirstTimeSetupRequest,
    InvitationCreate, TokenPair, DeviceInfo
)
from app.core.config import get_settings
from app.core.token_keys import get_token_key_manager

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
logger = logging.getLogger(__name__)
settings = get_settings()


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

    # ============================================================================
    # Token Management (RS256 with SHA256 hashed refresh tokens)
    # ============================================================================

    @staticmethod
    def _hash_token(token: str) -> str:
        """Hash a token using SHA256 for database storage"""
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    @staticmethod
    def _generate_refresh_token() -> str:
        """Generate a cryptographically secure refresh token"""
        return secrets.token_urlsafe(64)

    @staticmethod
    def _create_access_token_rs256(
        subject: str,
        scopes: List[str],
        token_type: str = "human",
        extra_claims: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, int]:
        """
        Create a JWT access token signed with RS256.
        
        Returns:
            Tuple of (token, expires_in_seconds)
        """
        now = datetime.utcnow()
        expires = now + timedelta(minutes=settings.access_token_expire_minutes)
        expires_in = int((expires - now).total_seconds())

        # Get key manager for signing
        key_manager = get_token_key_manager()
        private_key = key_manager.get_private_key()
        kid = key_manager.get_key_id()

        claims = {
            "sub": subject,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": expires,
            "scope": " ".join(scopes),
            "type": token_type,
            "jti": str(uuid4()),  # Unique token ID
        }

        if extra_claims:
            claims.update(extra_claims)

        # Sign with RS256 using private key
        token = jwt.encode(
            claims,
            private_key,
            algorithm="RS256",
            headers={"kid": kid}
        )

        return token, expires_in

    @staticmethod
    async def create_token_pair(
        user: User,
        scopes: List[str],
        device_info: Optional[DeviceInfo] = None
    ) -> TokenPair:
        """
        Create an access token and refresh token pair for a user.
        
        Args:
            user: The user to create tokens for
            scopes: List of OAuth scopes
            device_info: Optional device information for token binding
            
        Returns:
            TokenPair containing access_token, refresh_token, and metadata
        """
        # Create access token
        extra_claims = {
            "email": user.email,
            "role": user.role,
        }

        access_token, expires_in = AuthService._create_access_token_rs256(
            subject=str(user.id),
            scopes=scopes,
            token_type="human",
            extra_claims=extra_claims
        )

        # Generate and hash refresh token
        raw_refresh_token = AuthService._generate_refresh_token()
        refresh_token_hash = AuthService._hash_token(raw_refresh_token)

        # Calculate refresh token expiration
        refresh_expires = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

        # Create refresh token record in database
        refresh_token_record = RefreshToken(
            token_hash=refresh_token_hash,
            token_family=uuid4(),  # New family for new session
            user_id=user.id,
            status=TokenStatus.ACTIVE.value,
            expires_at=refresh_expires,
            ip_address=device_info.ip_address if device_info else None,
            user_agent=device_info.user_agent if device_info else None,
            device_fingerprint=device_info.device_fingerprint if device_info else None,
            rotation_count=0
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh_token,  # Return raw token (only time it's exposed)
            token_type="bearer",
            expires_in=expires_in
        ), refresh_token_record

    @staticmethod
    async def save_refresh_token(db: AsyncSession, token_record: RefreshToken) -> None:
        """Save a refresh token record to the database"""
        db.add(token_record)
        await db.commit()

    @staticmethod
    async def refresh_access_token(
        refresh_token: str,
        db: AsyncSession
    ) -> TokenPair:
        """
        Refresh an access token using a refresh token.
        
        Implements token rotation: creates new refresh token, invalidates old one.
        
        Args:
            refresh_token: The raw refresh token string
            db: Database session
            
        Returns:
            New TokenPair
            
        Raises:
            ValueError: If refresh token is invalid, expired, or revoked
        """
        # Hash the provided token to lookup in database
        token_hash = AuthService._hash_token(refresh_token)

        # Find the refresh token in database
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.status == TokenStatus.ACTIVE.value
            )
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            raise ValueError("Invalid refresh token")

        # Check if token is expired
        if token_record.is_expired:
            token_record.status = TokenStatus.EXPIRED.value
            await db.commit()
            raise ValueError("Refresh token has expired")

        # Get user
        result = await db.execute(
            select(User).where(User.id == token_record.user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found or inactive")

        # Mark old token as rotated
        token_record.status = TokenStatus.ROTATED.value
        token_record.used_at = datetime.utcnow()

        # Determine scopes based on user role
        scopes = ["read"]
        if user.role == UserRole.ADMIN.value:
            scopes = ["read", "write", "admin"]
        elif user.role == UserRole.OPERATOR.value:
            scopes = ["read", "write"]

        # Create device info from existing token
        device_info = DeviceInfo(
            ip_address=token_record.ip_address,
            user_agent=token_record.user_agent,
            device_fingerprint=token_record.device_fingerprint
        )

        # Create new token pair
        new_pair, new_record = await AuthService.create_token_pair(user, scopes, device_info)

        # Link new token to family (rotation tracking)
        new_record.token_family = token_record.token_family
        new_record.previous_token_id = token_record.id
        new_record.rotation_count = token_record.rotation_count + 1

        # Check for potential token replay (rotation count too high)
        if new_record.rotation_count > 10:
            logger.warning(f"Token family {token_record.token_family} has excessive rotations. Possible replay attack.")

        # Save all changes
        db.add(new_record)
        await db.commit()

        return new_pair

    @staticmethod
    async def revoke_token(
        token_hash: str,
        reason: str,
        db: AsyncSession
    ) -> bool:
        """
        Revoke a refresh token by its hash.
        
        Args:
            token_hash: SHA256 hash of the refresh token
            reason: Reason for revocation
            db: Database session
            
        Returns:
            True if token was found and revoked, False otherwise
        """
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        token_record = result.scalar_one_or_none()

        if not token_record:
            return False

        token_record.status = TokenStatus.REVOKED.value
        token_record.revoked_at = datetime.utcnow()

        await db.commit()
        logger.info(f"Token {token_record.id} revoked. Reason: {reason}")

        return True

    @staticmethod
    async def revoke_all_user_tokens(
        user_id: UUID,
        reason: str,
        db: AsyncSession
    ) -> int:
        """
        Revoke all active refresh tokens for a user.
        
        Args:
            user_id: User ID
            reason: Reason for revocation
            db: Database session
            
        Returns:
            Number of tokens revoked
        """
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.user_id == user_id,
                RefreshToken.status == TokenStatus.ACTIVE.value
            )
        )
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            token.status = TokenStatus.REVOKED.value
            token.revoked_at = datetime.utcnow()
            count += 1

        await db.commit()
        logger.info(f"Revoked {count} tokens for user {user_id}. Reason: {reason}")

        return count

    @staticmethod
    async def create_service_token(
        client_id: str,
        client_secret: str,
        scopes: List[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Create an access token for a service account (Client Credentials Grant).
        
        Args:
            client_id: Service account client ID
            client_secret: Service account client secret
            scopes: Requested scopes
            db: Database session
            
        Returns:
            Dictionary with access_token, expires_in, and scope
            
        Raises:
            ValueError: If credentials are invalid or service account is inactive
        """
        # Find service account
        result = await db.execute(
            select(ServiceAccount).where(
                ServiceAccount.client_id == client_id,
                ServiceAccount.status == ServiceAccountStatus.ACTIVE.value
            )
        )
        service_account = result.scalar_one_or_none()

        if not service_account:
            raise ValueError("Invalid client credentials")

        # Verify client secret
        if not pwd_context.verify(client_secret, service_account.client_secret_hash):
            raise ValueError("Invalid client credentials")

        # Check if service account is expired
        if service_account.expires_at and datetime.utcnow() >= service_account.expires_at:
            raise ValueError("Service account has expired")

        # Validate requested scopes against allowed scopes
        allowed_scopes = set(service_account.scopes or [])
        requested_scopes = set(scopes)

        if not requested_scopes.issubset(allowed_scopes):
            invalid_scopes = requested_scopes - allowed_scopes
            raise ValueError(f"Invalid scopes requested: {invalid_scopes}")

        # Use requested scopes or default to allowed scopes
        effective_scopes = list(requested_scopes) if requested_scopes else list(allowed_scopes)

        # Create access token
        extra_claims = {
            "client_id": client_id,
            "account_type": "service",
        }

        access_token, expires_in = AuthService._create_access_token_rs256(
            subject=str(service_account.id),
            scopes=effective_scopes,
            token_type="service",
            extra_claims=extra_claims
        )

        # Update last used timestamp
        service_account.last_used_at = datetime.utcnow()
        service_account.use_count += 1
        await db.commit()

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "scope": " ".join(effective_scopes)
        }

    @staticmethod
    async def create_agent_token(
        agent_id: str,
        parent_agent_id: Optional[str],
        scopes: List[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Create an access token for an AI agent.
        
        Args:
            agent_id: Unique agent identifier
            parent_agent_id: Optional parent agent ID for delegation chains
            scopes: Requested scopes
            db: Database session
            
        Returns:
            Dictionary with access_token, expires_in, agent_id, and scope
            
        Raises:
            ValueError: If agent credentials are invalid or agent is inactive
        """
        # Find agent credential
        result = await db.execute(
            select(AgentCredential).where(
                AgentCredential.agent_id == agent_id,
                AgentCredential.status == AgentCredentialStatus.ACTIVE.value
            )
        )
        agent_cred = result.scalar_one_or_none()

        if not agent_cred:
            # If agent doesn't exist and parent is specified, we could auto-create
            # For now, require explicit registration
            raise ValueError("Invalid agent credentials")

        # Verify parent_agent_id matches if specified
        if parent_agent_id and agent_cred.parent_agent_id != parent_agent_id:
            raise ValueError("Parent agent mismatch")

        # Check if agent token is expired
        if agent_cred.expires_at and datetime.utcnow() >= agent_cred.expires_at:
            raise ValueError("Agent credentials have expired")

        # Validate requested scopes against allowed scopes
        allowed_scopes = set(agent_cred.allowed_scopes or ["read"])
        requested_scopes = set(scopes)

        if not requested_scopes.issubset(allowed_scopes):
            invalid_scopes = requested_scopes - allowed_scopes
            raise ValueError(f"Invalid scopes requested: {invalid_scopes}")

        effective_scopes = list(requested_scopes) if requested_scopes else list(allowed_scopes)

        # Create access token
        extra_claims = {
            "agent_id": agent_id,
            "parent_agent_id": parent_agent_id,
            "agent_name": agent_cred.agent_name,
            "capabilities": agent_cred.capabilities,
            "account_type": "agent",
        }

        access_token, expires_in = AuthService._create_access_token_rs256(
            subject=agent_id,
            scopes=effective_scopes,
            token_type="agent",
            extra_claims=extra_claims
        )

        # Update last used timestamp
        agent_cred.last_used_at = datetime.utcnow()
        agent_cred.use_count += 1
        await db.commit()

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "scope": " ".join(effective_scopes),
            "agent_id": agent_id
        }
