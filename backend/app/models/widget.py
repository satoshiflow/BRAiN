"""
AXE Widget Database Models

SQLAlchemy ORM models for web widget sessions, messages, and API credentials.
Supports embedded chat widget for customer support and assistance.

Models:
- WidgetSessionORM: Web chat sessions for embedded AXE widget
- WidgetMessageORM: Message history within sessions
- WidgetCredentialORM: API credentials for website projects
"""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Integer, Boolean, ForeignKey, JSON, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base
import uuid


class WidgetSessionORM(Base):
    """
    Widget Session Model

    Represents a web chat session for the embedded AXE widget.
    Sessions have a TTL (time-to-live) after which they expire.

    Attributes:
        id: Primary key (UUID)
        session_id: Unique session identifier for the widget
        project_id: Website project ID (for multi-tenant support)
        owner_user_id: Optional UUID of owning user
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp
        updated_at: Last update timestamp
        ip_address: Client IP address
        user_agent: Client user agent
        message_count: Number of messages in session
        status: Session status (active, expired, revoked)
        metadata: Custom JSONB metadata
        messages: Relationship to WidgetMessageORM
    """
    __tablename__ = "widget_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(String(36), unique=True, nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    owner_user_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    message_count = Column(Integer, default=0, nullable=False)
    status = Column(String(50), nullable=False, default='active', index=True)
    metadata = Column(JSONB, nullable=True)

    # Relationships
    messages = relationship("WidgetMessageORM", back_populates="session", cascade="all, delete-orphan")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'expired', 'revoked')",
            name='ck_widget_sessions_status'
        ),
    )

    def is_expired(self) -> bool:
        """Check if session has expired"""
        return datetime.utcnow() >= self.expires_at

    def __repr__(self):
        return f"<WidgetSession(session_id={self.session_id}, status={self.status}, project_id={self.project_id})>"


class WidgetMessageORM(Base):
    """
    Widget Message Model

    Represents a single message in a widget session.
    Messages can be from user or assistant.

    Attributes:
        id: Primary key (UUID)
        session_id: Foreign key to WidgetSessionORM
        role: Message role (user or assistant)
        content: Message content (text)
        created_at: Message creation timestamp
        metadata: Custom JSONB metadata
        session: Relationship back to WidgetSessionORM
    """
    __tablename__ = "widget_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("widget_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)
    content = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    metadata = Column(JSONB, nullable=True)

    # Relationships
    session = relationship("WidgetSessionORM", back_populates="messages")

    # Constraints
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name='ck_widget_messages_role'
        ),
    )

    def __repr__(self):
        return f"<WidgetMessage(id={self.id}, role={self.role}, session_id={self.session_id})>"


class WidgetCredentialORM(Base):
    """
    Widget Credential Model

    API credentials for website projects to authenticate widget requests.
    Each project has one credential pair.

    Security Notes:
    - api_key_hash and secret_hash are hashed (not reversible)
    - Credentials can be expired and revoked
    - Rate limits prevent abuse
    - last_used_at tracks credential usage for monitoring

    Attributes:
        id: Primary key (UUID)
        project_id: Unique website project identifier
        api_key_hash: Hashed API key (one-way hash)
        secret_hash: Hashed secret (one-way hash)
        created_at: Credential creation timestamp
        expires_at: Optional credential expiration
        last_used_at: Last usage timestamp
        is_active: Whether credential is active
        rate_limit: Max requests per minute
        scopes: JSON array of allowed scopes
        created_by: Creator identifier
        metadata: Custom JSONB metadata
    """
    __tablename__ = "widget_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(255), unique=True, nullable=False, index=True)
    api_key_hash = Column(String(255), unique=True, nullable=False)
    secret_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    rate_limit = Column(Integer, default=30, nullable=False)
    scopes = Column(JSON, nullable=True)
    created_by = Column(String(255), nullable=True)
    metadata = Column(JSONB, nullable=True)

    def __repr__(self):
        return f"<WidgetCredential(project_id={self.project_id}, active={self.is_active}, rate_limit={self.rate_limit})>"
