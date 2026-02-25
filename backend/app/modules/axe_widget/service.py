"""
AXE Widget Service Layer

Business logic for managing widget sessions, messages, and credentials.
Handles session lifecycle, TTL management, credential verification, and rate limiting.

Security:
- API keys and secrets are hashed (never stored in plain text)
- Sessions have configurable TTL
- Rate limiting per credential
- All credentials verified before operations
- Audit logging for sensitive operations
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, func
from sqlalchemy.exc import IntegrityError
from loguru import logger

from app.models.widget import WidgetSessionORM, WidgetMessageORM, WidgetCredentialORM
from .schemas import (
    WidgetSessionCreate,
    WidgetSessionResponse,
    WidgetMessageRequest,
    WidgetMessageResponse,
    WidgetCredentialCreate,
    WidgetCredentialResponse,
    WidgetCredentialWithKeyResponse,
)


class WidgetService:
    """Service for AXE Widget management"""

    # Default session TTL: 24 hours
    DEFAULT_SESSION_TTL_MINUTES = 24 * 60

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # Session Management
    # ========================================================================

    async def create_session(
        self,
        project_id: str,
        position: str = "bottom-right",
        theme: str = "dark",
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        ttl_minutes: int = DEFAULT_SESSION_TTL_MINUTES,
    ) -> WidgetSessionResponse:
        """
        Create a new widget session.

        Args:
            project_id: Website project identifier
            position: Widget position on page
            theme: Color theme
            metadata: Custom metadata
            ip_address: Client IP address
            user_agent: Client user agent
            ttl_minutes: Session time-to-live in minutes

        Returns:
            Created session response

        Raises:
            HTTPException: If project has no active credentials
        """
        # Verify project has active credentials
        credential = await self._get_credential_by_project(project_id)
        if not credential or not credential.is_active:
            logger.warning(f"Session creation failed: No active credential for project {project_id}")
            raise ValueError(f"Project '{project_id}' is not configured or credentials are inactive")

        # Generate session ID
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=ttl_minutes)

        # Create session
        session = WidgetSessionORM(
            id=uuid.uuid4(),
            session_id=session_id,
            project_id=project_id,
            created_at=now,
            expires_at=expires_at,
            updated_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
            message_count=0,
            status='active',
            metadata=metadata or {},
        )

        try:
            self.db.add(session)
            await self.db.commit()
            logger.info(f"Created widget session {session_id} for project {project_id}")
            return WidgetSessionResponse.from_orm(session)
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create session: {e}")
            raise ValueError("Failed to create session")

    async def get_session(self, session_id: str) -> Optional[WidgetSessionResponse]:
        """
        Get session by ID with expiration check.

        Args:
            session_id: Widget session ID

        Returns:
            Session response or None if not found/expired

        Raises:
            ValueError: If session is expired
        """
        result = await self.db.execute(
            select(WidgetSessionORM).where(WidgetSessionORM.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            return None

        if session.is_expired():
            logger.warning(f"Session {session_id} is expired")
            raise ValueError("Session has expired")

        return WidgetSessionResponse.from_orm(session)

    async def list_sessions(
        self,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[WidgetSessionResponse], int]:
        """
        List widget sessions with optional filtering.

        Args:
            project_id: Filter by project ID
            status: Filter by status (active, expired, revoked)
            limit: Max results per page
            offset: Pagination offset

        Returns:
            Tuple of (sessions list, total count)
        """
        query = select(WidgetSessionORM)

        if project_id:
            query = query.where(WidgetSessionORM.project_id == project_id)

        if status:
            query = query.where(WidgetSessionORM.status == status)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(WidgetSessionORM.id)).select_from(WidgetSessionORM).where(
                and_(
                    WidgetSessionORM.project_id == project_id if project_id else True,
                    WidgetSessionORM.status == status if status else True,
                )
            )
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await self.db.execute(
            query.order_by(WidgetSessionORM.created_at.desc()).limit(limit).offset(offset)
        )
        sessions = result.scalars().all()

        return [WidgetSessionResponse.from_orm(s) for s in sessions], total

    # ========================================================================
    # Message Management
    # ========================================================================

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WidgetMessageResponse:
        """
        Add a message to a session.

        Args:
            session_id: Session ID
            role: Message role (user or assistant)
            content: Message content
            metadata: Custom metadata

        Returns:
            Created message response

        Raises:
            ValueError: If session not found or expired
        """
        # Verify session exists and is not expired
        result = await self.db.execute(
            select(WidgetSessionORM).where(WidgetSessionORM.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise ValueError("Session not found")

        if session.is_expired():
            raise ValueError("Session has expired")

        # Create message
        message = WidgetMessageORM(
            id=uuid.uuid4(),
            session_id=session.id,
            role=role,
            content=content,
            created_at=datetime.utcnow(),
            metadata=metadata or {},
        )

        try:
            self.db.add(message)

            # Increment message count
            session.message_count += 1
            session.updated_at = datetime.utcnow()

            await self.db.commit()
            logger.info(f"Added message to session {session_id} (count: {session.message_count})")
            return WidgetMessageResponse.from_orm(message)
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to add message: {e}")
            raise ValueError("Failed to add message")

    async def get_message_history(
        self,
        session_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[WidgetMessageResponse]:
        """
        Get message history for a session.

        Args:
            session_id: Session ID
            limit: Max messages to return
            offset: Pagination offset

        Returns:
            List of messages ordered by creation time
        """
        result = await self.db.execute(
            select(WidgetSessionORM).where(WidgetSessionORM.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise ValueError("Session not found")

        # Get messages
        msg_result = await self.db.execute(
            select(WidgetMessageORM)
            .where(WidgetMessageORM.session_id == session.id)
            .order_by(WidgetMessageORM.created_at.asc())
            .limit(limit)
            .offset(offset)
        )
        messages = msg_result.scalars().all()

        return [WidgetMessageResponse.from_orm(m) for m in messages]

    # ========================================================================
    # Credential Management
    # ========================================================================

    async def create_credential(
        self,
        data: WidgetCredentialCreate,
        created_by: str,
    ) -> WidgetCredentialWithKeyResponse:
        """
        Create new API credentials for a project.

        Args:
            data: Credential creation data
            created_by: Creator identifier (user ID)

        Returns:
            Credential response with plain text API key and secret (shown once only)

        Raises:
            ValueError: If project already has credentials
        """
        # Check if project already has credentials
        existing = await self._get_credential_by_project(data.project_id)
        if existing:
            logger.warning(f"Credential creation failed: Project {data.project_id} already has credentials")
            raise ValueError(f"Credentials already exist for project '{data.project_id}'")

        # Generate API key and secret
        api_key = secrets.token_urlsafe(32)
        secret = secrets.token_urlsafe(32)

        # Hash credentials
        api_key_hash = self._hash_credential(api_key)
        secret_hash = self._hash_credential(secret)

        # Create credential
        credential = WidgetCredentialORM(
            id=uuid.uuid4(),
            project_id=data.project_id,
            api_key_hash=api_key_hash,
            secret_hash=secret_hash,
            created_at=datetime.utcnow(),
            expires_at=None,
            last_used_at=None,
            is_active=True,
            rate_limit=data.rate_limit,
            scopes=data.scopes or [],
            created_by=created_by,
            metadata=data.metadata or {},
        )

        try:
            self.db.add(credential)
            await self.db.commit()
            logger.warning(f"Created widget credentials for project {data.project_id} by {created_by}")

            # Return with plain text credentials (only time they're shown)
            response = WidgetCredentialWithKeyResponse.from_orm(credential)
            response.api_key = api_key
            response.secret = secret
            return response
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Failed to create credential: {e}")
            raise ValueError("Failed to create credential")

    async def get_credential(self, credential_id: str) -> Optional[WidgetCredentialResponse]:
        """Get credential by ID (admin only)"""
        result = await self.db.execute(
            select(WidgetCredentialORM).where(WidgetCredentialORM.id == credential_id)
        )
        credential = result.scalar_one_or_none()
        return WidgetCredentialResponse.from_orm(credential) if credential else None

    async def list_credentials(
        self,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[WidgetCredentialResponse], int]:
        """List all credentials with optional filtering (admin only)"""
        query = select(WidgetCredentialORM)

        if is_active is not None:
            query = query.where(WidgetCredentialORM.is_active == is_active)

        # Get total count
        count_result = await self.db.execute(
            select(func.count(WidgetCredentialORM.id))
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await self.db.execute(
            query.order_by(WidgetCredentialORM.created_at.desc()).limit(limit).offset(offset)
        )
        credentials = result.scalars().all()

        return [WidgetCredentialResponse.from_orm(c) for c in credentials], total

    async def revoke_credential(self, credential_id: str) -> bool:
        """Revoke a credential (set is_active=False)"""
        result = await self.db.execute(
            select(WidgetCredentialORM).where(WidgetCredentialORM.id == credential_id)
        )
        credential = result.scalar_one_or_none()

        if not credential:
            return False

        credential.is_active = False
        await self.db.commit()
        logger.warning(f"Revoked widget credential {credential_id}")
        return True

    # ========================================================================
    # Verification & Validation
    # ========================================================================

    async def verify_credential(
        self,
        project_id: str,
        api_key: str,
        secret: str,
    ) -> bool:
        """
        Verify API key and secret for a project.

        Args:
            project_id: Website project ID
            api_key: Plain text API key
            secret: Plain text secret

        Returns:
            True if credentials are valid and active

        Raises:
            ValueError: If credentials invalid/inactive
        """
        credential = await self._get_credential_by_project(project_id)

        if not credential:
            logger.warning(f"Credential verification failed: No credential for project {project_id}")
            raise ValueError("Invalid credentials")

        if not credential.is_active:
            logger.warning(f"Credential verification failed: Credential inactive for project {project_id}")
            raise ValueError("Credentials are inactive")

        # Verify API key hash
        if not self._verify_credential(api_key, credential.api_key_hash):
            logger.warning(f"Credential verification failed: Invalid API key for project {project_id}")
            raise ValueError("Invalid credentials")

        # Verify secret hash
        if not self._verify_credential(secret, credential.secret_hash):
            logger.warning(f"Credential verification failed: Invalid secret for project {project_id}")
            raise ValueError("Invalid credentials")

        # Update last_used_at
        credential.last_used_at = datetime.utcnow()
        await self.db.commit()

        return True

    async def check_rate_limit(self, project_id: str) -> bool:
        """
        Check if project has exceeded rate limit.

        Returns:
            True if under limit, False if exceeded
        """
        credential = await self._get_credential_by_project(project_id)
        if not credential:
            return False

        # For now, return True (rate limiting handled by limiter middleware)
        # In production, implement sliding window counter in Redis
        return True

    # ========================================================================
    # Private Helpers
    # ========================================================================

    async def _get_credential_by_project(self, project_id: str) -> Optional[WidgetCredentialORM]:
        """Get credential by project ID (internal use only)"""
        result = await self.db.execute(
            select(WidgetCredentialORM).where(WidgetCredentialORM.project_id == project_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _hash_credential(credential: str) -> str:
        """Hash a credential using SHA-256"""
        return hashlib.sha256(credential.encode()).hexdigest()

    @staticmethod
    def _verify_credential(plain: str, hashed: str) -> bool:
        """Verify a plain credential against its hash"""
        return hashlib.sha256(plain.encode()).hexdigest() == hashed
