"""
Token Models - Database Models for Token Management

Provides:
- RefreshToken: For token rotation and session management
- ServiceAccount: For non-human identity (automation, integrations)
- AgentCredential: For agent authentication and capability delegation
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class TokenStatus(str, enum.Enum):
    """Token status enumeration"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    ROTATED = "rotated"  # Replaced by new token


class ServiceAccountStatus(str, enum.Enum):
    """Service account status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class AgentCredentialStatus(str, enum.Enum):
    """Agent credential status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class AgentCapability(str, enum.Enum):
    """Agent capability enumeration for capability-based access"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    DELEGATE = "delegate"  # Can create sub-agents


class RefreshToken(Base):
    """
    Refresh Token Model
    
    Stores refresh tokens for token rotation pattern.
    Enables secure session management with revocation capability.
    
    Security:
    - One-time use (rotated on refresh)
    - Hashed token storage (never store plaintext)
    - Family tracking to detect replay attacks
    """
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Token data (hashed)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    token_family = Column(UUID(as_uuid=True), nullable=False, index=True)  # For rotation tracking
    
    # Ownership
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    
    # Status
    status = Column(String(50), default=TokenStatus.ACTIVE.value, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used_at = Column(DateTime, nullable=True)  # When rotated
    revoked_at = Column(DateTime, nullable=True)
    
    # Context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)
    device_fingerprint = Column(String(255), nullable=True)  # Optional device binding
    
    # Rotation tracking
    previous_token_id = Column(UUID(as_uuid=True), ForeignKey("refresh_tokens.id"), nullable=True)
    rotation_count = Column(Integer, default=0, nullable=False)  # Detect unusual patterns
    
    # Relationships
    user = relationship("User", backref="refresh_tokens")
    previous_token = relationship("RefreshToken", remote_side=[id], backref="next_tokens")

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user={self.user_id}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if token is currently active and not expired"""
        if self.status != TokenStatus.ACTIVE.value:
            return False
        return datetime.utcnow() < self.expires_at
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired"""
        return datetime.utcnow() >= self.expires_at


class ServiceAccount(Base):
    """
    Service Account Model
    
    Non-human identity for automation, integrations, and external services.
    Similar to a user but designed for programmatic access.
    
    Use cases:
    - CI/CD pipelines
    - External integrations
    - Monitoring systems
    - Backup services
    """
    __tablename__ = "service_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Identity
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Authentication
    client_id = Column(String(255), unique=True, nullable=False, index=True)
    client_secret_hash = Column(String(255), nullable=False)  # Never store plaintext
    
    # Status
    status = Column(String(50), default=ServiceAccountStatus.ACTIVE.value, nullable=False, index=True)
    
    # Permissions
    scopes = Column(JSON, default=list, nullable=False)  # ["api:read", "api:write"]
    roles = Column(JSON, default=list, nullable=False)  # ["service", "integration"]
    
    # Access control
    allowed_ips = Column(JSON, nullable=True)  # IP whitelist ["10.0.0.0/8", "192.168.1.1"]
    allowed_origins = Column(JSON, nullable=True)  # CORS origins for this account
    rate_limit = Column(Integer, default=1000, nullable=False)  # Requests per minute
    
    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    owner_team = Column(String(100), nullable=True)  # Team/org ownership
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Optional expiration
    
    # Audit
    last_ip = Column(String(45), nullable=True)
    use_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    creator = relationship("User", backref="created_service_accounts")

    def __repr__(self):
        return f"<ServiceAccount(id={self.id}, name={self.name}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if service account is active and not expired"""
        if self.status != ServiceAccountStatus.ACTIVE.value:
            return False
        if self.expires_at and datetime.utcnow() >= self.expires_at:
            return False
        return True


class AgentCredential(Base):
    """
    Agent Credential Model
    
    Credentials for AI agents with capability-based access control.
    Supports parent-child delegation chains for agent hierarchies.
    
    Use cases:
    - Agent authentication to API
    - Capability delegation (parent -> child agents)
    - Agent reputation tracking
    - Session-based agent operations
    
    Capabilities:
    - read: Read data from the system
    - write: Modify/create data
    - execute: Run operations and tasks
    - admin: Full administrative access
    - delegate: Create and authorize sub-agents
    """
    __tablename__ = "agent_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Agent identity
    agent_id = Column(String(255), unique=True, nullable=False, index=True)
    agent_name = Column(String(255), nullable=False)
    agent_type = Column(String(100), nullable=False)  # "executor", "coordinator", "worker"
    
    # Authentication
    credential_hash = Column(String(255), nullable=False)  # API key hash
    
    # Status
    status = Column(String(50), default=AgentCredentialStatus.ACTIVE.value, nullable=False, index=True)
    
    # Capabilities (capability-based access control)
    capabilities = Column(JSON, default=lambda: ["read"], nullable=False)
    # Example: ["read", "write", "execute"]
    
    # Scope limitations
    allowed_scopes = Column(JSON, default=list, nullable=False)  # API scopes
    allowed_resources = Column(JSON, nullable=True)  # Resource patterns ["docs/*", "tasks/{agent_id}/*"]
    
    # Delegation chain
    parent_agent_id = Column(String(255), ForeignKey("agent_credentials.agent_id"), nullable=True, index=True)
    delegation_depth = Column(Integer, default=0, nullable=False)  # 0 = root, max typically 3
    delegation_chain = Column(JSON, default=list, nullable=False)  # [root_id, ..., parent_id]
    
    # Ownership
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    owner_service_account_id = Column(UUID(as_uuid=True), ForeignKey("service_accounts.id"), nullable=True)
    
    # Context
    metadata = Column(JSON, default=dict, nullable=False)  # Agent-specific metadata
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True, index=True)
    last_used_at = Column(DateTime, nullable=True)
    
    # Usage tracking
    use_count = Column(Integer, default=0, nullable=False)
    last_ip = Column(String(45), nullable=True)
    
    # Reputation (for Agent Civilization V3)
    karma_score = Column(Integer, default=0, nullable=False)  # Reputation score
    successful_operations = Column(Integer, default=0, nullable=False)
    failed_operations = Column(Integer, default=0, nullable=False)
    
    # Relationships
    parent_agent = relationship("AgentCredential", remote_side=[agent_id], backref="child_agents")
    owner_user = relationship("User", foreign_keys=[owner_user_id], backref="agent_credentials")
    owner_service_account = relationship("ServiceAccount", foreign_keys=[owner_service_account_id], backref="agent_credentials")

    def __repr__(self):
        return f"<AgentCredential(id={self.id}, agent={self.agent_id}, status={self.status})>"
    
    @property
    def is_active(self) -> bool:
        """Check if credential is active and not expired"""
        if self.status != AgentCredentialStatus.ACTIVE.value:
            return False
        if self.expires_at and datetime.utcnow() >= self.expires_at:
            return False
        return True
    
    def has_capability(self, capability: str) -> bool:
        """Check if agent has a specific capability"""
        return capability in (self.capabilities or [])
    
    def has_any_capability(self, capabilities: list) -> bool:
        """Check if agent has any of the specified capabilities"""
        return any(c in (self.capabilities or []) for c in capabilities)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate for reputation"""
        total = self.successful_operations + self.failed_operations
        if total == 0:
            return 1.0
        return self.successful_operations / total
    
    @property
    def is_delegated(self) -> bool:
        """Check if this is a delegated (child) agent"""
        return self.parent_agent_id is not None
