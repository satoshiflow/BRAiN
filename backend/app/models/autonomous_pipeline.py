"""
Autonomous Pipeline Models

SQLAlchemy ORM models for workspace, project, and execution contracts.
Provides multi-tenant isolation and audit trail persistence.
"""

import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Enum, Text, Float, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class WorkspaceStatus(str, enum.Enum):
    """Workspace lifecycle status."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class ProjectStatus(str, enum.Enum):
    """Project lifecycle status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class Workspace(Base):
    """
    Tenant/Organization workspace.

    Provides hard isolation for:
    - Secrets & API keys
    - Evidence packs
    - Run contracts
    - Projects
    """
    __tablename__ = "workspaces"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, index=True)

    # Metadata
    description = Column(String(500), nullable=True)
    status = Column(String(50), default=WorkspaceStatus.ACTIVE.value, nullable=False, index=True)

    # Ownership
    owner_id = Column(String(255), nullable=True, index=True)  # User ID or org ID
    created_by = Column(String(255), nullable=True)  # User ID who created

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Isolation paths (storage)
    storage_path = Column(String(500), nullable=True)

    # Limits & Quotas
    max_projects = Column(Integer, default=100, nullable=False)
    max_runs_per_day = Column(Integer, default=1000, nullable=False)
    max_storage_gb = Column(Float, default=100.0, nullable=False)

    # Settings (stored as JSON)
    settings = Column(JSON, default={}, nullable=False)

    # Tags
    tags = Column(JSON, default=[], nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="workspace", cascade="all, delete-orphan")
    run_contracts = relationship("RunContract", back_populates="workspace", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Workspace(id={self.id}, workspace_id={self.workspace_id}, name={self.name})>"


class Project(Base):
    """
    Project within a workspace.

    Groups related pipeline runs and resources.
    """
    __tablename__ = "projects"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(255), unique=True, nullable=False, index=True)
    workspace_id = Column(String(255), ForeignKey("workspaces.workspace_id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False, index=True)

    # Metadata
    description = Column(String(500), nullable=True)
    status = Column(String(50), default=ProjectStatus.ACTIVE.value, nullable=False, index=True)

    # Ownership
    created_by = Column(String(255), nullable=True)  # User ID

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Project settings
    default_budget = Column(JSON, nullable=True)  # Execution budget
    default_policy = Column(JSON, nullable=True)  # Execution policy

    # Statistics
    total_runs = Column(Integer, default=0, nullable=False)
    successful_runs = Column(Integer, default=0, nullable=False)
    failed_runs = Column(Integer, default=0, nullable=False)

    # Tags
    tags = Column(JSON, default=[], nullable=False)

    # Relationships
    workspace = relationship("Workspace", back_populates="projects")
    run_contracts = relationship("RunContract", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Project(id={self.id}, project_id={self.project_id}, name={self.name})>"


class RunContract(Base):
    """
    Immutable run execution contract.

    Captures the complete state of a pipeline execution for audit and replay.
    Persists evidence packs and execution results.
    """
    __tablename__ = "run_contracts"

    # Identity
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id = Column(String(255), unique=True, nullable=False, index=True)
    workspace_id = Column(String(255), ForeignKey("workspaces.workspace_id"), nullable=False, index=True)
    project_id = Column(String(255), ForeignKey("projects.project_id"), nullable=True, index=True)

    # Execution metadata
    graph_id = Column(String(255), nullable=False, index=True)
    business_intent_id = Column(String(255), nullable=True)

    # Status & Results
    status = Column(String(50), nullable=False, index=True)  # pending, running, success, failed
    success = Column(Boolean, default=False, nullable=False)
    dry_run = Column(Boolean, default=False, nullable=False)

    # Execution details (stored as JSON)
    graph_spec = Column(JSON, nullable=True)  # Full execution graph specification
    execution_result = Column(JSON, nullable=True)  # Complete execution result
    evidence_pack = Column(JSON, nullable=True)  # Audit trail & evidence

    # Hashes & Verification
    contract_hash = Column(String(255), nullable=True)  # SHA256 of contract
    evidence_hash = Column(String(255), nullable=True)  # SHA256 of evidence pack

    # Storage
    storage_path = Column(String(500), nullable=True)  # Path to contract file

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    executed_at = Column(DateTime, nullable=True)  # When execution started
    completed_at = Column(DateTime, nullable=True)  # When execution completed

    # Relationships
    workspace = relationship("Workspace", back_populates="run_contracts")
    project = relationship("Project", back_populates="run_contracts")

    def __repr__(self):
        return f"<RunContract(id={self.id}, contract_id={self.contract_id}, status={self.status})>"
