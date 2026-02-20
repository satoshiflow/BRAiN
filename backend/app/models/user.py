"""
User and Invitation Models

SQLAlchemy ORM models for authentication and user management.
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User role enumeration"""
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class User(Base):
    """
    User Model
    
    Stores user accounts with role-based access control.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default=UserRole.OPERATOR.value, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Relationships
    created_users = relationship("User", back_populates="creator")
    creator = relationship("User", remote_side=[id], back_populates="created_users")
    invitations = relationship("Invitation", back_populates="creator")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class Invitation(Base):
    """
    Invitation Model
    
    Stores invitation tokens for new user registration.
    """
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    role = Column(String(50), default=UserRole.OPERATOR.value, nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", back_populates="invitations")

    def __repr__(self):
        return f"<Invitation(id={self.id}, email={self.email}, token={self.token[:8]}...)>"
