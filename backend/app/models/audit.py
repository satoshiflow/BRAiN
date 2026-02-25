"""
Auth Audit Log Model

SQLAlchemy ORM model for authentication and authorization audit logging.
Tracks all policy decisions, access attempts, and security events.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class AuthAuditLog(Base):
    """
    Auth Audit Log Model
    
    Comprehensive audit trail for authentication and authorization events.
    Captures all policy evaluations, access decisions, and security-relevant actions.
    """
    __tablename__ = "auth_audit_log"

    # Primary identifier
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Timestamp of the event
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Principal (who) - the entity requesting access
    principal_id = Column(String(255), nullable=False, index=True)
    principal_type = Column(String(50), nullable=False, default="user")  # user, agent, service, api_key
    
    # Action (what) - the attempted action
    action = Column(String(255), nullable=False, index=True)
    
    # Resource (where) - the target resource
    resource_id = Column(String(255), nullable=True, index=True)
    
    # Decision (result) - the policy decision
    decision = Column(String(50), nullable=False, index=True)  # allow, deny, warn, audit
    
    # Reasoning (why) - explanation for the decision
    reason = Column(Text, nullable=True)
    
    # Policy reference - which policy was applied
    policy_matched = Column(String(255), nullable=True, index=True)
    rule_matched = Column(String(255), nullable=True)  # specific rule within policy
    
    # Risk assessment
    risk_tier = Column(String(50), nullable=True, default="low")  # low, medium, high, critical
    
    # Network context
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(Text, nullable=True)
    
    # Request tracking
    request_id = Column(String(255), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    # Additional metadata (flexible JSON storage)
    metadata = Column(JSON, nullable=False, default=dict)
    
    # Additional context fields stored in metadata but extracted for common queries
    agent_id = Column(String(255), nullable=True, index=True)  # If acting on behalf of agent
    organization_id = Column(String(255), nullable=True, index=True)
    
    def __repr__(self):
        return (
            f"<AuthAuditLog("
            f"id={self.id}, "
            f"timestamp={self.timestamp}, "
            f"principal={self.principal_id}, "
            f"action={self.action}, "
            f"decision={self.decision}"
            f")>"
        )
    
    def to_dict(self) -> dict:
        """Convert audit log entry to dictionary representation"""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "principal_id": self.principal_id,
            "principal_type": self.principal_type,
            "action": self.action,
            "resource_id": self.resource_id,
            "decision": self.decision,
            "reason": self.reason,
            "policy_matched": self.policy_matched,
            "rule_matched": self.rule_matched,
            "risk_tier": self.risk_tier,
            "ip_address": self.ip_address,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "agent_id": self.agent_id,
            "organization_id": self.organization_id,
        }
