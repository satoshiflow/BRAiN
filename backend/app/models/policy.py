"""
Policy Model

SQLAlchemy ORM model for rule-based authorization policies.
Stores policy definitions, rules, conditions, and metadata.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class Policy(Base):
    """
    Policy Model
    
    Represents an authorization policy with rules, conditions, and effects.
    Policies are evaluated against actions to make access control decisions.
    """
    __tablename__ = "policies"

    # Primary identifier
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Human-readable identifier (unique slug)
    name = Column(String(255), nullable=False, unique=True, index=True)
    
    # Display name/title
    display_name = Column(String(255), nullable=True)
    
    # Policy description
    description = Column(Text, nullable=True)
    
    # Version tracking
    version = Column(String(50), nullable=False, default="1.0.0")
    
    # Resource matching pattern (e.g., "robot.*", "data.read", "*")
    resource_pattern = Column(String(500), nullable=False, default="*")
    
    # Action matching pattern (e.g., "create", "update", "*")
    action_pattern = Column(String(500), nullable=False, default="*")
    
    # Default effect when no rules match
    effect = Column(String(50), nullable=False, default="deny")  # allow, deny, warn, audit
    
    # Policy conditions (JSON storage for flexibility)
    # Structure: [{"field": "agent.role", "operator": "==", "value": "admin"}]
    conditions = Column(JSON, nullable=False, default=list)
    
    # Priority for evaluation order (higher = evaluated first)
    priority = Column(Integer, nullable=False, default=0, index=True)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    is_system = Column(Boolean, nullable=False, default=False)  # System policies can't be deleted
    
    # Ownership
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Soft delete support
    deleted_at = Column(DateTime, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    
    # Additional metadata
    tags = Column(JSON, nullable=False, default=list)
    metadata = Column(JSON, nullable=False, default=dict)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by], backref="created_policies")
    updater = relationship("User", foreign_keys=[updated_by], backref="updated_policies")
    
    def __repr__(self):
        return (
            f"<Policy("
            f"id={self.id}, "
            f"name={self.name}, "
            f"effect={self.effect}, "
            f"priority={self.priority}, "
            f"active={self.is_active}"
            f")>"
        )
    
    def to_dict(self) -> dict:
        """Convert policy to dictionary representation"""
        return {
            "id": str(self.id),
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "version": self.version,
            "resource_pattern": self.resource_pattern,
            "action_pattern": self.action_pattern,
            "effect": self.effect,
            "conditions": self.conditions,
            "priority": self.priority,
            "is_active": self.is_active,
            "is_system": self.is_system,
            "created_by": str(self.created_by) if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "tags": self.tags,
            "metadata": self.metadata,
        }
    
    def matches_resource(self, resource: str) -> bool:
        """Check if this policy applies to a given resource"""
        import fnmatch
        return fnmatch.fnmatch(resource, self.resource_pattern)
    
    def matches_action(self, action: str) -> bool:
        """Check if this policy applies to a given action"""
        import fnmatch
        return fnmatch.fnmatch(action, self.action_pattern)
